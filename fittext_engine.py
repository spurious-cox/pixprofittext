#!/usr/bin/env python3
"""
fittext_engine.py — fit a block of text inside an irregular shape. v1.0.0

Given a MASK (the shape, as an image whose opaque pixels are "inside") and a
string, find the largest font size at which the text fits entirely within the
shape, and where to put it.

The shape is taken as a pixel mask rather than as a path on purpose: Pixelmator
Pro can export a soloed layer as PNG, and its alpha channel is already an exact
rendering of the outline — curves, joins and all — so there is no Bezier
flattening to get subtly wrong.

The fit is exact rather than approximate. For a trial size the text is rendered
to its own mask and every possible placement is tested at once, by counting —
for each offset — how many text pixels would land OUTSIDE the shape. That count
is a cross-correlation, so one FFT gives the answer for every position
simultaneously; any offset scoring zero is a placement where no part of any
glyph crosses the boundary. Size is then found by binary search over that test.

Created by: Claude (Anthropic) for Tim McCoy
"""

import math

import numpy as np
from AppKit import (NSAttributedString, NSBitmapImageRep, NSColor,
                    NSDeviceRGBColorSpace, NSFont, NSFontAttributeName,
                    NSForegroundColorAttributeName, NSGraphicsContext,
                    NSMakeRect, NSMakeSize, NSMutableParagraphStyle,
                    NSParagraphStyleAttributeName)

INSIDE = 128            # alpha at or above this counts as inside the shape


# ---------------------------------------------------------------------------
# Rendering text to a mask
# ---------------------------------------------------------------------------

ALIGNMENTS = {"left": 0, "center": 1, "right": 2}


def text_mask(text, font_name, size, angle=0.0, line_spacing=1.0,
              calibration=None, wrap_width=None, align="center"):
    """Render `text` and return a tight boolean mask of its ink.

    Rendered through AppKit rather than a bitmap font library so the glyphs,
    kerning and line breaking are the same ones Core Text will use when
    Pixelmator draws the finished layer.
    """
    font = NSFont.fontWithName_size_(font_name, size)
    if font is None:
        font = NSFont.systemFontOfSize_(size)
    if calibration is not None:
        # Pixelmator's extra height is LINE SPACING, not bigger glyphs —
        # measured: glyph heights match to within 2%, the block is 39%
        # taller. Applying that as a vertical scale of the finished block
        # stretched every letterform and turned the text into solid bars.
        # It belongs in the paragraph style, before anything is drawn.
        line_spacing = calibration.height_factor
    para = NSMutableParagraphStyle.alloc().init()
    # NSTextAlignment is left=0, CENTRE=1, right=2 — the old
    # NSCenterTextAlignment=2 ordering is long gone, and using it silently
    # right-aligned every block of text this app produced.
    #
    # The alignment must match what Pixelmator will be told to use, or the
    # fit measures one arrangement and the document gets another: the
    # left-justified flag was sized as a centred block and came out small.
    para.setAlignment_(ALIGNMENTS.get(align, 1))
    if line_spacing != 1.0:
        para.setLineHeightMultiple_(line_spacing)
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: NSColor.whiteColor(),
        NSParagraphStyleAttributeName: para,
    }
    string = NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    if wrap_width:
        # Let AppKit break the lines: a paragraph has to be reflowed to fit a
        # shape, not just scaled — scaling alone would shrink one long line
        # until it was unreadable.
        from AppKit import NSStringDrawingUsesLineFragmentOrigin
        rect = string.boundingRectWithSize_options_(
            NSMakeSize(wrap_width, 1.0e6),
            NSStringDrawingUsesLineFragmentOrigin)
        bounds = NSMakeSize(min(wrap_width, math.ceil(rect.size.width)),
                            math.ceil(rect.size.height))
    else:
        bounds = string.size()
    width = int(math.ceil(bounds.width)) + 4
    height = int(math.ceil(bounds.height)) + 4
    if width < 2 or height < 2:
        return np.zeros((1, 1), dtype=bool)

    rep = NSBitmapImageRep.alloc().\
        initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
            None, width, height, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0)
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)
    string.drawInRect_(NSMakeRect(2, 2, bounds.width, bounds.height))
    NSGraphicsContext.restoreGraphicsState()

    # NSBitmapImageRep pads each row to a stride of its own choosing, so the
    # rows must be cut at bytesPerRow.  Reshaping on width*4 instead shifts
    # every row a little further than the last and shears the glyphs into
    # streaks — which still passes a containment test, and still looks wrong.
    stride = int(rep.bytesPerRow())
    raw = rep.bitmapData()
    pixels = np.frombuffer(raw, dtype=np.uint8, count=stride * height)
    rows = pixels.reshape(height, stride)[:, :width * 4]
    alpha = rows.reshape(height, width, 4)[:, :, 3]
    mask = alpha >= 16                          # any ink at all counts
    if calibration is not None and calibration.width_offset:
        # Width is an OFFSET, not a factor — see Calibration. Applied to the
        # width alone: the height is already right, having gone into the
        # line spacing above.
        ink = crop_with_offset(mask)
        target_w = max(1, int(round(ink.mask.shape[1] +
                                    calibration.width_offset)))
        mask = rescale_mask(ink.mask, target_w, ink.mask.shape[0])
    if angle:
        mask = rotate_mask(mask, angle)
    return crop_with_offset(mask)


def rotate_mask(mask, angle):
    """Rotate a boolean mask about its centre, keeping every set pixel.

    Nearest-neighbour on purpose: this is a containment test, and a smoothed
    edge would blur ink across the boundary in one direction or the other.
    """
    theta = math.radians(angle)
    cos, sin = math.cos(theta), math.sin(theta)
    h, w = mask.shape
    # Size the canvas to hold the rotated corners.
    nw = int(math.ceil(abs(w * cos) + abs(h * sin))) + 2
    nh = int(math.ceil(abs(w * sin) + abs(h * cos))) + 2
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    ncy, ncx = (nh - 1) / 2.0, (nw - 1) / 2.0

    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return np.zeros((1, 1), dtype=bool)
    dy, dx = ys - cy, xs - cx
    # Sample forwards from the source pixels; every one lands somewhere.
    ry = np.rint(ncy + dx * sin + dy * cos).astype(np.int64)
    rx = np.rint(ncx + dx * cos - dy * sin).astype(np.int64)
    keep = (ry >= 0) & (ry < nh) & (rx >= 0) & (rx < nw)
    out = np.zeros((nh, nw), dtype=bool)
    out[ry[keep], rx[keep]] = True
    # Forward mapping leaves pin-holes; close them so the containment test is
    # not fooled by a gap that the real glyph does not have.
    return close_holes(out)


def close_holes(mask):
    """Fill single-pixel gaps left by forward rotation (a 3x3 dilate of the
    mask, intersected with a 3x3 erode of its complement's holes)."""
    padded = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), dtype=np.uint8)
    padded[1:-1, 1:-1] = mask
    neighbours = (
        padded[0:-2, 0:-2] + padded[0:-2, 1:-1] + padded[0:-2, 2:] +
        padded[1:-1, 0:-2] + padded[1:-1, 2:] +
        padded[2:, 0:-2] + padded[2:, 1:-1] + padded[2:, 2:]
    )
    # A hole is an unset pixel with at least 5 set neighbours.
    return mask | ((~mask) & (neighbours >= 5))


class Rendered(object):
    """A rendered piece of text: the ink, and where the ink sits inside the
    layer box Pixelmator will give the text layer.

    Both halves are needed. The fit works on the ink — that is what must stay
    inside the shape — but the thing being positioned afterwards is the LAYER,
    whose box includes the font's line-height padding above and below the ink.
    Placing the layer at the ink's position would sit it slightly wrong every
    time, by an amount that changes with the font and the point size.
    """

    __slots__ = ("mask", "dx", "dy", "box_w", "box_h", "lines", "align")

    def __init__(self, mask, dx, dy, box_w, box_h):
        self.mask = mask
        self.dx, self.dy = dx, dy          # ink offset within the layer box
        self.box_w, self.box_h = box_w, box_h
        self.lines = []                    # set when the breaks came from a flow
        self.align = "center"

    @property
    def shape(self):
        return self.mask.shape


def crop_with_offset(mask):
    """Trim to the ink, remembering what was trimmed."""
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return Rendered(np.zeros((1, 1), dtype=bool), 0, 0,
                        mask.shape[1], mask.shape[0])
    y0, y1 = int(ys.min()), int(ys.max())
    x0, x1 = int(xs.min()), int(xs.max())
    return Rendered(mask[y0:y1 + 1, x0:x1 + 1], x0, y0,
                    mask.shape[1], mask.shape[0])


# ---------------------------------------------------------------------------
# The shape
# ---------------------------------------------------------------------------

class Calibration(object):
    """How Pixelmator's typesetting differs from AppKit's, for one piece of
    text in one font.

    Measured rather than modelled. Pixelmator lays the same string out
    wider than AppKit does, and taller (looser line spacing). Neither is
    reachable from a script: rich text exposes only color, font and size.
    So both are measured once, from the real thing.

    Width is an OFFSET and height is a FACTOR, and they are different
    shapes because the two effects are different things. Measured for
    Helvetica Neue at 13 sizes from 6pt to 72pt:

        drawn_w - model_w  =  79, 78, 79, 78, 79, 78, 79, 79, 77, 79, 79,
                              80, 79        -- constant, in pixels
        drawn_h / model_h  =  1.43 at every size, no trend

    Width was made a factor once before, because at +4px a 42pt fit came
    out 6.6% wide. That was the right observation and the wrong conclusion:
    the offset is not 4, it is ~79, and 4 was simply far too small. As a
    ratio the true offset reads 1.04 at 72pt and 1.53 at 6pt, so a factor
    fitted at one size is wrong at every other — which is what sent the
    verify loop shrinking 18, 17, 16, 14, 12, 10, 8, 6 and still 15px
    outside, the fixed offset becoming a larger share of an ever smaller
    line.
    """

    __slots__ = ("width_offset", "height_factor", "text", "font")

    def __init__(self, width_offset=0.0, height_factor=1.0, text="", font=""):
        self.width_offset = width_offset
        self.height_factor = height_factor
        self.text, self.font = text, font

    def applies_to(self, text, font):
        """Only the FONT matters. Both numbers are properties of the
        typeface — how much wider Pixelmator sets a line and how much looser
        its spacing — so re-measuring because the wording changed meant
        flashing a probe across the user's canvas for nothing."""
        return self.font == font

    def target(self, ink_w, ink_h):
        """What Pixelmator will actually draw, given what AppKit drew."""
        return (max(1, int(round(ink_w + self.width_offset))),
                max(1, int(round(ink_h * self.height_factor))))

    def __repr__(self):
        return "Calibration(%+.1fpx wide, x%.4f tall)" % (
            self.width_offset, self.height_factor)


def dark_ink(path, threshold=128):
    """Ink from a document export: pixels that are OPAQUE and DARK.

    Neither test alone is reliable, because Pixelmator's whole-document
    export is sometimes opaque and sometimes transparent, and each case
    defeats the other test in exactly the same way — by reporting the whole
    canvas:

      * opaque white background -> every pixel has alpha 255, so an alpha
        test returns all of it (this is what gave a height factor of 0.0000)
      * transparent background  -> convert("L") renders those pixels BLACK,
        so a darkness test returns all of it (same numbers, same failure)

    Requiring both is stable whichever export turns up.  The calibration
    probes are drawn near-black, so they satisfy both wherever there is ink.
    """
    from PIL import Image
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    opaque = rgba[:, :, 3] > 16
    dark = rgba[:, :, :3].mean(axis=2) < threshold
    return opaque & dark


def rescale_mask(mask, width, height):
    """Resize a boolean mask, keeping anything that was set."""
    from PIL import Image
    if mask.shape[1] == width and mask.shape[0] == height:
        return mask
    image = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8))
    resized = image.resize((max(1, width), max(1, height)), Image.BILINEAR)
    return np.array(resized) >= 64


def load_shape(path, fill_interior=True):
    """Read a mask image; opaque pixels are inside the shape.

    `fill_interior` closes holes so only the OUTER boundary constrains the
    text — a shape with letters knocked out of it is still one shape, and
    text crossing those gaps is fine.  Turn it off to treat a hole as a
    genuine no-go area.
    """
    from PIL import Image
    image = Image.open(path).convert("RGBA")
    alpha = np.array(image)[:, :, 3]
    shape = alpha >= INSIDE
    return fill_holes(shape) if fill_interior else shape


def fill_edge_notches(shape, min_depth):
    """Close a notch that SPLITS the shape, leaving the outline alone.

    A notch worth ignoring divides a row in two: an arch standing on legs
    has, in the notched rows, ink at the left and ink at the right with a
    gap between. Filling that gap lets the flow run its lines across, which
    is what "Ignore Notch" asks for. The legs otherwise stay empty, because
    text cannot read down one and up the other.

    The test is per ROW, between the first and last ink on it. That is the
    whole of it, and it is why this is right where a per-column rule was
    wrong: a column-wise fill closed every column starting lower than the
    shape's top, which on a dome is not a notch at all but its curvature —
    it squared off all four corners and left the notch untouched.

    It also leaves a notch that opens onto a SIDE alone, for free. A flag's
    swallowtail takes a bite out of the right edge, so those rows hold one
    contiguous run and there is no gap between first and last ink to fill.

    `min_depth` is in rows: a gap shallower than this is roughness rather
    than a notch, and the flow can already lay a line beside it.
    """
    if not shape.any():
        return shape
    out = shape.copy()
    for y in range(shape.shape[0]):
        cols = np.nonzero(shape[y])[0]
        if cols.size:
            out[y, int(cols.min()):int(cols.max()) + 1] = True
    added = out & ~shape
    if not added.any():
        return shape
    rows = np.nonzero(added.any(axis=1))[0]
    if int(rows.max() - rows.min() + 1) < min_depth:
        return shape                     # roughness, not a notch
    return out


def fill_holes(shape):
    """Everything enclosed by the outline counts as inside.

    Found by flooding the background inwards from a border that is padded on
    on purpose, so the flood always has somewhere to start: whatever the
    flood cannot reach is enclosed, whether it is shape or hole.
    """
    from PIL import Image, ImageDraw
    h, w = shape.shape
    padded = Image.new("L", (w + 2, h + 2), 0)
    padded.paste(Image.fromarray(np.where(shape, 255, 0).astype(np.uint8)),
                 (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    reached = np.array(padded)[1:-1, 1:-1] == 128
    return ~reached


def shape_bounds(shape):
    ys, xs = np.nonzero(shape)
    if ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def centroid(shape):
    ys, xs = np.nonzero(shape)
    return float(xs.mean()), float(ys.mean())


def dilate(mask, radius):
    """Grow a mask by `radius` pixels, ENLARGING it to make room.

    Growing in place would clip the new margin against the mask's own edge —
    the one place a margin is actually needed — so the array is enlarged by
    the radius on every side first. Getting this wrong produced text that
    passed the margin test and still touched the outline.
    """
    if radius <= 0:
        return mask
    radius = int(radius)
    out = np.zeros((mask.shape[0] + 2 * radius, mask.shape[1] + 2 * radius),
                   dtype=bool)
    out[radius:radius + mask.shape[0], radius:radius + mask.shape[1]] = mask
    for _ in range(radius):
        padded = np.zeros((out.shape[0] + 2, out.shape[1] + 2), dtype=bool)
        padded[1:-1, 1:-1] = out
        out = (padded[0:-2, 1:-1] | padded[2:, 1:-1] |
               padded[1:-1, 0:-2] | padded[1:-1, 2:] | out)
    return out


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------

def _overlap_map(outside, text):
    """For every placement of `text` over `outside`, how many text pixels land
    outside the shape.

    One FFT answers the question for all positions at once — the alternative,
    sliding the text over the shape, is O(positions x text pixels) and far too
    slow to sit behind a live angle slider.
    """
    H, W = outside.shape
    h, w = text.shape
    if h > H or w > W:
        return None
    fh, fw = _fast_len(H + h - 1), _fast_len(W + w - 1)
    spectrum = (np.fft.rfft2(outside.astype(np.float32), (fh, fw)) *
                np.fft.rfft2(text[::-1, ::-1].astype(np.float32), (fh, fw)))
    full = np.fft.irfft2(spectrum, (fh, fw))
    return full[h - 1:H, w - 1:W]


def _fast_len(n):
    """Round up to a length numpy's FFT likes (2^a * 3^b * 5^c)."""
    best = 2 ** int(math.ceil(math.log2(max(n, 1))))
    for a in range(int(math.log2(best)) + 1):
        for b in range(8):
            for c in range(5):
                v = (2 ** a) * (3 ** b) * (5 ** c)
                if n <= v < best:
                    best = v
    return best


def best_placement(shape, text, prefer=None):
    """Where to put `text` so no ink leaves `shape`.

    Returns (x, y) of the text mask's top-left corner, or None if it will not
    fit anywhere.  Among the placements that work, the one whose centre is
    nearest `prefer` (the shape's centroid by default) is chosen — a fit that
    is technically legal but jammed into a corner is not the one anybody
    wants.
    """
    overlap = _overlap_map(~shape, text)
    if overlap is None:
        return None
    # FFT arithmetic leaves a little noise; a genuine fit scores 0.
    ys, xs = np.nonzero(overlap < 0.5)
    if ys.size == 0:
        return None
    if prefer is None:
        prefer = centroid(shape)
    h, w = text.shape
    cx = xs + w / 2.0
    cy = ys + h / 2.0
    d = (cx - prefer[0]) ** 2 + (cy - prefer[1]) ** 2
    i = int(np.argmin(d))
    return int(xs[i]), int(ys[i])


# ---------------------------------------------------------------------------
# The fit
# ---------------------------------------------------------------------------

class Fit(object):
    """A placed piece of text: where its ink goes, and where the LAYER goes."""

    __slots__ = ("size", "x", "y", "width", "height", "angle", "text_mask",
                 "rendered")

    @property
    def lines(self):
        return getattr(self.rendered, "lines", [])

    @property
    def align(self):
        return getattr(self.rendered, "align", "center")

    def __init__(self, size, x, y, rendered, angle):
        self.size = size
        self.x, self.y = x, y              # top-left of the INK
        self.height, self.width = rendered.mask.shape
        self.angle = angle
        self.text_mask = rendered.mask
        self.rendered = rendered

    @property
    def center(self):
        return self.x + self.width / 2.0, self.y + self.height / 2.0

    @property
    def layer_position(self):
        """Top-left of the ROTATED layer box, which is what Pixelmator's
        `position` property sets."""
        return (self.x - self.rendered.dx, self.y - self.rendered.dy)


# Wrap widths to try, as fractions of the shape's bounding-box width. A
# paragraph can be laid out tall and narrow or short and wide; which one fits
# biggest depends on the shape, so a few shapes of block are tried and the
# best kept.
WRAP_FRACTIONS = (0.95, 0.8, 0.65, 0.5, 0.35)

# The longest line must use at least this much of the widest opening the
# shape offered, or the layout is a column rather than a filled shape.
MIN_WIDTH_USE = 0.55


def fit_text(shape, text, font_name, angle=0.0, padding=0,
             min_size=6.0, max_size=None, tolerance=0.5, line_spacing=1.0,
             calibration=None, wrap=False, align="center"):
    """Largest font size at which `text` fits inside `shape` at `angle`.

    Binary search: the fit is monotonic in size — if it fits at 80pt it fits
    at 60pt — so the largest workable size is found in about a dozen tests
    rather than by stepping through every point size.
    """
    if not text.strip():
        return None
    bounds = shape_bounds(shape)
    if bounds is None:
        return None
    if max_size is None:
        # No text can be taller than the shape itself.
        max_size = float(bounds[3] - bounds[1] + 1)

    prefer = centroid(shape)

    widths = [None]
    if wrap:
        span = float(bounds[2] - bounds[0] + 1)
        widths = [span * f for f in WRAP_FRACTIONS]

    def attempt_width(size, wrap_width):
        """Place using the grown mask; keep the real ink for everything else.

        The margin is applied by dilating the text and testing THAT against
        the shape. But the dilated mask is not the text — at a 6px margin
        neighbouring letters merge into solid bars — so it must not be what
        gets drawn in the preview. Only the placement comes from it; the
        position is shifted back by the margin so it describes the ink.
        """
        rendered = text_mask(text, font_name, size, angle, line_spacing,
                             calibration, wrap_width, align=align)
        grown = dilate(rendered.mask, padding) if padding else rendered.mask
        spot = best_placement(shape, grown, prefer)
        if spot is not None:
            spot = (spot[0] + padding, spot[1] + padding)
        return (spot, rendered)

    def attempt(size):
        """Try each candidate wrap width; any that fits will do."""
        for wrap_width in widths:
            spot, rendered = attempt_width(size, wrap_width)
            if spot is not None:
                return spot, rendered
        return None, rendered

    lo, hi = float(min_size), float(max_size)
    spot, rendered = attempt(lo)
    if spot is None:
        return None                     # will not fit even at the floor
    best = Fit(lo, spot[0], spot[1], rendered, angle)

    while hi - lo > tolerance:
        mid = (lo + hi) / 2.0
        spot, rendered = attempt(mid)
        if spot is None:
            hi = mid
        else:
            lo = mid
            best = Fit(mid, spot[0], spot[1], rendered, angle)
    return best


def best_angle(shape, text, font_name, angles=None, **kwargs):
    """The angle that lets the text be biggest, and its fit."""
    if angles is None:
        angles = list(range(-90, 91, 5))
    winner = None
    for angle in angles:
        fit = fit_text(shape, text, font_name, angle=float(angle), **kwargs)
        if fit is not None and (winner is None or fit.size > winner.size):
            winner = fit
    return winner


# ---------------------------------------------------------------------------
# Flowing text into the shape itself
# ---------------------------------------------------------------------------
#
# The block fit treats the text as one rectangle, which wastes a curved shape:
# a bowl is widest across the middle and narrow at the bottom, and a rectangle
# big enough to stay inside it is much smaller than the shape could hold.
#
# Flowing lays out line by line instead. For each line, the widest run of the
# shape that is clear for the FULL height of that line is measured, the next
# words are fitted to that width, and the line is centred on that run — so the
# lines follow the outline, long across the middle and short at the ends, and
# the justification falls out of the shape rather than being chosen.


def line_runs(shape, top, height):
    """The widest horizontal run clear for every row of a line.

    A line is only safe where the shape is continuous down its whole height,
    so the rows are ANDed together before the longest run is measured — using
    just the middle row would let ascenders and descenders cross the edge.
    """
    bottom = min(shape.shape[0], top + height)
    if top < 0 or bottom <= top:
        return None
    band = np.logical_and.reduce(shape[top:bottom, :], axis=0)
    if not band.any():
        return None
    # Longest run of True in `band`.
    padded = np.concatenate(([False], band, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[0::2], edges[1::2]
    widest = int(np.argmax(ends - starts))
    return int(starts[widest]), int(ends[widest])


def justification_for(shape, sample=60):
    """Which way to justify, decided by the SHAPE rather than by taste.

    A shape whose left edge is straight and whose right edge is ragged — a
    pennant with a notch bitten out of its right — wants its text
    left-justified: centring it wastes the whole straight side. A shape
    ragged on both sides, like a diamond, wants centring.

    Measured as the variation in each edge across the rows: the flag reads
    0.000 left against 0.139 right, the diamond 0.141 against 0.141.
    """
    bounds = shape_bounds(shape)
    if bounds is None:
        return "center"
    x0, y0, x1, y1 = bounds
    step = max(1, (y1 - y0) // sample)
    lefts, rights = [], []
    for y in range(y0, y1 + 1, step):
        run = line_runs(shape, y, 18)
        if run:
            lefts.append(run[0])
            rights.append(run[1])
    if len(lefts) < 3:
        return "center"
    span = float(x1 - x0 + 1) or 1.0
    left_var = float(np.std(lefts)) / span
    right_var = float(np.std(rights)) / span
    if left_var < right_var * 0.5:
        return "left"
    if right_var < left_var * 0.5:
        return "right"
    return "center"


def flow_text(shape, text, font_name, size, line_spacing=1.15, padding=0,
              top=None, axis=None, align="center"):
    """Lay the text out following the shape. Returns a mask, or None.

    Words are placed greedily: each line takes as many as the shape is wide
    enough to hold at that height.
    """
    words = text.split()
    if not words:
        return None
    probe = text_mask("Hg", font_name, size)
    line_h = max(1, int(round(probe.box_h * line_spacing)))
    space_w = max(1, int(round(size * 0.28)))

    ys = np.nonzero(shape.any(axis=1))[0]
    if ys.size == 0:
        return None
    first, last = int(ys.min()), int(ys.max())
    top = first if top is None else max(first, int(top))

    canvas = np.zeros(shape.shape, dtype=bool)
    index = 0
    y = top
    cache = {}
    lines = []
    widest_run = 0        # the most width the shape ever offered a line
    widest_line = 0       # the most any line actually used

    def line_render(words_slice):
        """Render a whole line at once.

        Word by word would need each word's baseline computed by hand, and
        getting that wrong shows immediately: short words with no ascender
        ("you", "us") float above the others and the line looks mis-set.
        One string per line keeps the baseline and the kerning that the
        typesetter already knows how to do.
        """
        key = " ".join(words_slice)
        if key not in cache:
            cache[key] = text_mask(key, font_name, size)
        return cache[key]

    while index < len(words) and y + line_h <= last + 1:
        run = line_runs(shape, y, line_h)
        if run is None:
            y += max(1, line_h // 3)
            continue
        left, right = run
        if axis is not None:
            # Only as wide as a line centred on the shape's axis can be.
            #
            # Off by default. It was added so a centred text layer could
            # reproduce the flow exactly, but constraining every line to one
            # axis costs more width than the conversion does: on the notched
            # flag it turned a 9.5pt result into 7.3pt. The block fit does
            # not need axis-centred lines — it only needs the ink to fit
            # somewhere, and it finds where.
            reach = min(axis - left, right - axis)
            if reach <= 0:
                y += max(1, line_h // 3)
                continue
            left = int(round(axis - reach))
            right = int(round(axis + reach))
        usable = (right - left) - 2 * padding
        widest_run = max(widest_run, usable)
        if usable <= 0:
            y += max(1, line_h // 3)
            continue

        # How many words will this line hold?
        count = 0
        rendered = None
        while index + count < len(words):
            trial = line_render(words[index:index + count + 1])
            if count and trial.mask.shape[1] > usable:
                break
            if not count and trial.mask.shape[1] > usable:
                rendered = None
                break
            count += 1
            rendered = trial
        if not count or rendered is None:
            y += max(1, line_h // 3)
            continue

        ph, pw = rendered.mask.shape
        if align == "left":
            x = left + padding
        elif align == "right":
            x = right - padding - pw
        else:
            x = left + padding + (usable - pw) // 2
        top_y = y + max(0, (line_h - ph) // 2)
        if top_y + ph > canvas.shape[0] or x + pw > canvas.shape[1] or x < 0:
            return None
        canvas[top_y:top_y + ph, x:x + pw] |= rendered.mask
        widest_line = max(widest_line, pw)
        lines.append(" ".join(words[index:index + count]))
        index += count
        y += line_h

    if index < len(words):
        return None                      # ran out of shape before words
    # Reject a layout that ignores the shape's width.
    #
    # Maximising point size alone is not enough. A tall shape usually has a
    # narrow column clear all the way down, and one enormous word per line
    # stacked vertically will always beat a sensibly filled layout on size —
    # it is bigger text and unreadable typography. Requiring the longest line
    # to use a fair share of the widest opening the shape offered rules that
    # out, while still allowing genuinely narrow shapes, where the widest
    # opening is small too.
    if widest_run and widest_line < MIN_WIDTH_USE * widest_run:
        return None
    return canvas, lines


def fit_flowed(shape, text, font_name, angle=0.0, padding=0, min_size=6.0,
               max_size=None, tolerance=0.5, line_spacing=1.15, axis=False,
               align=None):
    """Largest size at which the text flows inside the shape at this angle."""
    if not text.strip():
        return None
    work = rotate_mask(shape, -angle) if angle else shape
    bounds = shape_bounds(work)
    if bounds is None:
        return None
    if max_size is None:
        max_size = float(bounds[3] - bounds[1] + 1)

    centre_x = (bounds[0] + bounds[2]) / 2.0 if axis else None
    if align is None:
        align = justification_for(work)

    def attempt(size):
        result = flow_text(work, text, font_name, size, line_spacing, padding,
                           axis=centre_x, align=align)
        if result is None:
            return None
        laid, lines = result
        if not laid.any() or (laid & ~work).any():
            return None                  # ink crossed the outline
        return laid, lines

    # Scan rather than bisect. Bisection assumes that if a size fits then
    # every smaller size fits, and the width-use rule breaks that: a SHORT
    # text at a small size uses very little of a wide shape and is rejected,
    # while the same text at a larger size fills it and is accepted. Starting
    # from the smallest size and bisecting therefore concluded "will not fit,
    # even at 6 pt" for text that fits perfectly well at 60.
    steps = 22
    ratio = (float(max_size) / float(min_size)) ** (1.0 / (steps - 1))
    sizes = [float(min_size) * (ratio ** i) for i in range(steps)]
    best = best_size = None
    for size in reversed(sizes):           # largest first; take the first win
        laid = attempt(size)
        if laid is not None:
            best, best_size = laid, size
            break
    if best is None:
        return None
    # Refine upwards between the winner and the next size that failed.
    lo, hi = best_size, min(float(max_size), best_size * ratio)
    while hi - lo > tolerance:
        mid = (lo + hi) / 2.0
        laid = attempt(mid)
        if laid is None:
            hi = mid
        else:
            lo, best, best_size = mid, laid, mid

    # Then choose WHERE to start. Flowing from the shape's topmost row puts
    # the block's widest lines above the shape's widest band, which on a
    # diamond left 36px at the top and 83px at the bottom — text that is
    # inside the shape but visibly not centred in it. Starting a little
    # lower costs nothing and balances the margins.
    top_row, bottom_row = bounds[1], bounds[3]
    balanced = best
    best_gap = None
    for start in range(int(top_row),
                       int(top_row + (bottom_row - top_row) * 0.25),
                       max(4, int((bottom_row - top_row) * 0.02))):
        result = flow_text(work, text, font_name, best_size, line_spacing,
                           padding, top=start, axis=centre_x, align=align)
        if result is None:
            continue
        laid, _lines = result
        if not laid.any() or (laid & ~work).any():
            continue
        ys = np.nonzero(laid.any(axis=1))[0]
        gap = abs((ys.min() - top_row) - (bottom_row - ys.max()))
        if best_gap is None or gap < best_gap:
            best_gap, balanced = gap, (laid, _lines)
    fit = FlowFit(best_size, balanced[0], angle, shape, balanced[1])
    fit.align = align
    return fit


class FlowFit(object):
    """A flowed layout, expressed the way the block fit is so the preview and
    the placement code do not have to care which produced it."""

    __slots__ = ("size", "angle", "text_mask", "x", "y", "width", "height",
                 "rendered", "lines", "align")

    def __init__(self, size, laid, angle, shape, lines=None):
        self.size = size
        self.angle = angle
        # The line breaks the flow chose. A Pixelmator text layer re-wraps to
        # a rectangle, so the only way to reproduce a shaped layout there is
        # to hand it these breaks and centre the result.
        self.lines = lines or []
        self.align = "center"
        if angle:
            laid = rotate_mask(laid, angle)
        placed = crop_with_offset(laid)
        self.text_mask = placed.mask
        self.height, self.width = placed.mask.shape
        self.rendered = placed
        spot = best_placement(shape, placed.mask, centroid(shape))
        self.x, self.y = spot if spot else (placed.dx, placed.dy)

    @property
    def center(self):
        return self.x + self.width / 2.0, self.y + self.height / 2.0

    @property
    def layer_position(self):
        return (self.x, self.y)


def fit_shaped(shape, text, font_name, angle=0.0, padding=0,
               calibration=None, line_spacing=1.15):
    """Line breaks from the shape, size and position from the calibration.

    Flowing decides WHERE the lines should break — that is the part that
    needs the shape. But a Pixelmator text layer cannot hold per-line
    offsets: it re-lays the words itself. So the flow's answer is taken as
    line breaks, and those pre-broken lines are then fitted as one centred
    block through the calibrated fitter, which knows what Pixelmator's
    typesetter will actually do with them.

    The result is a preview that matches what Apply produces, instead of a
    beautiful preview and a disappointing layer.
    """
    flowed = fit_flowed(shape, text, font_name, angle=angle, padding=padding,
                        line_spacing=line_spacing)
    if flowed is None or not flowed.lines:
        return None
    broken = "\n".join(flowed.lines)
    fit = fit_text(shape, broken, font_name, angle=angle, padding=padding,
                   calibration=calibration)
    if fit is None:
        return None
    fit.rendered.lines = flowed.lines
    return fit

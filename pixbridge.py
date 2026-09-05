#!/usr/bin/env python3
"""
pixbridge.py — talking to Pixelmator Pro. v1.0.0

Everything that has to go through AppleScript lives here, so the geometry in
fittext_engine.py stays testable without an app running.

Two Pixelmator Pros can be installed at once: the original
(com.pixelmatorteam.pixelmator.x) and the rebranded "Pixelmator Pro Creator
Studio" (com.apple.pixelmator).  They share a scripting dictionary but NOT a
bundle id, and `tell application "Pixelmator Pro"` can reach whichever it
likes — so everything here is addressed by bundle id, and the one actually
holding a document wins.

Created by: Claude (Anthropic) for Tim McCoy
"""

import os
import subprocess

BUNDLE_IDS = ("com.apple.pixelmator",                 # Creator Studio 4.x
              "com.pixelmatorteam.pixelmator.x")      # Pixelmator Pro 3.x


class PixmatorError(RuntimeError):
    pass


def run(script):
    result = subprocess.run(["/usr/bin/osascript", "-e", script],
                            capture_output=True)
    out = result.stdout.decode("utf-8", "replace").strip()
    if result.returncode != 0:
        raise PixmatorError(result.stderr.decode("utf-8", "replace").strip())
    return out


def _tell(bundle_id, body):
    return 'tell application id "%s"\n%s\nend tell' % (bundle_id, body)


def active_bundle():
    """The bundle id of the Pixelmator that has a document open.

    Preferring the one with a document is what keeps the app from quietly
    driving the other copy — which is exactly what happened the first time.
    """
    fallback = None
    for bundle_id in BUNDLE_IDS:
        try:
            count = run(_tell(bundle_id, "return (count of documents) as text"))
        except PixmatorError:
            continue
        if count.isdigit() and int(count) > 0:
            return bundle_id
        fallback = fallback or bundle_id
    if fallback is None:
        raise PixmatorError("Pixelmator Pro does not appear to be running.")
    raise PixmatorError("Pixelmator Pro has no document open.")


def document_info(bundle_id):
    """(name, width, height) of the front document."""
    body = ('set d to front document\n'
            'return (name of d) & "\\t" & (width of d) & "\\t" & (height of d)')
    name, width, height = run(_tell(bundle_id, body)).split("\t")
    return name, float(width), float(height)


def selected_shape_layer(bundle_id):
    """The name of the selected shape layer, or None.

    Matched on the class NAME rather than the bare `shape layer` class:
    Pixelmator has a class per shape kind — rounded rectangle, ellipse,
    polygon, star — and comparing against `shape layer` alone misses all of
    them. Selecting the diamond therefore matched nothing, and the caller
    quietly fell back to the first shape in the document.

    Names are used rather than ids because a layer reference cannot be handed
    between separate osascript invocations, and every call here is one.
    """
    body = ('set d to front document\n'
            'repeat with L in layers of d\n'
            '  if (selected of L) and ((class of L as text) contains "shape layer") then\n'
            '    return name of L\n'
            '  end if\n'
            'end repeat\n'
            'return ""')
    return run(_tell(bundle_id, body)) or None


def shape_layer_names(bundle_id):
    body = ('set d to front document\n'
            'set out to ""\n'
            'repeat with L in layers of d\n'
            '  if (class of L as text) contains "shape layer" then set out to out & (name of L) & "\\n"\n'
            'end repeat\n'
            'return out')
    return [n for n in run(_tell(bundle_id, body)).split("\n") if n]


def selected_layer_description(bundle_id):
    """Whatever IS selected, so the user can be told why it will not do."""
    body = ('set d to front document\n'
            'repeat with L in layers of d\n'
            '  if selected of L then return (name of L) & "\\t" & (class of L as text)\n'
            'end repeat\n'
            'return ""')
    answer = run(_tell(bundle_id, body))
    if not answer or "\t" not in answer:
        return None, None
    name, kind = answer.split("\t", 1)
    return name, kind


SNAPSHOT = os.path.expanduser(
    "~/Library/Application Support/PixProFitText/layer_visibility.txt")


def restore_visibility(bundle_id):
    """Put every layer back on if a previous export never finished.

    export_layer_mask switches off every layer but one. If the app dies in
    between — a crash, or a build that killed it mid-flight — the document
    is left with a single visible layer and everything else off, which
    looks exactly like the artwork having been deleted. The snapshot is
    written BEFORE anything is hidden, so it is always there to undo it.
    """
    if not os.path.exists(SNAPSHOT):
        return 0
    try:
        rows = [r.split("\t") for r in
                open(SNAPSHOT, encoding="utf-8").read().split("\n") if r]
    except OSError:
        return 0
    if not rows:
        os.remove(SNAPSHOT)
        return 0
    pairs = "".join(
        '  if (id of L as text) is "%s" then set visible of L to %s\n'
        % (_escape(i), "true" if v == "1" else "false") for i, v in rows)
    body = ('set d to front document\n'
            'repeat with L in layers of d\n'
            '  try\n'
            '%s'
            '  end try\n'
            'end repeat\n'
            'return "ok"' % pairs)
    try:
        run(_tell(bundle_id, body))
    except Exception:
        return 0
    os.remove(SNAPSHOT)
    return len(rows)


def _snapshot_visibility(bundle_id):
    """Record what is on and what is off, on disk, before hiding anything."""
    body = ('set d to front document\n'
            'set out to ""\n'
            'repeat with L in layers of d\n'
            '  set out to out & (id of L as text) & tab & '
            '(if visible of L then "1" else "0") & linefeed\n'
            'end repeat\n'
            'return out')
    rows = run(_tell(bundle_id, body))
    os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
    with open(SNAPSHOT, "w", encoding="utf-8") as fh:
        fh.write(rows)


def export_layer_mask(bundle_id, layer_name, out_path):
    """Export just one layer as PNG, and put every other layer back.

    Visibility is captured and restored BY LAYER ID, not by position. The
    first version walked `layers of d` twice and matched saved states to the
    second walk by index — so anything that changed the layer set between
    the two walks handed every layer somebody else's state, and the document
    came back with most of its layers switched off. Ids survive reordering,
    insertion and deletion; positions do not.

    Each restore is also its own `try`, so one layer that refuses cannot
    leave the rest of them hidden.
    """
    _snapshot_visibility(bundle_id)
    body = ('set d to front document\n'
            'set ids to {}\n'
            'set states to {}\n'
            'repeat with L in layers of d\n'
            '  set end of ids to (id of L)\n'
            '  set end of states to (visible of L)\n'
            'end repeat\n'
            'set outcome to "ok"\n'
            'try\n'
            '  repeat with L in layers of d\n'
            '    if (name of L) is "%s" then\n'
            '      set visible of L to true\n'
            '    else\n'
            '      set visible of L to false\n'
            '    end if\n'
            '  end repeat\n'
            '  export d to POSIX file "%s" as PNG\n'
            'on error errMsg\n'
            '  set outcome to "ERROR: " & errMsg\n'
            'end try\n'
            'repeat with L in layers of d\n'
            '  try\n'
            '    set theID to id of L\n'
            '    repeat with i from 1 to count of ids\n'
            '      if (item i of ids) is theID then\n'
            '        set visible of L to (item i of states)\n'
            '        exit repeat\n'
            '      end if\n'
            '    end repeat\n'
            '  end try\n'
            'end repeat\n'
            'return outcome' % (_escape(layer_name), _escape(out_path)))
    outcome = run(_tell(bundle_id, body))
    if outcome != "ok":
        raise PixmatorError(outcome)
    return out_path


def add_text_layer(bundle_id, text, font_name, size, angle, position,
                   color=(0, 0, 0), name="Fitted Text", align=None,
                   box_width=None):
    """Create the text layer and put it exactly where the fit says.

    The angle is NEGATED on the way in. Pixelmator's `rotation` is
    counter-clockwise-positive; the engine's rotate_mask is
    clockwise-positive. Measured in a scratch document: rotation +22 rises
    to the right, rotate_mask(+22) falls to the right, both at slope 0.403.
    Same magnitude, opposite sign, so the preview and the layer leaned
    opposite ways — 44 degrees apart at -22. apply_fit never caught it
    because it only asks whether ink escapes the shape, and on a roughly
    symmetric shape the mirrored angle still fits.

    Order matters: the rotation goes on BEFORE the position, because
    `position` addresses the top-left of the ROTATED bounding box — setting it
    first and then rotating moves the layer out from under the answer.
    """
    body = ('set d to front document\n'
            'tell d\n'
            '  set t to make new text layer at the beginning of layers '
            'with properties {text content:"%s"}\n'
            '  tell text content of t\n'
            '    set its font to "%s"\n'
            '    set its size to %.3f\n'
            '    set its color to {%d, %d, %d}\n'
            '  end tell\n'
            '  set name of t to "%s"\n'
            '%s'
            '%s'
            # Re-assert the size AFTER the width. The box arrives too late
            # to stop the wrap Pixelmator performed when the layer was
            # created with its text, so the layout is nudged into being
            # recomputed at the width we actually asked for. Without this,
            # 7 lines came back as 8 bands with 43px outside the shape,
            # however wide the box was made.
            '  tell text content of t to set its size to %.3f\n'
            '  delay 0.1\n'
            '  set rotation of t to %.3f\n'
            '  delay 0.15\n'
            '  set position of t to {%.1f, %.1f}\n'
            '  delay 0.1\n'
            '  set b to bounds of t\n'
            '  return (item 1 of b as text) & "\\t" & (item 2 of b as text) '
            '& "\\t" & (item 3 of b as text) & "\\t" & (item 4 of b as text)\n'
            'end tell'
            % (_escape(text), _escape(font_name), size,
               # AppleScript colour channels are 0-65535, not 0-255.
               # Passing 0-255 through made every chosen colour arrive as
               # near-black: red (255,0,0) became (255,0,0) out of 65535.
               color[0] * 257, color[1] * 257, color[2] * 257, _escape(name),
               ('  set horizontal alignment of t to %s\n' % align)
               if align in ("left", "center", "right") else '',
               # A scripted text layer gets an automatic box width, and any
               # line longer than it is RE-WRAPPED by Pixelmator — which
               # destroys a shaped layout, fails the check, and sends the
               # retry loop shrinking the text to nothing. Give the box room
               # for the longest line and it lays out as intended.
               ('  set width of t to %d\n' % int(box_width)) if box_width else '',
               size, (-angle) % 360.0, position[0], position[1]))
    return [float(v) for v in run(_tell(bundle_id, body)).split("\t")]


def unique_layer_name(bundle_id, base):
    """A layer name nothing else is using.

    Each fit gets its own layer: reusing one name meant every Apply deleted
    the previous result, so fitting text into a second shape destroyed the
    first.
    """
    body = ('set d to front document\n'
            'set out to ""\n'
            'repeat with L in layers of d\n'
            '  set out to out & (name of L) & "\\n"\n'
            'end repeat\n'
            'return out')
    taken = set(n for n in run(_tell(bundle_id, body)).split("\n") if n)
    if base not in taken:
        return base
    n = 2
    while "%s %d" % (base, n) in taken:
        n += 1
    return "%s %d" % (base, n)


def delete_layer(bundle_id, layer_name):
    """Delete by name, addressed directly.

    NOT by walking `layers of d` and deleting the loop variable: removing a
    layer renumbers the collection being iterated, and Pixelmator refuses the
    reference outright ("Can't get item 1 of every layer").
    """
    body = ('set d to front document\n'
            'try\n'
            '  delete layer "%s" of d\n'
            'end try\n'
            'return "ok"' % _escape(layer_name))
    return run(_tell(bundle_id, body))


def _escape(text):
    return str(text).replace("\\", "\\\\").replace('"', '\\"')\
                    .replace("\n", "\\n")


# ---------------------------------------------------------------------------
# Applying a fit, and checking it landed
# ---------------------------------------------------------------------------
#
# Pixelmator's own text metrics are not quite AppKit's — the glyph heights
# match, but line spacing is looser and each line runs about 57px wider, and
# neither is settable from a script (rich text exposes only color, font and
# size, and size is an INTEGER). Predicting the difference exactly would mean
# reverse-engineering someone else's typesetter and being wrong again the next
# time it changes.
#
# So the fit is predicted, then MEASURED: the layer is exported on its own,
# its ink compared against the shape, and the size dropped a point at a time
# until nothing is outside. It costs a second or two on Apply, and it is the
# only version of "the text is inside the shape" that is actually a fact.

VERIFY_STEPS = 10
# The prediction lands within a point or two, so starting a shade under it
# usually makes the first attempt the only one.
OPENING_SHRINK = 0.97


def apply_fit(bundle_id, shape, fit, text, font_name, angle, mask_path,
              color=(255, 255, 255), name="Fitted Text", padding=0,
              calibration=None, on_step=None, on_probe=None):
    """Place the text, measure where it really landed, and correct it.

    Two different errors can leave ink outside the shape, and they need
    opposite fixes:

      * the text came out BIGGER than predicted  -> shrink it
      * the text came out the right size but in the wrong PLACE -> move it

    Telling them apart matters. Shrinking a mispositioned block does
    eventually work, by buying enough slack that the error stops mattering —
    but it took ten round trips and cost 10pt of size to fix a 6px offset.
    So the offset is measured from the drawn ink and applied as a nudge, and
    the size is only reduced when the ink is genuinely too big.

    Returns (size_used, escaped_pixels, attempts, lines_lost, box_width).
    """
    import numpy as np
    import fittext_engine as engine

    size = max(6, int(fit.size * OPENING_SHRINK))
    placement = fit
    nudge = [0.0, 0.0]
    escaped = 0
    lost = 0
    nudges = 0
    corrected = False

    for attempt in range(1, VERIFY_STEPS + 1):
        if on_step:
            on_step(attempt, size)
        position = (placement.layer_position[0] + nudge[0],
                    placement.layer_position[1] + nudge[1])
        # A flowed layout only survives the trip if its own line breaks go
        # with it — Pixelmator would otherwise re-wrap the words to a
        # rectangle and lose the shape entirely.
        lines = getattr(placement, "lines", None)
        payload = "\n".join(lines) if lines else text
        delete_layer(bundle_id, name)
        # Wide enough that Pixelmator will not re-wrap the lines we chose,
        # measured from the LONGEST LINE at this size. The layout's own box
        # width is no good here: a flowed layout is composed on a canvas the
        # size of the whole document, so it reported 2137px for a 459px
        # shape.
        box = _box_for(engine, lines, text, font_name, size, calibration)
        # The position names where the INK should go, but it sets the box's
        # left edge — and the ink sits centred inside a box deliberately
        # much wider than the line. Without taking that back out, widening
        # the box in 2.6.2 shoved every layout ~110px right of where it was
        # fitted, which the loop then read as oversized (drawn/model 1.22,
        # over the 1.02 threshold) and answered by shrinking on every pass
        # instead of ever nudging, down to the 6pt floor.
        mask_h, mask_w = placement.text_mask.shape
        align_now = getattr(placement, "align", "center") if lines else None
        if align_now == "center":
            inset = max(0.0, (box - mask_w) / 2.0)
        elif align_now == "right":
            inset = max(0.0, float(box - mask_w))
        else:
            inset = 0.0
        position = (position[0] - inset, position[1])
        add_text_layer(bundle_id, payload, font_name, size, angle, position,
                       color=color, name=name,
                       align=getattr(placement, "align", "center") if lines
                       else None, box_width=box)
        export_layer_mask(bundle_id, name, mask_path)
        actual = engine.load_shape(mask_path, fill_interior=False)
        escaped = int((actual & ~shape).sum())

        ys, xs = np.nonzero(actual)
        drawn_w = float(xs.max() - xs.min() + 1) if ys.size else 0.0
        drawn_h = float(ys.max() - ys.min() + 1) if ys.size else 0.0
        # How many separate bands of ink Pixelmator drew. If that is fewer
        # than the number of lines we sent, our breaks did not survive and
        # text has been LOST — the layer looks tidy and is missing words.
        #
        # This used to be computed only to log it, and the pass was declared
        # a success on `escaped == 0` alone. A 1.43in arch asked to hold 317
        # characters logged "lines drawn=5 sent=7", escaping 0, and reported
        # done: two lines silently gone. Counting bands is reliable — the
        # same text rendered here gives 7 bands for 7 lines at every size
        # from 6pt up — so a shortfall is real and must fail the pass.
        rows = actual.any(axis=1).astype(np.int8)
        drawn_lines = int(np.clip(np.diff(np.concatenate(
            ([0], rows, [0]))), 0, None).sum())
        sent_lines = len(lines) if lines else 1
        if on_probe:
            on_probe(attempt, size, box, position, drawn_w, drawn_h,
                     mask_w, mask_h, drawn_lines, sent_lines, escaped)
        # Either direction is a failure. Fewer bands than lines means text
        # vanished; MORE means Pixelmator re-broke the layout, so what got
        # drawn is not what was verified. Checking only for "fewer" let a
        # re-wrap through as a success with 43px hanging outside the shape.
        drift = drawn_lines - sent_lines
        lost = -drift if drift < 0 else 0
        if escaped == 0 and drift == 0:
            box = _tighten_box(bundle_id, engine, shape, payload, font_name,
                               size, angle, position, color, name, align_now,
                               box, sent_lines, mask_path)
            return size, 0, attempt, 0, box
        if ys.size == 0:
            break

        # Correct the model from what was really drawn — ONCE. Re-correcting
        # on every failure made the size swing 15, 16, 15, 16 and never
        # settle: each correction changes the mask, which changes the next
        # measured ratio, which undoes the correction.
        if calibration is not None and not corrected and mask_w and mask_h:
            corrected = True
            calibration = engine.Calibration(
                calibration.width_factor * (drawn_w / mask_w),
                calibration.height_factor * (drawn_h / mask_h),
                calibration.text, calibration.font)
            better = engine.fit_text(
                shape, "\n".join(lines) if lines else text, font_name,
                angle=angle, padding=padding, calibration=calibration,
                align=getattr(placement, "align", "center"))
            if better is not None:
                if lines:
                    better.rendered.lines = lines
                    better.rendered.align = getattr(placement, "align",
                                                    "center")
                # Never allow a retry to grow: every pass must move down, or
                # ten passes can end no closer than they started.
                new_size = min(int(better.size), size - 1)
                if new_size >= 6:
                    placement = better
                    size = new_size
                    nudge = [0.0, 0.0]
                    nudges = 0
                    continue

        overshoot = max(drawn_w / max(mask_w, 1), drawn_h / max(mask_h, 1))
        if nudges >= 2:
            overshoot = max(overshoot, 1.03)
        if overshoot > 1.02:
            size = max(6, min(int(size / overshoot), size - 1))
            smaller = _refit(engine, shape, text, font_name, angle, padding,
                             size, calibration, placement)
            if smaller is not None:
                placement = smaller
                nudge = [0.0, 0.0]
                nudges = 0
        else:
            # Align CENTRES, not top-left corners. The drawn ink is a
            # little smaller than the mask it is being matched to once the
            # size has come down, so corner-aligning collects all the slack
            # at the bottom-right — the text sat 24px high and 10px left,
            # with an 83px bottom margin against a 36px top.
            dx = ((placement.x + mask_w / 2.0)
                  - (float(xs.min()) + drawn_w / 2.0))
            dy = ((placement.y + mask_h / 2.0)
                  - (float(ys.min()) + drawn_h / 2.0))
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                size = max(6, size - 1)
                smaller = _refit(engine, shape, text, font_name, angle,
                                 padding, size, calibration, placement)
                if smaller is not None:
                    placement = smaller
                    nudge = [0.0, 0.0]
                    nudges = 0
            else:
                nudge[0] += dx
                nudge[1] += dy
                nudges += 1
        if size < 6:
            break
    return size, escaped, VERIFY_STEPS, (lost or drift), box


def _tighten_box(bundle_id, engine, shape, payload, font_name, size, angle,
                 position, color, name, align, box, sent_lines, mask_path):
    """Shrink the settled layer's box to something near its own text.

    _box_for deliberately asks for a box MUCH wider than the longest line,
    so that Pixelmator cannot re-wrap the lines the fit chose. That is the
    right thing to do while the size is still moving. What it leaves behind
    is a finished layer whose box is several times the width of the shape —
    413 units of box around 175 units of text on a 207-unit arch — so the
    ink sits centred in something far wider than the artwork and has to be
    dragged back over the shape by hand every time.

    The width is found by trying, not by formula: the relationship between
    the box we ask for and what Pixelmator does with it has already caught
    this code out twice. Each candidate is drawn and re-measured, and a
    candidate is only accepted if the line count and the escape count are
    both still what they were. Anything else keeps the wide box, which is
    known to work.
    """
    import numpy as np
    best = box
    for fraction in (0.55, 0.40, 0.30):
        trial = int(box * fraction)
        if trial < 40 or trial >= best:
            continue
        delete_layer(bundle_id, name)
        add_text_layer(bundle_id, payload, font_name, size, angle, position,
                       color=color, name=name, align=align, box_width=trial)
        export_layer_mask(bundle_id, name, mask_path)
        drawn = engine.load_shape(mask_path, fill_interior=False)
        if not drawn.any():
            break
        rows = drawn.any(axis=1).astype(np.int8)
        drawn_lines = int(np.clip(np.diff(np.concatenate(
            ([0], rows, [0]))), 0, None).sum())
        escaped = int((drawn & ~shape).sum())
        if drawn_lines == sent_lines and escaped == 0:
            best = trial
        else:
            break                       # narrower will only be worse
    if best != box:
        delete_layer(bundle_id, name)
        add_text_layer(bundle_id, payload, font_name, size, angle, position,
                       color=color, name=name, align=align, box_width=best)
    return best


def _box_for(engine, lines, text, font_name, size, calibration):
    """How wide the text layer must be to hold its longest line unbroken."""
    candidates = lines or text.split("\n")
    widest = 0
    for line in candidates:
        if not line.strip():
            continue
        widest = max(widest, engine.text_mask(line, font_name, size,
                                              0.0).mask.shape[1])
    factor = calibration.width_factor if calibration else 1.0
    # MUCH wider than the line needs, deliberately. The box has exactly one
    # job: stop Pixelmator re-wrapping the lines the fit chose. Too wide
    # costs a single nudge, which the verify loop performs anyway, because
    # it positions by MEASURED ink. Too narrow silently returns a different
    # layout — "lines drawn=20 sent=19" — and then every pass measures
    # something else and the correction never settles.
    #
    # 1.10 was still not enough, because the width ratio is size-dependent:
    # measured 1.031 at the 72pt probe, but at 12pt Pixelmator draws 10%
    # wider than the model, per-glyph advances rounding to whole pixels
    # being proportionally far larger down there.
    return int(widest * factor * 1.45 + 160)


def _refit(engine, shape, text, font_name, angle, padding, size,
           calibration, previous):
    """Re-fit at a smaller size, KEEPING the breaks already chosen.

    Re-flowing here was the mistake. fit_flowed picks fresh breaks for each
    new size, so every verify pass measured a different layout — 5 lines,
    then 4, then 3 — while the width correction learned from the five-line
    layout was applied to the four-line one. It never converged, and once
    the box no longer matched the lines being sent, Pixelmator re-wrapped
    them itself and stranded a word on its own line. The breaks are the
    fit's decision; the verify loop only gets to change the size.
    """
    align = getattr(previous, "align", "center")
    lines = getattr(previous, "lines", None)
    smaller = engine.fit_text(shape, "\n".join(lines) if lines else text,
                              font_name, angle=angle, padding=padding,
                              min_size=float(size), max_size=float(size),
                              calibration=calibration, align=align)
    if smaller is not None and lines:
        smaller.rendered.lines = lines
        smaller.rendered.align = align
    return smaller


# Fixed probes. The two numbers being measured are properties of the FONT,
# not of the sentence: how much wider Pixelmator sets a line, and how much
# looser its line spacing is. Measuring them from the user's own text meant a
# fresh probe — and a fresh flash of text across their canvas — every time
# the wording changed. Fixed probes mean one measurement per font, ever.
# The probe has SPACES in it, and is long. A single word measured the
# ratio at 1.0257 one day and 1.0073 the next — the difference being which
# kind of export came back, since anti-aliased edge pixels survive one and
# not the other. Real sentences measured 1.0318 and 1.0329 in the same run:
# a long probe averages the edge effects out, and word gaps are part of what
# is being measured, since real lines are made of words.
WIDTH_PROBE = "Hamburgefonstiv and the quick brown fox jumps over it"
SPACING_PROBE = "\n".join([WIDTH_PROBE] * 3)
PROBE_LAYER = "PixProFitText calibration"


def calibrate(bundle_id, text, font_name, mask_path, reference=100.0):
    """Measure Pixelmator's typesetting against AppKit's, for this font.

    Done in a SCRATCH DOCUMENT, not the user's. Measuring means drawing a
    probe and exporting it, and doing that in the open document flashed a
    line of nonsense across their artwork and — worse — moved the layer
    selection, because creating a layer selects it and deleting it leaves the
    selection somewhere else. Neither is acceptable for something the app
    does on its own initiative.

    `text` is accepted only so the result can be tagged with it; the
    measurement uses fixed probes so it can be cached per font.
    """
    import numpy as np
    import fittext_engine as engine

    probe_size = 72.0
    widest = max(engine.text_mask(p, font_name, probe_size, 0.0).mask.shape[1]
                 for p in (WIDTH_PROBE, SPACING_PROBE))
    tallest = engine.text_mask(SPACING_PROBE, font_name, probe_size,
                               0.0).mask.shape[0]
    doc_w, doc_h = int(widest + 120), int(tallest + 120)

    scratch_name = "PixProFitText measuring"
    run(_tell(bundle_id,
              'make new document with properties '
              '{name:"%s", width:%d, height:%d}' % (scratch_name, doc_w, doc_h)))
    try:
        def measure(probe):
            body = ('tell document "%s"\n'
                    '  set t to make new text layer at the beginning of layers '
                    'with properties {text content:"%s"}\n'
                    '  tell text content of t\n'
                    '    set its font to "%s"\n'
                    '    set its size to %d\n'
                    '    set its color to {255, 255, 255}\n'
                    '  end tell\n'
                    '  set name of t to "probe"\n'
                    '  set position of t to {20, 20}\n'
                    '  delay 0.1\n'
                    'end tell\n'
                    'export document "%s" to POSIX file "%s" as PNG\n'
                    'delete layer "probe" of document "%s"\n'
                    'return "ok"'
                    % (_escape(scratch_name), _escape(probe),
                       _escape(font_name), int(probe_size),
                       _escape(scratch_name), _escape(mask_path),
                       _escape(scratch_name)))
            run(_tell(bundle_id, body))
            # By DARKNESS, not alpha: this is a flattened document export,
            # so every pixel is opaque and an alpha test returns the whole
            # canvas. It did exactly that — both probes measured 900x600,
            # so the pitch subtraction gave a height factor of ZERO and the
            # width ratio was canvas-over-text (1.22 instead of ~1.07).
            drawn = engine.dark_ink(mask_path)
            ys, xs = np.nonzero(drawn)
            if ys.size == 0:
                return None
            rendered = engine.text_mask(probe, font_name, probe_size, 0.0)
            ink_h, ink_w = rendered.mask.shape
            scale = reference / probe_size
            return (float(xs.max() - xs.min() + 1) * scale,
                    float(ys.max() - ys.min() + 1) * scale,
                    float(ink_w) * scale, float(ink_h) * scale)

        one = measure(WIDTH_PROBE)
        three = measure(SPACING_PROBE)
    finally:
        run(_tell(bundle_id,
                  'try\n  close document "%s" without saving\nend try\n'
                  'return "ok"' % _escape(scratch_name)))

    if one is None or three is None:
        return engine.Calibration(1.0, 1.0, text, font_name)

    # Line spacing has to be measured as the PITCH between lines, not as the
    # height ratio of a block. A block's ratio depends on how many lines it
    # has — the glyph height of the first line is shared, so a 3-line probe
    # gives a smaller ratio than a 7-line body of text, and text calibrated
    # on three lines came out 8% short on seven. Subtracting the one-line
    # probe from the three-line one leaves two line pitches and no glyphs.
    app_pitch = (three[3] - one[3]) / 2.0
    pix_pitch = (three[1] - one[1]) / 2.0
    factor = (pix_pitch / app_pitch) if app_pitch > 0 else 1.0
    width = (one[0] / one[2]) if one[2] > 0 else 1.0
    return engine.Calibration(width, factor, text, font_name)

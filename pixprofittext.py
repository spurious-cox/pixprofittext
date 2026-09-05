#!/usr/bin/env python3
"""
PixProFitText — fit text inside an irregular shape in Pixelmator Pro.
Version: 1.0.0

Pick a shape layer in Pixelmator, type the text, choose a font and an angle,
and the app finds the largest point size at which the whole text sits inside
that shape — then puts it there as a real, editable text layer.

The preview is computed from AppKit's metrics, which are close to
Pixelmator's but not identical, so it is honest about being a preview. Apply
does the real thing and then MEASURES it: the finished layer is exported on
its own and its ink compared against the shape, correcting position or size
until nothing is outside. "Inside the shape" is a fact it checks, not a
calculation it trusts.

2.7.3  The panel says where to find it again — "Info, next to Exit" —
       so dismissing it with "Don't show this again" is not a one-way door.
2.7.2  The Info button says "Info". It was a ⓘ glyph on a rounded
       button, 30px wide, sitting between Exit and the shape name — present,
       but small enough that Tim looked straight past it. A word is not
       ambiguous.
2.7.1  The Info panel names the Text panel controls worth reaching for,
       rather than mentioning spacing alone. The controls listed are the
       ones actually in Pixelmator's Text panel — alignment both ways,
       Line Height, Before and After Paragraph, Indents, and the two
       Convert buttons — not a guess at what a text panel usually holds.
2.7.0  An Align control: Auto, Left, Center, Right. Auto keeps the old
       behaviour — the justification is read off the shape by comparing how
       much the left and right edges wander — but it is a heuristic, and on
       the flag it has now been seen to answer both ways. Measured directly
       on that shape's mask it says LEFT (left edge std 0.0 against right
       edge std 66.9) and fit_flowed reproduces LEFT end to end, yet a run
       logged center. Rather than keep tuning a guess, the choice is now
       overridable and the log records which was used.
2.6.3  Put the text back where it was fitted. 2.6.2 widened the box but
       did not take the extra width back out of the position, and the
       position sets the box's LEFT EDGE while centred ink sits in the
       middle of it — so every layout landed ~110px right of where it
       belonged. The loop read that as oversized and shrank on all ten
       passes rather than nudging once, ending at the 6pt floor still
       379px outside. The inset is now subtracted for centre and right
       alignment, which is what made a tight box work before.
2.6.2  The text box is much wider than the line it holds. It was still
       re-wrapping at 1.10 — "lines drawn=20 sent=19" on passes 3 and 5
       of a five-pass Apply that fell from a predicted 12.6pt to 8pt.
       The box has one job, which is to stop Pixelmator re-wrapping the
       lines the fit chose; too wide costs a single nudge the loop
       performs anyway, since it positions by MEASURED ink, while too
       narrow makes every pass measure a different layout so the
       correction never settles.

       The reason 1.10 was not enough is that the width ratio is SIZE
       DEPENDENT: 1.031 measured at the 72pt probe, but 10% at 12pt,
       because per-glyph advances round to whole pixels and that
       rounding is proportionally far larger at small sizes. The
       one-time correction in apply_fit is what absorbs the remainder.

       Also: the Info panel says "Text panel", which is what Pixelmator
       calls it. It said "Format panel".
2.6.1  Applied text stopped matching the preview: every long line lost
       its last word to a line of its own ("they", "about this,"). Two
       causes, both about width. The calibration probe was a single word,
       and measured 1.0257 one day and 1.0073 the next depending on which
       kind of export came back — while real sentences measure 1.032. The
       probe is now a long line WITH SPACES, which averages the edge
       effects out and measures the word gaps that real lines are made of.
       And the text box was the line's ink width plus a flat 60px, which
       is not enough at 13pt; it is now proportional. A box slightly too
       wide costs one nudge the verify loop already performs. A box
       slightly too narrow makes Pixelmator re-wrap, and what comes back is
       not the layout that was fitted. Cache key moves to 6.
2.6.0  An Info panel, shown once on first run and available from the ⓘ
       button beside Exit thereafter. It says what the app promises and
       what it does not: the fit is calculated as well as it can be for
       whatever shape it is given, and the text it places stays editable —
       spacing and line height are still yours to adjust afterwards. That
       last part matters because line spacing is not scriptable at all, so
       adjusting it by hand is not a workaround, it is the intended finish.
2.5.2  The calibration probe is found by OPAQUE AND DARK, because 2.5.1
       was only half a fix. Pixelmator's document export is sometimes
       opaque and sometimes transparent, and each case defeats the other
       test the same way — by reporting the whole canvas. Alpha alone fails
       on an opaque export; darkness alone fails on a transparent one,
       since convert("L") renders transparent pixels black. 2.5.1 measured
       correctly the day it was written and produced the identical wrong
       numbers (x1.2202 wide, x0.0000 tall) the next day, on an export that
       happened to come back transparent. Requiring both is stable whichever
       one turns up.

       The cache key moves to 5. It has to: ensure_calibration returns
       early whenever the font is already cached, so the wrong pair 2.5.1
       stored under key 4 would never have been re-measured — 2.5.2 would
       have read it straight back and behaved exactly like 2.5.0.
2.5.1  The calibration measures the probe again, not the canvas. It read
       the exported PNG through its ALPHA channel, but Pixelmator's
       whole-document export is opaque, so both probes came back as the
       full canvas — 900x600 each. Identical heights meant the line-pitch
       subtraction produced a height factor of 0.0000, and the width ratio
       was canvas-over-text, 1.22. Measured by darkness instead, which is
       what actually distinguishes near-black probe text on white. Not new
       breakage: the cached +4px/x1.4405 predated a Pixelmator that
       exported transparency, and the cache meant calibrate never re-ran
       until 2.5.0 bumped the key. The verify loop was never affected —
       export_layer_mask solos the layer, so alpha means something there.
2.5.0  Two fixes for text that applied far smaller than it previewed —
       43pt previewed, 13pt applied, six shrinking passes.

       Pixelmator's extra WIDTH is a factor, not a constant offset. The
       measured +4px was right at the size it was probed and 28px short at
       42pt: drawn 450 against a predicted 422, 6.6% over, 363px outside
       the shape. Proportional all along; invisible at 8-16pt, which is
       every fit that had worked.

       And the verify loop no longer re-flows. _refit called fit_flowed,
       which chose fresh line breaks at each smaller size, so the passes
       sent 5 lines, then 4, then 3 — with a width correction learned from
       the five-line layout being applied to the four. Once the box stopped
       matching the lines, Pixelmator re-wrapped them itself and stranded a
       word alone ("conform"). The loop now varies only the size.

       Calibrations are re-measured: the stored numbers changed meaning,
       so the cache key moves to 3.
2.4.1  Logging only, no behaviour change. Each verify pass now records
       the box width it asked for, where it put the layer, the ink
       Pixelmator actually drew against the ink the model predicted, and
       how many separate bands of ink came back versus how many lines were
       sent. That last pair is the point: if they disagree, our line breaks
       are not surviving the trip and the text box is re-wrapping them.
2.4.0  The applied angle matches the previewed angle. Pixelmator's
       `rotation` is counter-clockwise-positive and the engine's
       rotate_mask is clockwise-positive — measured in a scratch document,
       rotation +22 rises to the right and rotate_mask(+22) falls to the
       right, both at slope 0.403. Same magnitude, opposite sign, so a
       -22° preview produced a layer leaning the other way, 44° out. The
       angle is now negated where it crosses into AppleScript. apply_fit
       had no chance of catching it: it only asks whether ink escapes the
       shape, and on a roughly symmetric shape the mirrored angle fits
       just as well.

       Also a title bar that says what this is: version on the left,
       name and icon centred, copyright on the right.
2.3.0  Margin defaults to a proportion of the shape instead of a flat 6.
       6 was a number I picked because it looked right on the first shape;
       nothing measured it. It cannot be right in general either, being an
       absolute pixel count read against shapes of any size — 6px of
       clearance is a visible band on a 400px chevron and invisible on a
       4000px canvas. It is now MARGIN_FRACTION of the shape's smaller
       side, worked out when the shape is read, so it scales with the
       document. The box stays: a notched or spiky outline wants more than
       any formula gives, because near a point the boundary closes in from
       two sides at once. Type or step it and your value is kept for the
       rest of the session; it is no longer saved between runs, because a
       margin carried over from a differently-sized document would be
       overridden by the shape anyway and a setting nothing honours is a
       trap.

       Spacing is gone. The idea was to fit smaller so there was room to
       loosen the line spacing by hand afterwards, since Pixelmator exposes
       no spacing property to scripting. It cannot work in shape-following
       mode: each line's LENGTH is chosen for the row it sits on, so
       inflating the model spreads the lines onto rows 30% further down the
       shape than where Pixelmator actually draws them. A line sized for a
       wide row lands in the notch. That is a line-pitch error, not a scale
       error, so shrinking never clears it — the flag went ten passes down
       to 6 pt still 216 px outside, where the same shape at Spacing 1.00
       applied clean in one pass. Removed rather than left as a trap. The
       stored setting is dropped on load so an old 1.30 cannot linger
       invisibly. Margin, and its stepper, stay.
2.2.1  Apply no longer collapses when Spacing is above 1.00. Apply
       corrects its model once from what Pixelmator really drew, as
       height_factor * (drawn_h / mask_h) — and with Spacing 1.30 that
       mask is DELIBERATELY 30% taller than what gets drawn, so the ratio
       came back at 0.77 and the loop read the headroom as a calibration
       error. It rewrote the model with it and shrank to compensate: a
       10.4 pt fit landed at 7 pt. Apply is now told the headroom and
       scales drawn_h by it before the comparison, so both sides measure
       the same thing, and it is handed the same inflated calibration the
       fit used so its own refit keeps the headroom rather than eating it.
2.2.0  Steppers on Margin (1 px a click) and Spacing (0.05 a click).
       Typing in either box still works and moves its stepper with it, so
       the two never disagree. The "px" label went to make room — the row
       had reached the right edge of the window — and is now a tooltip.
2.1.1  White (and every other colour picked from the Crayons or Color
       Palettes tabs) no longer arrives as black. Those tabs hand back an
       NSCatalogColor, and the deprecated name-based conversion
       colorUsingColorSpaceName_("NSCalibratedRGBColorSpace") returns None
       for one — the code then fell back to black. Worse, that black was
       written to the plist, so the next launch started black and picking
       white again just repeated the failure: the colour looked stuck.
       Now converts with colorUsingColorSpace_, which handles catalog,
       grayscale and pattern-free colours, and clamps: the wide-gamut
       sliders can return components above 1.0, which would have overflowed
       past 65535 once Pixelmator's x257 scaling was applied.
2.1.0  A Spacing box, for looser line spacing. Pixelmator's line spacing
       is not scriptable — there is no leading, spacing, kerning or tracking
       property anywhere in its dictionary — so the app cannot set it. What
       it CAN do is leave room for it: fit as though every line were that
       much taller, so the text still fits once the spacing is opened up by
       hand in the Format panel afterwards. 1.0 fits tight, as before.
2.0.2  The chosen colour is actually applied. AppleScript colour channels
       are 0-65535, not 0-255, so every colour was sent at 1/257th of its
       value and arrived as near-black — red (255,0,0) read back as
       (254,0,0). The colour well was working the whole time; the number
       leaving the app was wrong.
2.0.1  The chosen justification now reaches the FITTING, not just the
       output. 2.0.0 told Pixelmator to left-justify the flag but still
       measured a centred block, so the preview showed centred text and
       the document got smaller left-justified text — two different
       arrangements. Sizing what will actually be drawn takes the flag
       from 15.7pt to 19.2pt, and makes the preview true again.
2.0.0  The SHAPE chooses the justification, which is what makes the
       notched flag work. A shape with a straight left edge and a ragged
       right one — a pennant — wants left-justified text; centring throws
       away the whole straight side. Measured as the variation in each
       edge across the rows: the flag reads 0.000 left against 0.139
       right, the diamond 0.141 against 0.141. The flag goes from 9.5pt to
       15.7pt; symmetric shapes are unchanged.

       Also moves the shape label clear of the Exit button, which was
       sitting on top of it.
1.9.5  No behaviour change. Two attempts at the notched-flag case were
       tried and both made it worse, so both were reverted and the reasons
       written down where the next person will look:
         * Constraining every flowed line to the shape's centre axis, so a
           centred text layer could reproduce the flow exactly. Costs more
           width than the conversion does: flag 9.5pt -> 7.3pt.
         * Flowing at the MEASURED line spacing instead of a tight 1.15.
           Fits fewer lines, so the flow settles smaller and hands the
           block fit worse breaks: flag 9.5 -> 8.2, diamond 15.8 -> 13.7.
       The axis option is kept, off by default, for a future mode that
       applies each line as its own layer.
1.9.4  Layer visibility is restored BY LAYER ID. Reading a shape means
       hiding every other layer, exporting, and putting them back — and the
       putting-back matched saved states to layers by POSITION in a list
       walked twice. Anything that shifted the layer set between the two
       walks gave every layer somebody else's state, which is how a run on
       the crown left most of the document switched off. Ids survive
       reordering and insertion; positions do not. Each restore is its own
       try, so one stubborn layer cannot strand the rest hidden.
1.9.3  The flow chooses where to START, not just how to wrap. Laying lines
       from the shape's topmost row put the block's widest lines above the
       shape's widest band: on a diamond that left 36px above and 83px
       below — inside the shape, but visibly not centred in it. Trying a
       few starting rows and keeping the most balanced gives 61/62, and
       makes the text BIGGER (14pt to 15.8pt), because it can now use the
       wide middle instead of the point.
1.9.2  The placement correction aligns centres rather than top-left
       corners. Once the size has been reduced the drawn ink is smaller
       than the mask it is matched against, so corner-aligning pushed the
       text up and left and left all the slack at the bottom right — a
       36px top margin against 83px at the bottom.
1.9.1  The model is corrected ONCE, and every pass must move down. 1.9.0
       re-corrected on each failure, and the size swung 15, 16, 15, 16 for
       ten passes and finished with 1267 pixels outside the shape: each
       correction changed the mask, which changed the next measured ratio,
       which undid the correction. Correcting once and never letting a
       retry grow settles the 22-line case in two passes.
1.9.0  When a verification pass fails, the measurement is used to correct
       the FONT MODEL and the fit is redone — rather than taking a point
       off and trying again. The calibration comes from a three-line probe
       and its small per-line error multiplies by the line count: at 22
       lines it overflowed, and the old loop crawled 15pt -> 7pt over ten
       passes without ever learning why. One look at what was really drawn
       fixes the model for that text.
1.8.3  Writes a log of every Try and Apply to
       ~/Library/Logs/PixProFitText.log — the settings that went in, the
       fit that came out, each verification pass and the final layer size.
       A fit that fails on Tim's machine and succeeds on mine is not
       something to reason about from screenshots.
1.8.2  Apply runs on the main thread. It was running on a background
       thread so the window would stay live, but the fitting it does there
       renders text through AppKit — and AppKit text layout is not
       thread-safe. The measurements it took off-thread disagreed with the
       ones the preview took on it, so Apply kept deciding the text did not
       fit and shrinking it, while the preview of the very same fit was
       perfect. It blocks for a couple of seconds now, which is honest.
1.8.1  The preview draws in the colour that will be used, and Apply stops
       shuffling text that is simply too wide. Nudging can only correct an
       OFFSET — moving text that overflows by 1.7% just moves the overflow
       to the other side — so two fruitless nudges now force a size
       reduction instead of burning every pass.
1.8.0  Settings are remembered between runs — font, face, angle, margin,
       colour, layout and the text itself — written after every Try and
       Apply, so the app opens where it was left rather than back at
       Helvetica Neue at 0 degrees.

       Also stops the colour picker recolouring the TEXT BOX. The colour
       panel sends changeColor: down the responder chain and an NSTextView
       obligingly applies it to its own contents, so picking a colour
       restyled the editor and changed nothing about the output. The editor
       now declines it; the colour belongs to the layer that gets made.
1.7.2  Remembered font measurements are versioned. 1.7.0 changed how line
       spacing is measured — per-line pitch instead of a block's height —
       but the old, wrong number was already saved under the same key, so
       an existing install kept using it: Apply under-predicted and shrank
       the text pass after pass. Changing the way something is measured
       has to invalidate what was measured the old way.

       Also: the Colour label was printing over the degree sign as "ofour",
       and is now "Color", which is the spelling Tim uses.
1.7.1  The colour panel no longer opens by itself. An NSColorWell that
       becomes first responder ACTIVATES, and an active colour well opens
       the system colour picker — so the window came up with the picker in
       front of it. The well now refuses first responder and the text box
       gets the focus, which is where typing should go anyway.
1.7.0  Closing the window quits, and an Exit button does it from
       anywhere. Closing while there is unapplied work asks first — the
       whole point of the window is the Apply at the end of it, and
       quitting one keystroke away from that with no warning loses the fit.

       Line spacing is measured as the PITCH between lines rather than the
       height of a probe block. A block's height ratio depends on how many
       lines it has, so text calibrated on a three-line probe came out 8%
       short on seven — and Apply spent six passes shrinking 43pt text to
       24pt chasing it.
1.6.0  Each fit gets its own layer, named after the shape it went into,
       so filling one shape after another no longer destroys the earlier
       ones — every Apply used the same layer name and deleted the previous
       result before writing its own.

       Also stops the applied text re-wrapping and shrinking. A scripted
       text layer is given an automatic box width; any line longer than it
       is re-wrapped by Pixelmator, which breaks a shaped layout, fails the
       check, and sends the retry loop shrinking until it gives up — 19px
       text in a 459px shape. The box is now made wide enough for the
       longest line.
1.5.1  Measuring a font happens in a scratch document now, not in the
       user's. It drew a probe line across their artwork — and moved the
       layer selection, because creating a layer selects it and deleting it
       leaves the selection somewhere else, so the shape they had just
       chosen quietly stopped being chosen. Nothing the app does on its own
       initiative should touch either.
1.5.0  Selecting a shape now works for every kind of shape, and saying
       nothing is selected is no longer done by quietly using a different
       one. "shape layer" is only one of Pixelmator's shape classes — a
       rounded rectangle is a "rounded rectangle shape layer" — so picking
       the diamond matched nothing and the app fell back to the first shape
       in the document. It now matches on the class name, and asks for a
       shape rather than guessing.

       Also fixes "will not fit, even at 6 pt" on short text. The rule that
       stops a column of single words rejects any layout not using a fair
       share of the shape's width, which SHORT text cannot do at small
       sizes — and the size search bisected from the bottom, so one
       rejection at 6 pt ended the search. It scans from the top now.
1.4.0  A font is measured once, ever. The measurement means creating and
       deleting a real text layer, which flashes across the document — and
       it was happening every time the wording changed, because the
       calibration was keyed on the text. Both numbers are properties of
       the TYPEFACE, so they are now taken from fixed probes and remembered
       between launches. First use of a font flashes once; nothing after
       that does.
1.3.2  Three faults behind "Try gives a column of blobs":
         * The calibration probe was drawn at 100pt and EXPORTED, and an
           export is clipped to the canvas — so a probe wider than the
           document measured short, which read as "Pixelmator sets this
           narrower" and squashed every line. The probe is now scaled to
           fit the canvas first.
         * The measured height difference is line SPACING, not taller
           glyphs, but it was applied as a vertical scale of the finished
           block — stretching every letterform until the lines merged. It
           now goes into the paragraph style before anything is drawn.
         * The preview drew the DILATED mask, which is the text plus its
           margin; at 6px the letters merge into bars. The margin is used
           for the placement test only; the preview shows the real ink.
       And dilate() grew the mask in place, clipping the margin against the
       mask's own edge — the one place it was needed.
1.3.1  Changing the font no longer touches the document. Measuring how
       Pixelmator sets the text means creating and deleting a real text
       layer, and that was being done from the font popup — text flashing
       up in the document from a menu the user only browsed. Only Try and
       Apply reach into Pixelmator now.

       Also stops the flow choosing a column of single words. It maximised
       point size, and a tall shape almost always has a narrow strip clear
       from top to bottom, so one huge word per line beat any sensibly
       filled layout. The longest line must now use a fair share of the
       widest opening the shape offered.
1.3.0  A colour well. The text was forced to white, which is invisible on
       a pale shape and was never a sensible default. The layer stays a
       normal editable text layer either way — the colour can still be
       changed in Pixelmator afterwards — but there is no reason to make
       that a required second step.
1.2.1  Apply now produces what Try showed. The flowed preview was drawn
       with AppKit's metrics and never went through the Pixelmator
       calibration, so the layer came out about a quarter larger per line,
       offset, and overflowing — and the retry loop just shrank it until it
       gave up. The flow now decides only the LINE BREAKS; those lines are
       then sized and placed by the calibrated fitter, which knows what
       Pixelmator's typesetter will really do. Try measures the font once,
       so the preview and the result agree.
1.2.0  Text follows the shape. Instead of the largest rectangle that fits,
       each line is measured against the width the shape actually has at
       that height, so the lines run short across the dome, wide across the
       middle and short again at the base — and the justification comes out
       of the shape rather than being chosen. Also fixes text coming out
       right-aligned: NSTextAlignment is left=0, CENTRE=1, right=2, and the
       old NSCenterTextAlignment=2 silently meant "right".
1.1.0  A menu bar, so Cut/Copy/Paste work in the text box — without one
       there is nothing for Cmd-V to route to, and the field silently
       refuses to paste.  Fitting no longer happens on every keystroke: a
       paragraph takes a couple of seconds to fit, which made typing
       unusable.  The Try button asks for it instead.

Created by: Claude (Anthropic) for Tim McCoy

v2.8.0 fixes three things found while a 1.43 x 0.95in arch refused to hold
317 characters at anything above the 6pt floor:

  * A pass that LOST lines was reported as a success. The verify loop asked
    only whether ink had escaped the shape; "lines drawn=5 sent=7" was
    logged and ignored, so two lines of scripture vanished and the app said
    it had verified the placement. Losing lines now fails the pass and says
    so in plain words.
  * Every button ignored the first click when the window was not key —
    AppKit spends that click activating the app, and NSButton declines
    acceptsFirstMouse. Coming back from Pixelmator, "Follow the shape"
    looked like a checkbox that randomly ignored you.
  * The cached calibration for HelveticaNeue-Bold had drifted to a height
    factor of 0.92 while Regular measured 1.48; every earlier generation of
    that cache had the two faces agreeing to within 0.2%.

Worth recording what was NOT wrong, because it cost an afternoon: the fitted
size itself. 317 characters in an arch that size honestly want about 6pt,
and both the flowed and the plain path agree on it to within 0.3pt. The
shape was too small for the text all along.
"""

APP_VERSION = "2.10.3"
COPYRIGHT = "© 2026 Tim McCoy"

import os
import sys
import threading
import time

import objc
from AppKit import (NSApplication, NSApp, NSBackingStoreBuffered, NSBezierPath,
                    NSBitmapImageRep, NSButton, NSColor, NSComboBox,
                    NSColorSpace, NSDeviceRGBColorSpace, NSFont,
                    NSFontManager, NSImage,
                    NSImageScaleProportionallyUpOrDown, NSImageView,
                    NSMakeRect, NSMakeSize, NSPopUpButton, NSScrollView,
                    NSLayoutAttributeLeft, NSLayoutAttributeRight,
                    NSMakePoint, NSSlider, NSStepper, NSTextField,
                    NSTextView, NSTitlebarAccessoryViewController,
                    NSView,
                    NSViewHeightSizable, NSViewMaxYMargin, NSViewMinYMargin,
                    NSAlert, NSColorPanel, NSColorWell, NSMenu, NSMenuItem,
                    NSWorkspace,
    NSViewWidthSizable, NSWindow, NSWindowStyleMaskClosable,
                    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
                    NSWindowStyleMaskTitled)
from Foundation import NSBundle, NSObject, NSThread, NSURL, NSUserDefaults

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fittext_engine as engine
import pixbridge as bridge

SCRATCH = os.path.expanduser("~/Library/Caches/PixProFitText")
DEFAULT_TEXT = "YOUR TEXT\nHERE"


def scratch(name):
    os.makedirs(SCRATCH, exist_ok=True)
    return os.path.join(SCRATCH, name)


LOG_PATH = os.path.expanduser("~/Library/Logs/PixProFitText.log")


def note(message):
    """Record what the app actually did, so a report can be checked rather
    than guessed at."""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%H:%M:%S"), message))
    except OSError:
        pass


class PassthroughLabel(NSTextField):
    """A label that lets clicks through to whatever is behind it.

    A non-editable NSTextField still hit-tests, and the status line — 560pt
    wide at y 50 — lies directly over the "Follow the shape" checkbox at
    y 46..66. It swallowed every click except the 4pt strip along the
    checkbox's bottom edge, so the box appeared to ignore the mouse at
    random and could be hit only by luck. Labels display; they should never
    take a click away from a control.
    """

    def hitTest_(self, point):
        return None


def _label(text, x, y, width=90):
    field = PassthroughLabel.alloc().initWithFrame_(NSMakeRect(x, y, width, 18))
    field.setStringValue_(text)
    field.setEditable_(False)
    field.setSelectable_(False)
    field.setBordered_(False)
    field.setDrawsBackground_(False)
    field.setFont_(NSFont.systemFontOfSize_(11))
    return field


class FirstMouseButton(NSButton):
    """A button that acts on the first click, even from another app.

    AppKit spends the first click on an inactive window activating it, and
    NSButton answers no to acceptsFirstMouse, so coming back from Pixelmator
    the click that should have toggled "Follow the shape" only brought this
    window forward. That reads as a checkbox ignoring you at random — and it
    behaved perfectly whenever the window already had focus, which is what
    made it look intermittent rather than broken.
    """

    def acceptsFirstMouse_(self, event):
        return True


class PlainTextView(NSTextView):
    """A text box that will not be restyled by the colour panel.

    The colour panel sends changeColor: to the first responder, and
    NSTextView applies it to its own text — so choosing the colour for the
    fitted text recoloured the editor instead, and nothing else. The colour
    here belongs to the layer that gets created, not to this field.
    """

    def changeColor_(self, sender):
        pass


SETTINGS_KEY = "PixProFitTextSettings"
SEEN_INTRO_KEY = "PixProFitTextSeenIntro"

# Auto reads the justification off the shape; the rest force it.
ALIGN_CHOICES = (("Auto", None), ("Left", "left"),
                 ("Center", "center"), ("Right", "right"))

INFO_TITLE = "PixProFitText"
INFO_BODY = (
    "We calculate, as best as possible, a fit for any shape you offer.\n\n"
    "What lands on the canvas is an ordinary editable text layer, and "
    "finishing it by hand is expected rather than a fallback. Everything in "
    "Pixelmator's Text panel still applies:\n\n"
    "    \u2022  Font, size and colour\n"
    "    \u2022  Alignment, horizontal and vertical\n"
    "    \u2022  Spacing: Line Height, Before Paragraph, After Paragraph\n"
    "    \u2022  Indents\n"
    "    \u2022  Convert to Shape, Convert to Pixels\n\n"
    "Line Height is the one to reach for first — it is also the one thing "
    "no script can set, since Pixelmator exposes no spacing property at "
    "all, so opening it up by hand is the intended finish.\n\n"
    "Two things to expect. Each line is sized for the row it sits on, so "
    "anything that moves the lines vertically can push a long one into a "
    "notch. And a shape with a straight edge on one side reads as aligned "
    "to that edge; use the Align menu when it reads differently than you "
    "do.\n\n"
    "You can bring this back at any time with the Info button, next to "
    "Exit.")


def show_info(controller, first_time=False):
    """The Info panel. Offered once, then whenever the ⓘ button is pressed."""
    alert = NSAlert.alloc().init()
    alert.setAlertStyle_(1)                       # informational
    alert.setMessageText_("%s %s" % (INFO_TITLE, APP_VERSION))
    alert.setInformativeText_(INFO_BODY)
    alert.addButtonWithTitle_("OK")
    icon = app_icon()
    if icon is not None:
        alert.setIcon_(icon)
    if first_time:
        alert.setShowsSuppressionButton_(True)
        alert.suppressionButton().setTitle_("Don\u2019t show this again")
    alert.runModal()
    if first_time and alert.suppressionButton().state():
        NSUserDefaults.standardUserDefaults().setBool_forKey_(
            True, SEEN_INTRO_KEY)


def app_icon():
    """This app's own icon, for badging its alerts."""
    bundle = NSBundle.mainBundle()
    path = bundle.bundlePath()
    if bundle.bundleIdentifier() != "com.timmccoy.pixprofittext":
        path = "/Applications/PixProFitText.app"
    try:
        return NSWorkspace.sharedWorkspace().iconForFile_(path)
    except Exception:
        return None
MARGIN_MIN, MARGIN_MAX = 0, 400
# Clearance as a share of the shape's smaller side. 1.5% is ~7px on Tim's
# 455px test shapes, which is where the hand-picked 6 had landed.
MARGIN_FRACTION = 0.015
MARGIN_FLOOR, MARGIN_CEILING = 2, 40
DEFAULT_MARGIN = 6              # only until a shape has been read


def margin_for(shape):
    """Clearance proportional to the shape, in pixels of the document."""
    import numpy as np
    ys, xs = np.nonzero(shape)
    if ys.size == 0:
        return DEFAULT_MARGIN
    side = min(ys.max() - ys.min() + 1, xs.max() - xs.min() + 1)
    return int(max(MARGIN_FLOOR,
                   min(MARGIN_CEILING, round(side * MARGIN_FRACTION))))


def _number(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _colour_from(text):
    try:
        r, g, b = [max(0, min(255, int(v))) for v in str(text).split(",")]
    except (TypeError, ValueError):
        return NSColor.blackColor()
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(
        r / 255.0, g / 255.0, b / 255.0, 1.0)


def _rgb_of(colour):
    """A colour as 0-255 RGB, whatever colour space the picker handed back.

    The Crayons and Color Palettes tabs return an NSCatalogColor, which the
    old colorUsingColorSpaceName_ cannot convert — it returns None, and
    white then read as black. colorUsingColorSpace_ resolves those. The
    result is clamped because the wide-gamut sliders produce extended-range
    components outside 0-1.
    """
    if colour is None:
        return None
    for space in (NSColorSpace.genericRGBColorSpace(),
                  NSColorSpace.sRGBColorSpace(),
                  NSColorSpace.deviceRGBColorSpace()):
        try:
            rgb = colour.colorUsingColorSpace_(space)
        except Exception:
            rgb = None
        if rgb is None:
            continue
        try:
            parts = (rgb.redComponent(), rgb.greenComponent(),
                     rgb.blueComponent())
        except Exception:
            continue
        return tuple(max(0, min(255, int(round(c * 255)))) for c in parts)
    return None


# Settings written by a version that had a control this one no longer has.
# Dropping a control does not undo what it set, and a value nothing reads
# but nothing clears either is worse than the control was.
RETIRED_SETTINGS = ("spacing", "margin")


def _titlebar_label(text, align):
    field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 200, 16))
    field.setStringValue_(text)
    field.setBezeled_(False)
    field.setDrawsBackground_(False)
    field.setEditable_(False)
    field.setSelectable_(False)
    field.setFont_(NSFont.systemFontOfSize_(11))
    field.setTextColor_(NSColor.secondaryLabelColor())
    field.setAlignment_(align)
    field.sizeToFit()
    return field


def decorate_titlebar(window):
    """Version on the left, name and icon centred, copyright on the right.

    The centre is the window's own title, which AppKit already centres. An
    icon can only join it through a represented URL — pointing that at the
    app's own bundle puts the app icon beside the name, which is the only
    supported way to get a picture into the middle of a title bar. Left and
    right are ordinary titlebar accessories, so they sit clear of the
    traffic lights and stay put when the window is resized.
    """
    for text, attribute, align in (("v" + APP_VERSION, NSLayoutAttributeLeft, 0),
                                   (COPYRIGHT, NSLayoutAttributeRight, 2)):
        label = _titlebar_label(text, align)
        holder = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, label.frame().size.width + 16, 22))
        label.setFrameOrigin_(NSMakePoint(8, 3))
        holder.addSubview_(label)
        controller = NSTitlebarAccessoryViewController.alloc().init()
        controller.setView_(holder)
        controller.setLayoutAttribute_(attribute)
        window.addTitlebarAccessoryViewController_(controller)

    bundle = NSBundle.mainBundle()
    path = bundle.bundlePath()
    if bundle.bundleIdentifier() != "com.timmccoy.pixprofittext":
        # Running from source: point at the installed copy so the icon is
        # the app's own rather than the interpreter's.
        installed = "/Applications/PixProFitText.app"
        path = installed if os.path.isdir(installed) else None
    if path:
        window.setRepresentedURL_(NSURL.fileURLWithPath_(path))


def load_settings():
    stored = NSUserDefaults.standardUserDefaults().dictionaryForKey_(
        SETTINGS_KEY)
    saved = dict(stored) if stored else {}
    if any(saved.pop(key, None) is not None for key in RETIRED_SETTINGS):
        NSUserDefaults.standardUserDefaults().setObject_forKey_(
            saved, SETTINGS_KEY)
    return saved


def save_settings(controller):
    """Remember how the app was last used.

    Written after each Try and Apply rather than only on quit: the app is
    often left running, and losing the setup because it was force-quit or
    the machine restarted is exactly the case worth covering.
    """
    rgb = controller.colour()
    NSUserDefaults.standardUserDefaults().setObject_forKey_({
        "family": str(controller.font_menu.titleOfSelectedItem() or ""),
        "face": str(controller.face_menu.titleOfSelectedItem() or ""),
        "angle": "%.2f" % controller.angle(),
        "wrap": "1" if controller.wrapping() else "0",
        "align": controller.alignment() or "",
        "color": "%d,%d,%d" % rgb,
        "text": controller.text(),
    }, SETTINGS_KEY)


class Controller(NSObject):

    # -- construction ------------------------------------------------------

    def init(self):
        self = objc.super(Controller, self).init()
        if self is None:
            return None
        self.shape = None
        self.shape_layer = None
        self.bundle = None
        self.calibration = None
        self.fit = None
        self.busy = False
        self.applied = False      # is there work that has not been applied?
        # Until you touch it, Margin belongs to whatever shape is loaded.
        self.margin_touched = False
        self._build()
        self.refreshShape_(None)
        # Once, on first run — after the window is up, so it has something
        # to sit in front of rather than appearing out of nowhere.
        if not NSUserDefaults.standardUserDefaults().boolForKey_(
                SEEN_INTRO_KEY):
            self.performSelector_withObject_afterDelay_(
                "_firstRunInfo:", None, 0.4)
        return self

    def _firstRunInfo_(self, ignored):
        show_info(self, first_time=True)

    def showInfo_(self, sender):
        show_info(self)

    def _build(self):
        width, height = 760, 620
        window = NSWindow.alloc().\
            initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, width, height),
                NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable,
                NSBackingStoreBuffered, False)
        window.setTitle_("PixProFitText")
        decorate_titlebar(window)
        window.setMinSize_(NSMakeSize(680, 520))
        view = window.contentView()

        # -- preview, filling the top
        self.preview = NSImageView.alloc().initWithFrame_(
            NSMakeRect(12, 210, width - 24, height - 222))
        self.preview.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        self.preview.setAutoresizingMask_(
            NSViewWidthSizable | NSViewHeightSizable)
        self.preview.setWantsLayer_(True)
        view.addSubview_(self.preview)

        # -- controls, pinned to the bottom
        panel = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, 200))
        panel.setAutoresizingMask_(NSViewWidthSizable | NSViewMaxYMargin)
        view.addSubview_(panel)

        panel.addSubview_(_label("Text", 12, 168))
        text_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 74, 330, 92))
        text_scroll.setHasVerticalScroller_(True)
        text_scroll.setBorderType_(2)
        self.text_view = PlainTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 330, 92))
        self.text_view.setFont_(NSFont.systemFontOfSize_(13))
        saved = load_settings()
        self.text_view.setString_(saved.get("text") or DEFAULT_TEXT)
        self.text_view.setDelegate_(self)
        self.text_view.setRichText_(False)
        text_scroll.setDocumentView_(self.text_view)
        panel.addSubview_(text_scroll)

        panel.addSubview_(_label("Font", 356, 168))
        self.font_menu = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(356, 140, 260, 26), False)
        families = list(NSFontManager.sharedFontManager().availableFontFamilies())
        self.font_menu.addItemsWithTitles_([str(f) for f in families])
        preferred = saved.get("family") or "Helvetica Neue"
        if preferred in [str(f) for f in families]:
            self.font_menu.selectItemWithTitle_(preferred)
        self.font_menu.setTarget_(self)
        self.font_menu.setAction_("fontChanged:")
        panel.addSubview_(self.font_menu)

        self.face_menu = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(624, 140, 124, 26), False)
        self.face_menu.setTarget_(self)
        self.face_menu.setAction_("fontChanged:")
        panel.addSubview_(self.face_menu)
        self._reloadFaces()
        if saved.get("face"):
            self.face_menu.selectItemWithTitle_(saved["face"])

        panel.addSubview_(_label("Color", 660, 112, 44))
        self.colour_well = NSColorWell.alloc().initWithFrame_(
            NSMakeRect(700, 106, 48, 26))
        self.colour_well.setColor_(_colour_from(saved.get("color")))
        self.colour_well.setTarget_(self)
        self.colour_well.setAction_("colourChanged:")
        # An NSColorWell that takes first responder ACTIVATES itself, and an
        # active well opens the system colour picker — which is how the
        # picker ended up in front of the window at launch. It should only
        # open when it is actually clicked.
        self.colour_well.setRefusesFirstResponder_(True)
        panel.addSubview_(self.colour_well)

        panel.addSubview_(_label("Angle", 356, 112))
        self.angle_slider = NSSlider.alloc().initWithFrame_(
            NSMakeRect(410, 108, 172, 24))
        self.angle_slider.setMinValue_(-90.0)
        self.angle_slider.setMaxValue_(90.0)
        self.angle_slider.setDoubleValue_(_number(saved.get("angle"), 0.0))
        self.angle_slider.setTarget_(self)
        self.angle_slider.setAction_("angleChanged:")
        # Refit when the slider is let go, not on every pixel of the drag.
        self.angle_slider.setContinuous_(False)
        panel.addSubview_(self.angle_slider)

        self.angle_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(590, 110, 44, 22))
        self.angle_field.setStringValue_(
            "%d" % round(_number(saved.get("angle"), 0.0)))
        self.angle_field.setTarget_(self)
        self.angle_field.setAction_("angleTyped:")
        panel.addSubview_(self.angle_field)
        panel.addSubview_(_label("°", 636, 112, 14))

        self.wrap_box = FirstMouseButton.alloc().initWithFrame_(
            NSMakeRect(356, 46, 220, 20))
        self.wrap_box.setButtonType_(3)                    # switch
        self.wrap_box.setTitle_("Follow the shape")
        self.wrap_box.setState_(0 if saved.get("wrap") == "0" else 1)
        self.wrap_box.setTarget_(self)
        self.wrap_box.setAction_("markStale:")
        panel.addSubview_(self.wrap_box)

        align_tip = ("Auto reads the justification off the shape — a straight "
                     "edge on one side means the text lines up with it. "
                     "Override it when Auto reads the shape differently than "
                     "you do.")
        align_label = _label("Align", 590, 46, 42)
        align_label.setToolTip_(align_tip)
        panel.addSubview_(align_label)
        self.align_menu = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(636, 42, 112, 26), False)
        self.align_menu.addItemsWithTitles_([n for n, _ in ALIGN_CHOICES])
        saved_align = saved.get("align") or ""
        for i, (_name, value) in enumerate(ALIGN_CHOICES):
            if (value or "") == saved_align:
                self.align_menu.selectItemAtIndex_(i)
                break
        self.align_menu.setTarget_(self)
        self.align_menu.setAction_("markStale:")
        self.align_menu.setToolTip_(align_tip)
        panel.addSubview_(self.align_menu)

        self.try_button = FirstMouseButton.alloc().initWithFrame_(
            NSMakeRect(496, 16, 122, 30))
        self.try_button.setTitle_("Try")
        self.try_button.setBezelStyle_(1)
        self.try_button.setTarget_(self)
        self.try_button.setAction_("refit:")
        panel.addSubview_(self.try_button)

        best = FirstMouseButton.alloc().initWithFrame_(NSMakeRect(356, 74, 130, 28))
        best.setTitle_("Best angle")
        best.setBezelStyle_(1)
        best.setTarget_(self)
        best.setAction_("findBestAngle:")
        panel.addSubview_(best)

        margin_tip = ("Pixels of clearance kept between the text and the "
                      "edge of the shape. More margin means smaller text.")
        margin_label = _label("Margin", 500, 80, 50)
        margin_label.setToolTip_(margin_tip)
        panel.addSubview_(margin_label)

        self.padding_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(554, 78, 44, 22))
        self.padding_field.setStringValue_(
            "%d" % DEFAULT_MARGIN)
        self.padding_field.setTarget_(self)
        self.padding_field.setAction_("marginTyped:")
        self.padding_field.setToolTip_(margin_tip)
        panel.addSubview_(self.padding_field)

        self.margin_stepper = NSStepper.alloc().initWithFrame_(
            NSMakeRect(600, 76, 19, 26))
        self.margin_stepper.setMinValue_(0)
        self.margin_stepper.setMaxValue_(400)
        self.margin_stepper.setIncrement_(1)
        self.margin_stepper.setValueWraps_(False)
        self.margin_stepper.setIntValue_(DEFAULT_MARGIN)
        self.margin_stepper.setTarget_(self)
        self.margin_stepper.setAction_("marginStepped:")
        self.margin_stepper.setRefusesFirstResponder_(True)
        self.margin_stepper.setToolTip_(margin_tip)
        panel.addSubview_(self.margin_stepper)

        px = _label("px", 623, 80, 22)
        px.setToolTip_(margin_tip)
        panel.addSubview_(px)

        self.status = _label("", 12, 50, 560)
        panel.addSubview_(self.status)
        self.shape_label = _label("", 180, 24, 176)
        self.shape_label.setTextColor_(NSColor.secondaryLabelColor())
        panel.addSubview_(self.shape_label)

        refresh = FirstMouseButton.alloc().initWithFrame_(NSMakeRect(360, 16, 126, 30))
        refresh.setTitle_("Reread shape")
        refresh.setBezelStyle_(1)
        refresh.setTarget_(self)
        refresh.setAction_("refreshShape:")
        panel.addSubview_(refresh)

        self.apply_button = FirstMouseButton.alloc().initWithFrame_(
            NSMakeRect(626, 16, 122, 30))
        self.apply_button.setTitle_("Apply")
        self.apply_button.setBezelStyle_(1)
        self.apply_button.setKeyEquivalent_("\r")
        self.apply_button.setTarget_(self)
        self.apply_button.setAction_("apply:")
        panel.addSubview_(self.apply_button)

        exit_button = FirstMouseButton.alloc().initWithFrame_(
            NSMakeRect(12, 16, 92, 30))
        exit_button.setTitle_("Exit")
        exit_button.setBezelStyle_(1)
        exit_button.setTarget_(self)
        exit_button.setAction_("exitApp:")
        panel.addSubview_(exit_button)

        info_button = FirstMouseButton.alloc().initWithFrame_(
            NSMakeRect(110, 16, 62, 30))
        info_button.setTitle_("Info")
        info_button.setBezelStyle_(1)
        info_button.setTarget_(self)
        info_button.setAction_("showInfo:")
        info_button.setToolTip_("What this app promises, and what it leaves "
                                "to you")
        panel.addSubview_(info_button)

        window.setDelegate_(self)
        window.setInitialFirstResponder_(self.text_view)
        window.center()
        window.makeKeyAndOrderFront_(None)
        window.makeFirstResponder_(self.text_view)
        # Belt and braces: if anything did activate the well, put the panel
        # away rather than leaving it over the window.
        NSColorPanel.sharedColorPanel().orderOut_(None)
        self.window = window


    # -- reading the shape -------------------------------------------------

    def refreshShape_(self, sender):
        """Re-read the selected shape layer out of Pixelmator."""
        try:
            self.bundle = bridge.active_bundle()
            name = bridge.selected_shape_layer(self.bundle)
            if name is None:
                # Say so rather than fitting to whatever shape happens to be
                # first — silently using a different shape than the one that
                # is selected is worse than doing nothing.
                shapes = bridge.shape_layer_names(self.bundle)
                chosen, kind = bridge.selected_layer_description(self.bundle)
                if not shapes:
                    complain("No shape to fit text into",
                             "This document has no shape layers. Draw a "
                             "shape, select it, and press Reread shape.")
                elif chosen:
                    complain("Select a shape layer",
                             "“%s” is a %s, which has no outline to fit text "
                             "inside.\n\nSelect one of these and press Reread "
                             "shape:\n    %s"
                             % (chosen, kind, "\n    ".join(shapes)))
                else:
                    complain("Select a shape layer",
                             "Nothing is selected in Pixelmator.\n\nSelect "
                             "one of these and press Reread shape:\n    %s"
                             % "\n    ".join(shapes))
                self.shape = None
                say(self, "Select a shape layer, then Reread shape.", True)
                self._draw()
                return
            back = bridge.restore_visibility(self.bundle)
            if back:
                note("restored visibility of %d layers left hidden by an "
                     "interrupted export" % back)
            mask = bridge.export_layer_mask(self.bundle, name,
                                            scratch("shape.png"))
            self.shape = engine.load_shape(mask)
            self.shape_layer = name
            # A margin you set is yours; otherwise it follows the shape.
            if not self.margin_touched:
                self.setMargin_(margin_for(self.shape))
            doc, width, height = bridge.document_info(self.bundle)
            self.shape_label.setStringValue_(
                'shape "%s" in %s  (%d x %d)' % (name, doc, width, height))
            self.calibration = None          # font/text metrics must be redone
            self.refit_(None)
        except bridge.PixmatorError as exc:
            self.shape = None
            say(self, str(exc), True)
            self._draw()

    # -- controls ----------------------------------------------------------

    def _reloadFaces(self):
        manager = NSFontManager.sharedFontManager()
        family = self.font_menu.titleOfSelectedItem()
        members = manager.availableMembersOfFontFamily_(family) or []
        self.face_menu.removeAllItems()
        names = [str(m[1]) for m in members] or ["Regular"]
        self.face_menu.addItemsWithTitles_(names)
        for wanted in ("Bold", "Regular"):
            if wanted in names:
                self.face_menu.selectItemWithTitle_(wanted)
                break

    def font_name(self):
        manager = NSFontManager.sharedFontManager()
        family = self.font_menu.titleOfSelectedItem()
        face = self.face_menu.titleOfSelectedItem()
        for member in (manager.availableMembersOfFontFamily_(family) or []):
            if str(member[1]) == str(face):
                return str(member[0])          # the PostScript name
        return str(family)

    def text(self):
        return str(self.text_view.string())

    def angle(self):
        return float(self.angle_slider.doubleValue())

    def colour(self):
        """The chosen colour as Pixelmator wants it: 0-255 per channel."""
        rgb = _rgb_of(self.colour_well.color())
        if rgb is None:
            note("COLOR unreadable from the well (%r) - using black"
                 % (self.colour_well.color(),))
            return (0, 0, 0)
        return rgb

    def wrapping(self):
        return bool(self.wrap_box.state())

    def alignment(self):
        """The forced justification, or None to read it off the shape."""
        index = self.align_menu.indexOfSelectedItem()
        if 0 <= index < len(ALIGN_CHOICES):
            return ALIGN_CHOICES[index][1]
        return None

    # -- keeping the box and its stepper agreeing --------------------------

    def setMargin_(self, value):
        """Set both halves of the control without claiming you typed it."""
        value = int(max(MARGIN_MIN, min(MARGIN_MAX, value)))
        self.padding_field.setStringValue_("%d" % value)
        self.margin_stepper.setIntValue_(value)

    def marginStepped_(self, sender):
        self.margin_touched = True
        self.padding_field.setStringValue_("%d" % sender.intValue())
        self.markStale_(sender)

    def marginTyped_(self, sender):
        self.margin_touched = True
        self.setMargin_(self.padding())
        self.markStale_(sender)


    def padding(self):
        try:
            return max(MARGIN_MIN,
                       min(MARGIN_MAX, int(self.padding_field.stringValue())))
        except ValueError:
            return 0

    def fontChanged_(self, sender):
        """Pick a font; do not go and measure it.

        Measuring means creating and deleting a text layer in the user's
        document, which is far too much to happen from browsing a menu.
        """
        if sender is self.font_menu:
            self._reloadFaces()
        self.calibration = None
        self.markStale_(None)

    def textDidChange_(self, notification):
        """Typing only invalidates the fit — it does not recompute it.

        Fitting a paragraph takes a second or two, and doing that on every
        keystroke made the box unusable to type in. The Try button asks for
        the work; typing just marks what is on screen as stale.
        """
        self.calibration = None
        self.fit = None
        self.applied = False
        say(self, "Text changed — press Try to fit it.")
        self._draw()

    def angleChanged_(self, sender):
        self.angle_field.setStringValue_("%d" % round(self.angle()))
        self.markStale_(None)

    def colourChanged_(self, sender):
        """Redraw so the preview shows the colour that will be applied."""
        self._draw()

    def exitApp_(self, sender):
        if may_exit(self):
            NSApp.terminate_(None)

    def windowShouldClose_(self, sender):
        """The red button ends the app, not just the window — but not
        silently over the top of a fit that was never applied."""
        if may_exit(self):
            NSApp.terminate_(None)
        return False

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def markStale_(self, sender):
        """Something changed; the preview is out of date but nothing is
        recomputed until Try is pressed. Fitting takes a second or two, and
        doing it unbidden — after a paste, on leaving a field — was the app
        deciding for itself when to work."""
        self.fit = None
        self.applied = False
        say(self, "Press Try to fit.")
        self._draw()

    def angleTyped_(self, sender):
        try:
            value = max(-90.0, min(90.0, float(sender.stringValue())))
        except ValueError:
            value = self.angle()
        self.angle_slider.setDoubleValue_(value)
        self.angle_field.setStringValue_("%d" % round(value))
        self.markStale_(None)

    # -- fitting and preview -----------------------------------------------

    def refit_(self, sender):
        """Work out the fit and redraw. Cheap enough to run from the slider."""
        if self.shape is None or self.busy:
            return
        text = self.text()
        if not text.strip():
            self.fit = None
            say(self, "Type something to fit.")
            self._draw()
            return
        self.fit = compute_fit(self, text, self.font_name(), self.angle())
        if self.fit is None:
            # Log the failures too. The TRY line used to live only in the
            # success branch, so three runs in a row that answered "will not
            # fit" left no trace at all and looked from the log like the
            # button had never been pressed.
            note("TRY  shape=%s font=%s angle=%.0f margin=%d follow=%s "
                 "chars=%d color=%s -> NO FIT, align=%s, cal=%s"
                 % (self.shape_layer, self.font_name(), self.angle(),
                    self.padding(), self.wrapping(), len(text),
                    self.colour(), self.alignment() or "auto",
                    self.calibration))
            say(self, "Will not fit at this angle, even at 6 pt.", True)
        else:
            tag = "" if self.calibration else "  (preview)"
            say(self, "%d pt at %d°%s"
                      % (round(self.fit.size), round(self.angle()), tag))
            note("TRY  shape=%s font=%s angle=%.0f margin=%d follow=%s "
                 "chars=%d color=%s -> %.1f pt, %d lines, align=%s (%s), "
                 "cal=%s"
                 % (self.shape_layer, self.font_name(), self.angle(),
                    self.padding(), self.wrapping(), len(text),
                    self.colour(), self.fit.size, len(self.fit.lines),
                    getattr(self.fit, "align", "?"),
                    self.alignment() or "auto", self.calibration))
        save_settings(self)
        self._draw()

    def findBestAngle_(self, sender):
        if self.shape is None or self.busy:
            return
        say(self, "Trying angles…")
        best, best_angle = None, 0.0
        for angle in range(-90, 91, 5):
            fit = compute_fit(self, self.text(), self.font_name(),
                              float(angle))
            if fit is not None and (best is None or fit.size > best.size):
                best, best_angle = fit, float(angle)
        if best is None:
            say(self, "No angle fits.", True)
            return
        self.angle_slider.setDoubleValue_(best_angle)
        self.angle_field.setStringValue_("%d" % round(best_angle))
        self.refit_(None)

    def _draw(self):
        """Shape in grey, the fitted text over it, anything outside in red."""
        if self.shape is None:
            self.preview.setImage_(None)
            return
        bounds = engine.shape_bounds(self.shape)
        if bounds is None:
            self.preview.setImage_(None)
            return
        x0, y0, x1, y1 = bounds
        pad = 12
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1 = min(self.shape.shape[1] - 1, x1 + pad)
        y1 = min(self.shape.shape[0] - 1, y1 + pad)

        canvas = np.zeros((y1 - y0 + 1, x1 - x0 + 1, 3), dtype=np.uint8)
        canvas[:, :] = (250, 250, 250)
        canvas[self.shape[y0:y1 + 1, x0:x1 + 1]] = (208, 208, 212)

        if self.fit is not None:
            placed = np.zeros(self.shape.shape, dtype=bool)
            h, w = self.fit.text_mask.shape
            placed[self.fit.y:self.fit.y + h, self.fit.x:self.fit.x + w] = \
                self.fit.text_mask
            window = placed[y0:y1 + 1, x0:x1 + 1]
            inside = window & self.shape[y0:y1 + 1, x0:x1 + 1]
            outside = window & ~self.shape[y0:y1 + 1, x0:x1 + 1]
            canvas[inside] = self.colour()
            canvas[outside] = (220, 40, 40)
        self.preview.setImage_(_image_from_array(canvas))

    # -- applying ----------------------------------------------------------

    def apply_(self, sender):
        if self.shape is None or self.fit is None or self.busy:
            return
        self.busy = True
        self.apply_button.setEnabled_(False)
        say(self, "Applying…")
        # On the MAIN thread, deliberately. Apply re-renders text through
        # AppKit to check its own work, and AppKit text layout is not
        # thread-safe: measured off-thread it disagreed with the preview,
        # so Apply shrank text that the preview had fitted perfectly. A
        # short freeze is a fair price for measuring the same thing twice.
        self.performSelector_withObject_afterDelay_("_runApply:", None, 0.05)

    def _runApply_(self, ignored):
        self._applyWork()

    def _applyWork(self):
        text, font, angle = self.text(), self.font_name(), self.angle()
        padding = self.padding()
        colour = self.colour()
        try:
            if self.fit is None:
                post(self, "Press Try first.", True)
                return
            # Try already measured the font and produced the fit that was
            # previewed. Apply places exactly that — the flowed line breaks
            # included, since they are what was sized.
            note("APPLY start: %.1f pt predicted, %d lines, box-ink %dx%d"
                 % (self.fit.size, len(self.fit.lines),
                    self.fit.width, self.fit.height))
            payload = "\n".join(self.fit.lines) if self.fit.lines else text
            # Its own layer, named for the shape, so previous fits survive.
            layer_name = bridge.unique_layer_name(
                self.bundle, "Text in %s" % (self.shape_layer or "shape"))
            size, escaped, tries, lost, box = bridge.apply_fit(
                self.bundle, self.shape, self.fit, payload, font, angle,
                scratch("verify.png"), padding=padding,
                calibration=self.calibration, color=colour,
                name=layer_name,
                on_step=lambda n, s: (
                    note("APPLY pass %d at %d pt" % (n, s)),
                    post(self, "Checking it really fits — %d pt (pass %d)…"
                               % (s, n))),
                on_probe=lambda n, sz, box, pos, dw, dh, mw, mh, dl, sl, esc:
                    note("APPLY   pass %d  %d pt  box=%d  pos=(%d,%d)  "
                         "drawn=%dx%d  model=%dx%d  lines drawn=%d sent=%d  "
                         "escaping=%d"
                         % (n, sz, box, pos[0], pos[1], dw, dh, mw, mh,
                            dl, sl, esc)))
            note("APPLY done: %d pt, %d pass(es), escaping %d, lost %d, "
                 "box %d, layer %r"
                 % (size, tries, escaped, lost, box, layer_name))
            note("APPLY predicted %.1f pt -> settled %d pt" % (self.fit.size, size))
            if lost < 0:
                post(self, "Placed at %d pt, but Pixelmator re-broke the "
                           "lines into %d where the fit chose %d — the layout "
                           "on the layer is not the one that was verified."
                           % (size, len(self.fit.lines) - lost,
                              len(self.fit.lines)), True)
            elif lost:
                # Silence here is the worst outcome: the layer looks tidy
                # and is missing words.
                post(self, "Placed at %d pt, but %d line%s did not fit — the "
                           "shape is too small for this much text. Shorten it, "
                           "enlarge the shape, or reduce the margin."
                           % (size, lost, "" if lost == 1 else "s"), True)
            elif escaped:
                post(self, "Placed at %d pt, but %d pixels still sit outside."
                           % (size, escaped), True)
            else:
                self.applied = True
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "_saveSettings:", None, False)
                post(self, "“%s” placed at %d pt — verified inside the shape "
                           "(%d pass%s)."
                           % (layer_name, size, tries,
                              "" if tries == 1 else "es"))
        except bridge.PixmatorError as exc:
            post(self, str(exc), True)
        finally:
            post(self, None)

    def _saveSettings_(self, ignored):
        save_settings(self)

    def _mainPost_(self, payload):
        message, warn = payload
        if message is None:
            self.busy = False
            self.apply_button.setEnabled_(True)
            self.refit_(None)
            return
        say(self, message, warn)


def compute_fit(controller, text, font, angle):
    """The fit, in whichever mode is selected.

    In shape-following mode the flow picks the line breaks and the CALIBRATED
    fitter sizes and places them, because those pre-broken lines are what
    Pixelmator is actually handed. Sizing them with AppKit's metrics instead
    produced a lovely preview and a layer a quarter too big that hung out of
    the shape.

    A module function, not a method: PyObjC maps every method to a selector,
    and one taking arguments without trailing underscores is rejected.
    """
    if not controller.wrapping():
        # Unticked means "honour the line breaks I typed" — but a passage
        # pasted in as one paragraph has none, and fit_text without wrap
        # tries to place all 449 characters on a single line, which cannot
        # fit any shape and reports "will not fit, even at 6 pt". Wrap for
        # it in that case; if the text carries its own breaks, respect them.
        own_breaks = len([L for L in text.split("\n") if L.strip()]) > 1
        return engine.fit_text(controller.shape, text, font, angle=angle,
                               padding=controller.padding(),
                               calibration=controller.calibration,
                               wrap=not own_breaks,
                               align=controller.alignment())
    # The flow plans at a deliberately TIGHT line spacing, not the measured
    # one. Planning at the real 1.44 fits fewer lines, so the flow settles
    # on a smaller size and hands the block fit line breaks it cannot
    # improve on — measured against both shapes it cost the flag 9.5pt ->
    # 8.2pt and the diamond 15.8pt -> 13.7pt. The flow's job is to choose
    # good BREAKS; the calibrated block fit decides the size.
    flowed = engine.fit_flowed(controller.shape, text, font, angle=angle,
                               padding=controller.padding(),
                               align=controller.alignment())
    if flowed is None or not flowed.lines:
        return None
    broken = "\n".join(flowed.lines)
    ensure_calibration(controller, broken, font)
    fit = engine.fit_text(controller.shape, broken, font, angle=angle,
                          padding=controller.padding(),
                          calibration=controller.calibration,
                          align=flowed.align)
    if fit is not None:
        fit.rendered.lines = flowed.lines
        fit.rendered.align = flowed.align
    return fit


# Versioned: the stored numbers mean something different since the line
# spacing measurement changed, and reading the old ones back is worse than
# having none — it silently reintroduces the bug that was just fixed.
# 3: width_offset became width_factor.  4: key 3 had cached the
# canvas-not-probe measurement.  5: so had key 4, because 2.5.1's fix only
# covered the opaque export and the next measurement landed on a
# transparent one.  A cached calibration is never re-measured, so a bad one
# can only be got rid of by moving the key.
CALIB_KEY = "PixProFitTextCalibration6"


def ensure_calibration(controller, text, font):
    """Get this FONT's measurement — from memory if it has ever been taken.

    Measuring means putting a probe layer in the user's document and taking
    it away again, which they see. Once per font for the life of the
    install is the least that can be got away with, so the answers are kept
    in preferences rather than re-measured each session.
    """
    if controller.calibration is not None and \
            controller.calibration.applies_to(text, font):
        return
    stored = NSUserDefaults.standardUserDefaults().dictionaryForKey_(CALIB_KEY)
    if stored and font in stored:
        try:
            wide, tall = [float(v) for v in str(stored[font]).split(",")]
            controller.calibration = engine.Calibration(wide, tall,
                                                        text, font)
            return
        except ValueError:
            pass
    try:
        say(controller, "Measuring %s (once)…" % font)
        controller.calibration = bridge.calibrate(
            controller.bundle, text, font, scratch("calib.png"))
        remembered = dict(stored or {})
        remembered[font] = "%f,%f" % (controller.calibration.width_factor,
                                      controller.calibration.height_factor)
        NSUserDefaults.standardUserDefaults().setObject_forKey_(
            remembered, CALIB_KEY)
    except bridge.PixmatorError as exc:
        controller.calibration = None
        sys.stderr.write("PixProFitText: calibration failed: %s\n" % exc)


def may_exit(controller):
    """True if it is fine to quit now.

    Quitting with a fit on screen that was never applied throws away the
    work the window exists to produce, so that case asks; anything else
    goes straight out.
    """
    if controller.applied or controller.fit is None:
        return True
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Exit without applying?")
    alert.setInformativeText_(
        "The text has been fitted but not placed in the document. "
        "Quitting now discards it.")
    alert.addButtonWithTitle_("Exit Without Applying")
    alert.addButtonWithTitle_("Cancel")
    alert.buttons()[0].setKeyEquivalent_("")
    alert.buttons()[1].setKeyEquivalent_("\r")
    NSApp.activateIgnoringOtherApps_(True)
    return alert.runModal() == 1000


def complain(title, body):
    """An alert, for the things the user has to fix before anything works."""
    alert = NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(body)
    alert.addButtonWithTitle_("OK")
    NSApp.activateIgnoringOtherApps_(True)
    alert.runModal()


def say(controller, message, warn=False):
    """Put a line in the status field. A module function, not a method:
    PyObjC maps every method to a selector, and one that takes arguments
    without trailing underscores in its name is rejected at import."""
    controller.status.setStringValue_(message)
    controller.status.setTextColor_(
        NSColor.systemRedColor() if warn else NSColor.labelColor())


def post(controller, message, warn=False):
    """Say something during a long operation, and let it paint.

    Apply runs on the main thread, so the window will not redraw on its own
    while it works — the run loop has to be pumped for the message to
    appear at all.
    """
    if message is None:
        controller.busy = False
        controller.apply_button.setEnabled_(True)
        controller.refit_(None)
        return
    say(controller, message, warn)
    from Foundation import NSRunLoop, NSDate
    NSRunLoop.currentRunLoop().runUntilDate_(
        NSDate.dateWithTimeIntervalSinceNow_(0.01))


def _image_from_array(array):
    height, width = array.shape[:2]
    rep = NSBitmapImageRep.alloc().\
        initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
            None, width, height, 8, 3, False, False, NSDeviceRGBColorSpace,
            width * 3, 24)
    buffer = rep.bitmapData()
    flat = np.ascontiguousarray(array, dtype=np.uint8).tobytes()
    buffer[:len(flat)] = flat
    image = NSImage.alloc().initWithSize_(NSMakeSize(width, height))
    image.addRepresentation_(rep)
    return image


def build_menu(app):
    """A real menu bar, chiefly so the text box can be pasted into.

    Cmd-V is not handled by NSTextView on its own: the keystroke is matched
    against the main menu's key equivalents, and an app with no menu bar has
    nothing for it to match. Without this the text field silently ignores a
    paste, which looks like a broken field rather than a missing menu.
    """
    main = NSMenu.alloc().init()

    app_item = NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_(
        "About PixProFitText", "orderFrontStandardAboutPanel:", "")
    app_menu.addItem_(NSMenuItem.separatorItem())
    app_menu.addItemWithTitle_action_keyEquivalent_(
        "Hide PixProFitText", "hide:", "h")
    app_menu.addItemWithTitle_action_keyEquivalent_(
        "Quit PixProFitText", "terminate:", "q")
    app_item.setSubmenu_(app_menu)

    edit_item = NSMenuItem.alloc().init()
    main.addItem_(edit_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    for title, action, key in (
            ("Undo", "undo:", "z"),
            ("Redo", "redo:", "Z"),
            (None, None, None),
            ("Cut", "cut:", "x"),
            ("Copy", "copy:", "c"),
            ("Paste", "paste:", "v"),
            ("Paste and Match Style", "pasteAsPlainText:", "V"),
            ("Delete", "delete:", ""),
            ("Select All", "selectAll:", "a")):
        if title is None:
            edit_menu.addItem_(NSMenuItem.separatorItem())
        else:
            edit_menu.addItemWithTitle_action_keyEquivalent_(title, action, key)
    edit_item.setSubmenu_(edit_menu)

    app.setMainMenu_(main)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(0)
    build_menu(app)
    controller = Controller.alloc().init()
    app.setDelegate_(controller)
    app.activateIgnoringOtherApps_(True)
    app.run()


if __name__ == "__main__":
    main()

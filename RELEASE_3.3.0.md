# PixProFitText 3.3.0

Everything since 2.7.3. The headline is that text now fits on the first
try instead of shrinking until it gives up — and when it genuinely cannot
fit, it says so instead of quietly placing something wrong.

## The size collapse is fixed

Fits could arrive far smaller than predicted, having stepped down through
several sizes and still left ink outside the shape.

The cause was one wrong assumption about how Pixelmator sets a line: the
difference from the app's own model is a constant offset in pixels, not a
ratio. Treated as a ratio, shrinking the type made the fixed difference a
larger share of a smaller line, so the error grew as fast as the size
fell and the loop could never settle.

Width is now an offset and height remains a factor, which is what they
each measurably are. Fits settle in one pass with nothing outside the
shape.

## Nothing is placed quietly any more

- **Lost lines fail.** A layer with fewer lines drawn than sent would
  look tidy and be missing words. Any mismatch, in either direction, now
  fails the pass and says which happened.
- **Re-wraps are caught.** More lines drawn than sent means Pixelmator
  re-broke the layout and what you got is not what was verified.
- **Refusals are honest.** "Will not fit" now means the shape is too
  small for the text, and every attempt is logged, successes and
  failures alike.

## Ignore Notch

A deep bite out of the top or bottom edge — an arch standing on two legs
— costs more than it looks: the lines above it are squeezed into the
strip that clears it, and the legs stay empty, because text cannot read
down one and up the other. Ticking **Ignore Notch** treats it as filled
and runs the lines straight across.

Text then sits over the notch. That is the point, and tidying it is
yours. Notches in the sides are never touched — a flag's swallowtail is a
different problem — and neither are shapes whose gaps are the design,
like a crown, where it should be left off.

## Interface

- **The next step is highlighted.** Reread, then Try, then Apply — each
  takes Return and the blue in turn, and nothing is highlighted once a
  fit has been applied.
- **Word and character count** beside the Text heading.
- **Every button answers the first click**, including the first click
  after returning from Pixelmator.
- **The checkbox works.** The status line was overlapping it and taking
  the clicks.
- **The finished layer's box fits its text**, with room either side to
  grab, instead of being several times the width of the artwork.
- **Info** now says what you may need to finish by hand, and what the app
  cannot do: Pixelmator exposes neither line height nor character
  spacing to AppleScript, so no script can set them.

## Safety

Reading a shape hides every other layer, exports, and restores them. If
the app stopped in between, the document could be left with one visible
layer and everything else off. A snapshot is now written before anything
is hidden, and any stale one found puts every layer back.

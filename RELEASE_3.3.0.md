# PixProFitText 3.3.0

Everything since 2.7.3. The headline is that text now fits on the first
try instead of shrinking until it gives up — and when it genuinely cannot
fit, it says so instead of quietly placing something wrong.

## The size collapse is fixed

A fit predicted at 19 pt would be applied at 6 pt, having walked down
through 18, 17, 16, 14, 12, 10, 8 and still left ink outside the shape.

The cause was one wrong assumption. Pixelmator sets a line **a constant
79 pixels wider** than the app models it — measured at thirteen sizes
from 6 pt to 72 pt, the difference never moved. That was being treated as
a *ratio*, which reads as 1.04 at 72 pt and 1.53 at 6 pt. So every time
the verify loop shrank the type, the fixed offset became a larger share
of a smaller line, the error grew as fast as the size fell, and it could
never converge.

Width is now an offset and height remains a factor, which is what they
each measurably are. Fits settle in one pass with nothing outside the
shape.

## Nothing is placed quietly any more

- **Lost lines fail.** Seven lines sent and five drawn was logged and
  ignored; a layer would look tidy and be missing words. Any mismatch,
  in either direction, now fails the pass and says which happened.
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
- **Every button answers the first click.** Returning from Pixelmator,
  the first click used to be spent activating the window.
- **The checkbox works.** The status line was sitting on top of it and
  swallowing the clicks, leaving a four-pixel strip that could be hit by
  luck — which is why it seemed to ignore the mouse at random.
- **The finished layer's box fits its text**, with room either side to
  grab, instead of being several times the width of the artwork.
- **Info** now says what you may need to finish by hand, and what the app
  cannot do: Pixelmator exposes neither line height nor character
  spacing to AppleScript, so no script can set them.

## Safety

Reading a shape hides every other layer, exports, and restores them. If
the app died in between, the document was left with one visible layer and
everything else off — indistinguishable from the artwork having been
deleted. A snapshot is now written before anything is hidden, and any
stale one found puts every layer back.

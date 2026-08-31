# PixProFitText

Fits a block of text inside an irregular Pixelmator Pro shape, at the largest
size that stays inside the outline.

Select a shape layer, type or paste the text, press **Try** to see it, press
**Apply** to put it on the canvas as an ordinary editable text layer.

![text fitted to a pentagon, with the app beside it](docs/screenshot.png)

## What it does

* Reads the **selected shape layer** and fits to its **outer** boundary. Holes
  inside the shape are fine to cover — only the outline constrains the text.
* **Follows the shape**: the text is re-flowed so each line is as long as the
  row it sits on allows. Lines shorten where the shape narrows.
* Picks the **justification from the shape** — a straight edge on one side
  reads as text aligned to it — with an override when it reads the shape
  differently than you do.
* Rotates to any **angle**, and will find the angle that fits the largest text.
* Each **Apply** makes its own layer, named for the shape, so earlier fits
  survive.

## Using it

| Control | What it does |
| --- | --- |
| **Reread shape** | re-reads the selected shape layer out of Pixelmator |
| **Try** | works out the fit and previews it — nothing reaches the canvas |
| **Apply** | places it as a new text layer, then checks it really fits |
| **Best angle** | tries every angle in 5° steps and keeps the largest fit |
| **Follow the shape** | on: re-flow per row. off: your own line breaks, scaled as one block |
| **Align** | Auto reads it off the shape; Left / Center / Right force it |
| **Margin** | pixels of clearance kept between the ink and the outline |
| **Info** | what the app promises, and what it leaves to you |

Nothing is recomputed while you type. **Try** is what does the work, so pasting
a long passage does not set off a fit you did not ask for.

## Finishing by hand

The result is an ordinary text layer. Everything in Pixelmator's **Text panel**
still applies — alignment, Line Height, Before/After Paragraph, Indents, and
the two Convert buttons.

Reach for **Line Height** first. It is also the one thing no script can set:
Pixelmator exposes no leading, spacing, kerning or tracking property anywhere
in its dictionary, so opening the spacing up by hand is the intended finish
rather than a workaround.

An attempt was made to pre-compensate for this — fit smaller so there was room
to loosen the spacing afterwards — and it was removed. It cannot work in
shape-following mode: each line's *length* is chosen for the row it sits on, so
inflating the model puts lines on rows they were never sized for, and a long
line lands in a notch. That is a line-pitch error rather than a scale error, so
shrinking never clears it.

## Known limits

* **Notches are hard.** A line is sized for its row, so anything that moves the
  lines vertically afterwards — including your own Line Height change — can
  push a long line into a gap.
* **The width ratio is size-dependent.** Pixelmator sets text about 3% wider
  than AppKit at 72pt but around 10% wider at 12pt, because per-glyph advances
  round to whole pixels and that rounding is proportionally far larger at small
  sizes. The calibration stores one number; the verify loop absorbs the rest.
* **Line spacing is not scriptable at all** — see above.

## How it works

1. **Export the shape.** The selected layer is soloed, exported, and its
   visibility restored *by layer id*, so a failure cannot leave the document
   soloed or switch the wrong layers back on.
2. **Flow the text.** For each candidate size, each line is given the widest
   run of the shape that is clear for the whole height of that line — every row
   of the line is ANDed together, so an ascender cannot cross the outline.
3. **Place it.** The text mask and the shape are cross-correlated with an FFT,
   which scores every possible offset at once; the valid offset nearest the
   shape's centroid wins.
4. **Calibrate.** Pixelmator does not typeset identically to AppKit — it sets a
   line wider by a factor, and its line pitch is looser by a factor. Both are
   measured once per font from probes drawn in a *scratch document*, never in
   yours.
5. **Verify.** After the layer is placed, its ink is exported and compared with
   the shape. Ink outside the outline is either too big (shrink) or in the
   wrong place (nudge), and the two are told apart rather than both answered by
   shrinking.

## Building

    ./build.sh              build and sign into dist/
    ./build.sh --install    also install to /Applications

Signing uses a Developer ID identity selected **by SHA-1 hash**, not by name —
expired certificates with similar names sit in the keychain and signing by name
can pick a dead one. `codesign --deep` is not enough for a py2app bundle: it
skips the `.so` files under `Resources/lib` and the extension-less Mach-O at
`Contents/MacOS/python`, which is exactly what notarization rejects. The script
walks the bundle and signs anything `file` reports as Mach-O.

    ./release.sh            notarize, staple, and wrap it in a DMG

`build.sh` signs but does not notarize; `release.sh` does both the app and
the DMG, and staples each. Stapling the app matters because that is what gets
dragged out of the DMG, and stapling the DMG matters because that is what
gets downloaded — notarizing only one leaves a Gatekeeper warning on the
other. No password is typed: it uses the `PixProNotary` keychain profile.

**Pillow must be a `package`, not an `include`.** py2app compiles an
`include` into `Contents/Resources/lib/python314.zip`, and `codesign` cannot
reach inside a zip — so Pillow's 18 bundled dylibs shipped unsigned and Apple
rejected the whole archive. As a `package` it is copied out as a real
directory tree where the Mach-O walk signs every one of them.

## Files

    pixprofittext.py     the app: window, controls, preview, settings
    fittext_engine.py    the geometry — masks, flow, placement. No Pixelmator.
    pixbridge.py         every line of AppleScript that talks to Pixelmator
    build.sh             build, sign, install
    release.sh           notarize, staple, and build the DMG
    make_icon.py         builds the icns from icon/
    setup.py             py2app configuration

`fittext_engine.py` has no Pixelmator dependency at all and can be exercised on
its own — give it a boolean mask and a string.

## Requirements

macOS 26, Pixelmator Pro, Python 3.14 with PyObjC, numpy and Pillow in `venv/`.
Two Pixelmator builds may be installed at once; the app binds by **bundle id**
at run time and prefers whichever one has a document open.

## Licence

MIT. See [LICENSE](LICENSE).

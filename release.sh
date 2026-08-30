#!/bin/zsh
# Notarize PixProFitText.app and wrap it in a distributable DMG — v1.0.0
#
# Run ./build.sh first; this takes dist/PixProFitText.app as it finds it.
#
# Notarization uses the same keychain profile as Stache, the PixPro apps and
# KBD, so no password lives here or gets typed. If the profile is ever lost:
#   xcrun notarytool store-credentials "PixProNotary" \
#       --apple-id <appleid> --team-id RUDN8D7ZN9
#
# Both the app and the DMG are notarized and stapled. Stapling the app
# matters because that is what gets dragged out of the DMG; stapling the DMG
# matters because that is what gets downloaded. Notarizing only one of the
# two leaves a Gatekeeper warning on the other.
#
# Unlike Stache, this app has NO LaunchAgent — nothing relaunches it — so
# there is no agent to unload around the install, and it must be launched by
# hand afterwards.
set -e
cd "${0:A:h}"

SIGN_ID="4208ABA3EC12F24C1F09C7BB624EFF68B44259DB"
PROFILE="PixProNotary"
APP="dist/PixProFitText.app"
VOLNAME="PixProFitText"

[[ -d "$APP" ]] || { echo "error: $APP not found — run ./build.sh first" >&2; exit 1; }

VERSION=$(plutil -extract CFBundleShortVersionString raw "$APP/Contents/Info.plist")
DMG="dist/PixProFitText-${VERSION}.dmg"

xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1 \
    || { echo "error: no notary profile '$PROFILE' in keychain" >&2; exit 1; }

echo "==> notarizing the app (PixProFitText $VERSION)"
rm -f dist/PixProFitText_notarize.zip
ditto -c -k --keepParent "$APP" dist/PixProFitText_notarize.zip
xcrun notarytool submit dist/PixProFitText_notarize.zip \
    --keychain-profile "$PROFILE" --wait
xcrun stapler staple "$APP"

echo "==> building the disk image"
rm -rf dist/dmg "$DMG"
mkdir -p dist/dmg
cp -R "$APP" dist/dmg/
ln -s /Applications dist/dmg/Applications
# hdiutil intermittently returns "Resource busy" on a folder written seconds
# earlier — something (Spotlight, on-access AV) still has it open. It clears
# on its own, so retry rather than abandoning a build whose app is already
# notarized and stapled.
for attempt in 1 2 3 4 5; do
    if hdiutil create -volname "$VOLNAME" -srcfolder dist/dmg -ov \
            -format UDZO "$DMG" >/dev/null 2>/tmp/pixprofittext_hdiutil.err; then
        break
    fi
    echo "    hdiutil attempt $attempt failed: $(tr -d '\n' < /tmp/pixprofittext_hdiutil.err)"
    if [[ $attempt == 5 ]]; then
        echo "error: could not build the disk image" >&2
        exit 1
    fi
    sleep 5
done
rm -rf dist/dmg

echo "==> signing and notarizing the disk image"
codesign --force --timestamp --sign "$SIGN_ID" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait
xcrun stapler staple "$DMG"

echo "==> installing the stapled app to /Applications"
pkill -x PixProFitText 2>/dev/null || true
sleep 1
rm -rf /Applications/PixProFitText.app
cp -R "$APP" /Applications/
xattr -dr com.apple.quarantine /Applications/PixProFitText.app 2>/dev/null || true

echo "==> results"
echo "    dmg:      $DMG  ($(du -h "$DMG" | cut -f1))"
echo "    stapled:  app $(xcrun stapler validate "$APP" >/dev/null 2>&1 && echo YES || echo no), dmg $(xcrun stapler validate "$DMG" >/dev/null 2>&1 && echo YES || echo no)"
spctl -a -t open --context context:primary-signature -v "$DMG" 2>&1 | sed 's/^/    gatekeeper: /'
echo "    running instances: $(pgrep -x PixProFitText | wc -l | tr -d ' ')  (no LaunchAgent — relaunch by hand)"

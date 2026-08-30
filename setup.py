"""py2app build for PixProFitText.app

    ./venv/bin/python make_icon.py
    ./venv/bin/python setup.py py2app

Not LSUIElement: unlike the PixPro one-shot applets this is a window you work
in, alongside Pixelmator, so it wants a Dock icon and to be switchable.
"""
import re
from pathlib import Path
from setuptools import setup

APP = ["pixprofittext.py"]


def app_version():
    source = Path(__file__).with_name("pixprofittext.py").read_text()
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if not match:
        raise SystemExit("setup.py: APP_VERSION not found")
    return match.group(1)


VERSION = app_version()

setup(
    name="PixProFitText",
    app=APP,
    options={"py2app": {
        "argv_emulation": False,
        # py2app strips bundled binaries by default, and strip mangles some
        # of them badly enough that codesign refuses them outright:
        # "main executable failed strict validation" on liblzma, which could
        # then be neither signed nor un-signed.
        "strip": False,
        "iconfile": "icon/PixProFitText.icns",
        "includes": ["fittext_engine", "pixbridge", "numpy", "PIL"],
        "excludes": ["tkinter", "test", "unittest"],
        "plist": {
            "CFBundleName": "PixProFitText",
            "CFBundleDisplayName": "PixProFitText",
            "CFBundleIdentifier": "com.timmccoy.pixprofittext",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright":
                "Copyright © 2026 Tim McCoy. All rights reserved.",
            "CFBundleGetInfoString":
                "PixProFitText — fit text inside a shape in Pixelmator Pro.",
            # It drives Pixelmator Pro over Apple events, so it must say so.
            "NSAppleEventsUsageDescription":
                "PixProFitText reads the selected shape from Pixelmator Pro "
                "and adds the fitted text layer back to your document.",
        },
    }},
    setup_requires=["py2app"],
)

import sys

import py2app

__all__ = ["infoPlistDict"]


def infoPlistDict(CFBundleExecutable, plist={}):  # noqa: B006, M511
    CFBundleExecutable = CFBundleExecutable
    version = sys.version[:3]
    pdict = {
        "CFBundleDevelopmentRegion": "English",
        "CFBundleDisplayName": plist.get("CFBundleName", CFBundleExecutable),
        "CFBundleExecutable": CFBundleExecutable,
        "CFBundleIconFile": CFBundleExecutable,
        "CFBundleIdentifier": f"org.pythonmac.unspecified.{''.join(CFBundleExecutable.split())}",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": CFBundleExecutable,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": plist.get("CFBundleVersion", "0.0"),
        "CFBundleSignature": "????",
        "CFBundleVersion": "0.0",
        "LSHasLocalizedDisplayName": False,
        "NSAppleScriptEnabled": False,
        "NSHumanReadableCopyright": "Copyright not specified",
        "NSMainNibFile": "MainMenu",
        "NSPrincipalClass": "NSApplication",
        "PyMainFileNames": ["__boot__"],
        "PyResourcePackages": [],
        "PyRuntimeLocations": [
            (s % version)
            for s in [
                (
                    "@executable_path/../Frameworks/Python.framework"
                    "/Versions/%s/Python"
                ),
                "~/Library/Frameworks/Python.framework/Versions/%s/Python",
                "/Library/Frameworks/Python.framework/Versions/%s/Python",
                "/Network/Library/Frameworks/Python.framework/Versions/%s/Python",
                "/System/Library/Frameworks/Python.framework/Versions/%s/Python",
            ]
        ],
    }
    pdict.update(plist)
    pythonInfo = pdict.setdefault("PythonInfoDict", {})
    pythonInfo.update(
        {
            "PythonLongVersion": sys.version,
            "PythonShortVersion": ".".join(str(x) for x in sys.version_info[:2]),
            "PythonExecutable": sys.executable,
        }
    )
    py2appInfo = pythonInfo.setdefault("py2app", {})
    py2appInfo.update(
        {
            "version": py2app.__version__,
            "template": "app",
        }
    )
    return pdict

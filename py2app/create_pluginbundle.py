import importlib.resources
import os
import plistlib
import shutil
import sys

import py2app.bundletemplate
from py2app.util import make_exec, makedirs, mergecopy, mergetree, skipscm


def create_pluginbundle(
    destdir,
    name,
    extension=".plugin",
    module=py2app.bundletemplate,
    platform="MacOS",
    copy=mergecopy,
    mergetree=mergetree,
    condition=skipscm,
    plist=None,
    arch=None,
):
    if plist is None:
        plist = {}

    kw = module.plist_template.infoPlistDict(
        plist.get("CFBundleExecutable", name), plist
    )
    plugin = os.path.join(destdir, kw["CFBundleName"] + extension)
    if os.path.exists(plugin):
        # Remove any existing build artifacts to ensure
        # we're getting a clean build
        shutil.rmtree(plugin)
    contents = os.path.join(plugin, "Contents")
    resources = os.path.join(contents, "Resources")
    platdir = os.path.join(contents, platform)
    dirs = [contents, resources, platdir]
    plist = {}
    plist.update(kw)
    plistPath = os.path.join(contents, "Info.plist")
    if os.path.exists(plistPath):
        with open(plistPath, "rb") as fp:
            contents = plistlib.load(fp)

            if plist != contents:
                for d in dirs:
                    shutil.rmtree(d, ignore_errors=True)
    for d in dirs:
        makedirs(d)

    with open(plistPath, "wb") as fp:
        if hasattr(plistlib, "dump"):
            plistlib.dump(plist, fp)
        else:
            plistlib.writePlist(plist, fp)
    srcmain = module.setup.main(arch=arch)
    destmain = os.path.join(platdir, kw["CFBundleExecutable"])
    with open(os.path.join(contents, "PkgInfo"), "w") as fp:
        fp.write(kw["CFBundlePackageType"] + kw["CFBundleSignature"])
    copy(srcmain, destmain)
    make_exec(destmain)
    with importlib.resources.path(module.__name__, "lib") as p:
        mergetree(
            str(p),
            resources,
            condition=condition,
            copyfn=copy,
        )
    return plugin, plist


if __name__ == "__main__":
    create_pluginbundle("build", sys.argv[1])

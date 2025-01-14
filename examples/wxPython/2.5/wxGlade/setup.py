"""
Script for building the example.

Usage:
    python setup.py py2app
"""
import glob
import os
import sys

from setuptools import setup

NAME = "wxGlade"
VERSION = "0.3.4"
WXDIR = f"{NAME}-{VERSION}"

# these are files and packages
WIDGETS = os.path.join(WXDIR, "widgets", "")
# these are files
CODEGEN = os.path.join(WXDIR, "codegen", "")


def data_files_as_code(mf, wxdir):
    for fn in os.listdir(wxdir):
        if os.path.exists(os.path.join(wxdir, fn, "__init__.py")):
            mf.import_hook(fn, None, ["*"])
        elif fn.endswith(".py"):
            mf.import_hook(fn[: -len(".py")])


# make sure it can find everything it wants
sys.path[:0] = [WXDIR, WIDGETS, CODEGEN]


class wxglade_recipe:
    def check(self, dist, mf):
        m = mf.findNode("wxglade")
        if m is None:
            return None
        paths = [os.path.join(os.path.realpath(p), "") for p in (WIDGETS, CODEGEN)]
        for path in paths:
            data_files_as_code(mf, path)

        def filterfunc(mod, paths=paths):
            for path in paths:
                if getattr(mod, "filename", "").startswith(path):
                    return False
            return True

        return {
            "filters": [filterfunc],
        }


def get_data_files(paths):
    lst = []
    for f in paths:
        lst.extend(glob.glob(os.path.join(WXDIR, f)))
    return [("", lst)]


import py2app.recipes  # noqa: E402

py2app.recipes.wxglade = wxglade_recipe()

setup(
    app=["wxGlade.py"],
    data_files=get_data_files(["*.txt", "docs", "res", "widgets", "codegen", "icons"]),
    options={
        "py2app": {
            "argv_emulation": True,
            "compressed": True,
        }
    },
    setup_requires=["py2app"],
)

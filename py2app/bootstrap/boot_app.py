import re
import sys

cookie_re = re.compile(rb"coding[:=]\s*([-\w.]+)")
default_encoding = "utf-8"


def guess_encoding(fp):
    for _i in range(2):
        ln = fp.readline()

        m = cookie_re.search(ln)
        if m is not None:
            return m.group(1).decode("ascii")

    return default_encoding


def _run():
    global __file__
    import os
    import site  # noqa: F401

    sys.frozen = "macosx_app"
    base = os.environ["RESOURCEPATH"]

    argv0 = os.path.basename(os.environ["ARGVZERO"])
    script = SCRIPT_MAP.get(argv0, DEFAULT_SCRIPT)  # noqa: F821

    path = os.path.join(base, script)
    sys.argv[0] = __file__ = path
    with open(path, "rb") as fp:
        encoding = guess_encoding(fp)

    with open(path, encoding=encoding) as fp:
        source = fp.read() + "\n"

    BOM = b"\xef\xbb\xbf".decode("utf-8")
    if source.startswith(BOM):
        source = source[1:]

    exec(compile(source, path, "exec"), globals(), globals())

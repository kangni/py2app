def check(cmd, mf):
    m = mf.findNode("ctypes")
    if m is None or m.filename is None:
        return None

    return {"prescripts": ["py2app.bootstrap.ctypes_setup"]}

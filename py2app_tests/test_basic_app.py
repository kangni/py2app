"""
Test case for building an app bundle with a command-line tool, that bundle
is than queried in the various test methods to check if the app bundle
is correct.

This is basically a black-box functional test of the core py2app functionality

The app itself:
    - main script has 'if 0: import modules'
    - main script has a loop that reads and exec-s statements
    - the 'modules' module depends on a set of modules/packages through
      various forms of imports (absolute, relative, old-style python2,
      namespace packages 'pip-style', namespace package other,
      zipped eggs and non-zipped eggs, develop eggs)
    - add another test that does something simular, using virtualenv to
      manage a python installation
"""
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import time
import unittest
from distutils.sysconfig import get_config_var

import py2app

from .tools import kill_child_processes

DIR_NAME = os.path.dirname(os.path.abspath(__file__))


def make_checksums(path):
    result = {}
    for root, dnames, fnames in os.walk(path):
        for dn in dnames:
            result[os.path.join(root, dn)] = None

        for fn in fnames:
            h = hashlib.sha1()
            p = os.path.join(root, fn)
            if os.path.islink(p):
                result[p] = os.readlink(p)

            else:
                with open(p, "rb") as fp:
                    block = fp.read(10240)
                    while block:
                        h.update(block)
                        block = fp.read(10240)

                result[p] = h.hexdigest()


class TestBasicApp(unittest.TestCase):
    py2app_args = []
    python_args = []
    app_dir = os.path.join(DIR_NAME, "basic_app")

    # Basic setup code
    #
    # The code in this block needs to be moved to
    # a base-class.
    @classmethod
    def setUpClass(cls):
        kill_child_processes()

        env = os.environ.copy()
        pp = os.path.dirname(os.path.dirname(py2app.__file__))
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = pp + ":" + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = pp

        if "LANG" not in env:
            # Ensure that testing though SSH works
            env["LANG"] = "en_US.UTF-8"

        p = subprocess.Popen(
            [sys.executable]
            + cls.python_args
            + ["setup.py", "py2app"]
            + cls.py2app_args,
            cwd=cls.app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=False,
            env=env,
        )
        lines = p.communicate()[0]
        if p.wait() != 0:
            print(lines)
            raise AssertionError("Creating basic_app bundle failed")

        cls.checksums = make_checksums(os.path.join(cls.app_dir, "dist/BasicApp.app"))

    def assertChecksumsSame(self):
        self.assertEqual(
            self.checksums,
            make_checksums(os.path.join(self.app_dir, "dist/BasicApp.app")),
        )

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(os.path.join(cls.app_dir, "build")):
            shutil.rmtree(os.path.join(cls.app_dir, "build"))

        if os.path.exists(os.path.join(cls.app_dir, "dist")):
            shutil.rmtree(os.path.join(cls.app_dir, "dist"))

        time.sleep(2)

    def tearDown(self):
        kill_child_processes()
        time.sleep(1)

    def start_app(self):
        # Start the test app, return a subprocess object where
        # stdin and stdout are connected to pipes.
        path = os.path.join(self.app_dir, "dist/BasicApp.app/Contents/MacOS/BasicApp")

        p = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            close_fds=False,
        )
        # stderr=subprocess.STDOUT)
        return p

    def wait_with_timeout(self, proc, timeout=10):
        for _ in range(timeout):
            x = proc.poll()
            if x is None:
                time.sleep(1)
            else:
                return x

        os.kill(proc.pid, signal.SIGKILL)
        return proc.wait()

    #
    # End of setup code
    #

    def test_basic_start(self):
        p = self.start_app()

        p.stdin.close()

        status = self.wait_with_timeout(p)
        self.assertEqual(status, 0)

        p.stdout.close()

        self.assertChecksumsSame()

    def test_simple_imports(self):
        p = self.start_app()

        # Basic module that is always present:
        p.stdin.write(b'import_module("os")\n')
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), b"os")

        # Dependency of the main module:
        p.stdin.write(b'import_module("decimal")\n')
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), b"decimal")

        can_import_stdlib = False
        if "--alias" in self.py2app_args:
            can_import_stdlib = True

        if "--semi-standalone" in self.py2app_args:
            can_import_stdlib = True

        if sys.prefix.startswith("/System/"):
            can_import_stdlib = True

        if not can_import_stdlib:
            # Not a dependency of the module (stdlib):
            p.stdin.write(b'import_module("xdrlib")\n')
            p.stdin.flush()
            ln = p.stdout.readline().decode("utf-8")
            self.assertTrue(ln.strip().startswith("* import failed"), ln)

        else:
            p.stdin.write(b'import_module("xdrlib")\n')
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"xdrlib")

        if sys.prefix.startswith("/System") or "--alias" in self.py2app_args:
            # py2app is included as part of the system install
            p.stdin.write(b'import_module("py2app")\n')
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"py2app")

        else:
            # Not a dependency of the module (external):
            p.stdin.write(b'import_module("py2app")\n')
            p.stdin.flush()
            ln = p.stdout.readline().decode("utf-8")
            self.assertTrue(ln.strip().startswith("* import failed"), ln)

        p.stdin.close()
        p.stdout.close()
        status = self.wait_with_timeout(p)
        self.assertEqual(status, 0)
        self.assertChecksumsSame()

    def test_is_optimized(self):
        p = self.start_app()

        try:
            p.stdin.write(b"print(__debug__)\n")
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"True")

        finally:
            p.stdin.close()
            p.stdout.close()
            status = self.wait_with_timeout(p)
            self.assertEqual(status, 0)

        self.assertChecksumsSame()

    def test_framework_versions(self):
        fwk = get_config_var("PYTHONFRAMEWORK")
        path = os.path.join(
            self.app_dir, f"dist/BasicApp.app/Contents/Frameworks/{fwk}.framework"
        )
        if not os.path.exists(path):
            return

        names = {
            nm for nm in os.listdir(os.path.join(path, "Versions")) if "-" not in nm
        }
        ver_str = "%d.%d" % sys.version_info[:2]
        self.assertEqual(names, {"Current", ver_str})
        self.assertEqual(
            os.readlink(os.path.join(path, "Versions", "Current")), ver_str
        )

        self.assertEqual(
            os.readlink(os.path.join(path, fwk)),
            os.path.join("Versions", "Current", fwk),
        )
        self.assertEqual(
            os.readlink(os.path.join(path, "Resources")),
            os.path.join("Versions", "Current", "Resources"),
        )

    def test_python_executable_mode(self):
        path = os.path.join(self.app_dir, "dist/BasicApp.app/Contents/MacOS/python")

        self.assertTrue(os.path.exists(path))
        mode = os.stat(path).st_mode
        self.assertTrue(mode & 0o001, "Not executable for other")
        self.assertTrue(mode & 0o010, "Not executable for group")
        self.assertTrue(mode & 0o100, "Not executable for user")

    def test_python_executable_use(self):
        p = self.start_app()

        try:
            p.stdin.write(b"run_python()\n")
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"ok")

        finally:
            p.stdin.close()
            p.stdout.close()
            status = self.wait_with_timeout(p)
            self.assertEqual(status, 0)


class TestBasicAliasApp(TestBasicApp):
    py2app_args = [
        "--alias",
    ]


class TestBasicSemiStandaloneApp(TestBasicApp):
    py2app_args = [
        "--semi-standalone",
    ]


class TestBasicAppScriptName(unittest.TestCase):
    app_dir = os.path.join(DIR_NAME, "basic_app2")

    def test_email_not_included(self):
        path = os.path.join(
            self.app_dir,
            "dist/BasicApp.app/Contents/Resources/lib/python%d.%d"
            % sys.version_info[:2],
        )
        if os.path.exists(os.path.join(path, "email")):
            self.fail("'email' package copied into a semi-standalone build")


class TestBasicAliasAppScriptName(TestBasicAppScriptName):
    py2app_args = [
        "--alias",
    ]


class TestBasicSemiStandaloneAppScriptName(TestBasicAppScriptName):
    py2app_args = [
        "--semi-standalone",
    ]


class TestBasicAppWindowsLineEnd(TestBasicApp):
    app_dir = os.path.join(DIR_NAME, "basic_app_winle")

    @classmethod
    def setUpClass(cls):
        try:
            if os.path.exists(cls.app_dir):
                shutil.rmtree(cls.app_dir)

            assert not os.path.exists(cls.app_dir)
            shutil.copytree(TestBasicApp.app_dir, cls.app_dir)

            # Convert python files to Windows line endings
            for fn in os.listdir(cls.app_dir):
                if not fn.endswith(".py"):
                    continue

                path = os.path.join(cls.app_dir, fn)
                with open(path, "rb") as fp:
                    data_in = fp.read()

                data_out = data_in.replace(b"\n", b"\r\n")
                if data_out == data_in:
                    raise AssertionError("Data not changed")
                with open(path, "wb") as fp:
                    fp.write(data_out)

            super().setUpClass()

        except:  # noqa: E722, B001
            if os.path.exists(cls.app_dir):
                shutil.rmtree(cls.app_dir)

            raise

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.app_dir):
            shutil.rmtree(cls.app_dir)


class TestBasicAliasAppWindowsLineEnd(TestBasicAppWindowsLineEnd):
    py2app_args = [
        "--alias",
    ]


class TestBasicSemiStandaloneAppWindowsLineEnd(TestBasicAppWindowsLineEnd):
    py2app_args = [
        "--semi-standalone",
    ]


class TestBasicAppUnicodePath(TestBasicApp):
    app_dir = os.path.join(DIR_NAME, "basic_app " + chr(2744))

    @classmethod
    def setUpClass(cls):
        try:
            if os.path.exists(cls.app_dir):
                shutil.rmtree(cls.app_dir)

            assert not os.path.exists(cls.app_dir)
            shutil.copytree(TestBasicApp.app_dir, cls.app_dir)

            super().setUpClass()

        except:  # noqa: E722, B001
            if os.path.exists(cls.app_dir):
                shutil.rmtree(cls.app_dir)

            raise

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.app_dir):
            shutil.rmtree(cls.app_dir)

    @unittest.expectedFailure
    def test_python_executable_use(self):
        self.fail("loading codecs fails on py36i")


class TestBasicAliasAppUnicodePath(TestBasicAppUnicodePath):
    py2app_args = [
        "--alias",
    ]


class TestBasicSemiStandaloneAppUnicodePath(TestBasicAppUnicodePath):
    py2app_args = [
        "--semi-standalone",
    ]


class TestOptimized1(TestBasicApp):
    py2app_args = ["-O1"]

    def test_is_optimized(self):
        p = self.start_app()

        try:
            p.stdin.write(b"print(__debug__)\n")
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"False")

        finally:
            p.stdin.close()
            p.stdout.close()
            status = self.wait_with_timeout(p)
            self.assertEqual(status, 0)

        self.assertChecksumsSame()


class TestOptimized2(TestBasicApp):
    py2app_args = ["-O2"]

    def test_is_optimized(self):
        p = self.start_app()

        try:
            p.stdin.write(b"print(__debug__)\n")
            p.stdin.flush()
            ln = p.stdout.readline()
            self.assertEqual(ln.strip(), b"False")

        finally:
            p.stdin.close()
            p.stdout.close()
            status = self.wait_with_timeout(p)
            self.assertEqual(status, 0)

        self.assertChecksumsSame()

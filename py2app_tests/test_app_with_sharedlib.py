import os
import shutil
import signal
import subprocess
import sys
import time
import unittest

import py2app

from .tools import kill_child_processes

DIR_NAME = os.path.dirname(os.path.abspath(__file__))


class TestBasicAppWithExtension(unittest.TestCase):
    py2app_args = []
    python_args = []
    app_dir = os.path.join(DIR_NAME, "app_with_sharedlib")

    # Basic setup code
    #
    # The code in this block needs to be moved to
    # a base-class.
    @classmethod
    def setUpClass(cls):
        kill_child_processes()

        cls.tearDownClass()

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
            [sys.executable] + cls.python_args + ["setup.py", "build_ext"],
            cwd=cls.app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=False,
            env=env,
        )
        lines = p.communicate()[0]
        if p.wait() != 0:
            print(lines)
            raise AssertionError("Running build_ext failed")

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

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(os.path.join(cls.app_dir, "build")):
            shutil.rmtree(os.path.join(cls.app_dir, "build"))

        if os.path.exists(os.path.join(cls.app_dir, "dist")):
            shutil.rmtree(os.path.join(cls.app_dir, "dist"))

        if os.path.exists(os.path.join(cls.app_dir, "lib")):
            shutil.rmtree(os.path.join(cls.app_dir, "lib"))

        for fn in os.listdir(cls.app_dir):
            if fn.endswith(".so"):
                os.unlink(os.path.join(cls.app_dir, fn))

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

    def test_extension_use(self):
        p = self.start_app()

        p.stdin.write(b"print(double(9))\n")
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), b"18")

        p.stdin.write(b"print(square(9))\n")
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), b"81")

        p.stdin.write(b"print(half(16))\n")
        p.stdin.flush()
        ln = p.stdout.readline()
        self.assertEqual(ln.strip(), b"8")

        p.stdin.close()

        status = self.wait_with_timeout(p)
        self.assertEqual(status, 0)

        p.stdout.close()

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

        status = self.wait_with_timeout(p)
        self.assertEqual(status, 0)

        p.stdout.close()

    def test_app_structure(self):
        path = os.path.join(self.app_dir, "dist/BasicApp.app")

        if "--alias" in self.py2app_args:
            self.assertFalse(
                os.path.exists(
                    os.path.join(path, "Contents", "Frameworks", "libshared.1.dylib")
                )
            )
            self.assertFalse(
                os.path.exists(
                    os.path.join(path, "Contents", "Frameworks", "libshared.dylib")
                )
            )
            self.assertFalse(
                os.path.exists(
                    os.path.join(path, "Contents", "Frameworks", "libhalf.dylib")
                )
            )

        else:
            self.assertTrue(
                os.path.isfile(
                    os.path.join(path, "Contents", "Frameworks", "libshared.1.dylib")
                )
            )
            self.assertTrue(
                os.path.islink(
                    os.path.join(path, "Contents", "Frameworks", "libshared.dylib")
                )
            )
            self.assertEqual(
                os.readlink(
                    os.path.join(path, "Contents", "Frameworks", "libshared.dylib")
                ),
                "libshared.1.dylib",
            )
            self.assertTrue(
                os.path.isfile(
                    os.path.join(path, "Contents", "Frameworks", "libhalf.dylib")
                )
            )


class TestBasicAliasAppWithExtension(TestBasicAppWithExtension):
    py2app_args = [
        "--alias",
    ]


class TestBasicSemiStandaloneAppWithExtension(TestBasicAppWithExtension):
    py2app_args = [
        "--semi-standalone",
    ]

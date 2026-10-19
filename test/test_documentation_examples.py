"""Tests that verify code examples in docs/ execute and generate valid Cython pxd files."""

import subprocess
import sys
import textwrap

from click.testing import CliRunner

from autopxd import cli


class TestDocumentationExamples:
    """Ensure all user-facing documentation code examples are tested and work."""

    def test_quickstart_c_example(self) -> None:
        """Test the C Point example from docs/getting-started/quickstart.md."""
        header_code = textwrap.dedent("""\
            typedef struct {
                int x;
                int y;
            } Point;

            Point create_point(int x, int y);
            double distance(Point a, Point b);
        """)
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("example.h", "w") as f:
                f.write(header_code)

            result = runner.invoke(cli, ["example.h", "example.pxd"])
            assert result.exit_code == 0
            with open("example.pxd") as f:
                pxd_output = f.read()

            assert 'cdef extern from "example.h":' in pxd_output
            assert "ctypedef struct Point:" in pxd_output or "cdef struct Point:" in pxd_output
            assert "Point create_point(int x, int y)" in pxd_output
            assert "double distance(Point a, Point b)" in pxd_output

            # Verify Cython can parse this pxd
            with open("test_module.pyx", "w") as f:
                f.write(
                    textwrap.dedent("""\
                    from example cimport Point, create_point, distance

                    def make_point(x: int, y: int):
                        cdef Point p = create_point(x, y)
                        return (p.x, p.y)
                """)
                )
            res = subprocess.run(
                [sys.executable, "-m", "cython", "-3", "-I", ".", "test_module.pyx"],
                capture_output=True,
                text=True,
            )
            assert res.returncode == 0, f"Cython failed:\n{res.stderr}"

    def test_cpp_support_guide_example(self) -> None:
        """Test the C++ Widget class example from docs/user-guide/cpp.md."""
        cpp_header = textwrap.dedent("""\
            class BaseWidget {
            public:
                virtual void show();
            };

            class Widget : public BaseWidget {
            public:
                int width;
                int height;
                Widget();
                Widget(int w, int h);
                virtual ~Widget();
                int area() const;
                static Widget create();
            };

            template<typename T>
            T max_val(T a, T b);
        """)
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("widget.hpp", "w") as f:
                f.write(cpp_header)

            result = runner.invoke(cli, ["--cpp", "widget.hpp", "widget.pxd"])
            assert result.exit_code == 0
            with open("widget.pxd") as f:
                pxd_output = f.read()

            assert 'cdef extern from "widget.hpp":' in pxd_output
            assert "cdef cppclass Widget(BaseWidget):" in pxd_output
            assert "int width" in pxd_output
            assert "int height" in pxd_output
            assert "Widget()" in pxd_output
            assert "Widget(int w, int h)" in pxd_output
            assert "int area() const" in pxd_output
            assert "@staticmethod" in pxd_output
            assert "Widget create()" in pxd_output
            assert "T max_val[T](T a, T b)" in pxd_output

            # Verify Cython can parse this C++ pxd
            with open("widget_wrap.pyx", "w") as f:
                f.write(
                    textwrap.dedent("""\
                    # distutils: language = c++
                    from widget cimport Widget

                    def make_widget(w: int, h: int):
                        cdef Widget* obj = new Widget(w, h)
                        cdef int a = obj.area()
                        del obj
                        return a
                """)
                )
            res = subprocess.run(
                [sys.executable, "-m", "cython", "-3", "--cplus", "-I", ".", "widget_wrap.pyx"],
                capture_output=True,
                text=True,
            )
            assert res.returncode == 0, f"Cython failed on C++ pxd:\n{res.stderr}"

    def test_quickstart_python_api_example(self, tmp_path) -> None:
        """Test the Python API snippet from docs/getting-started/quickstart.md."""
        from headerkit.backends import get_backend
        from headerkit.writers.cython import write_pxd

        code = textwrap.dedent("""\
            typedef struct {
                int x;
                int y;
            } Point;
            Point create_point(int x, int y);
        """)
        backend = get_backend("libclang")
        header = backend.parse(code, "example.h")
        pxd = write_pxd(header)

        assert 'cdef extern from "example.h":' in pxd
        assert "Point create_point(int x, int y)" in pxd

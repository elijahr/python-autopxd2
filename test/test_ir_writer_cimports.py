"""Tests for PxdWriter cimport generation."""

from autopxd.ir import CType, Function, Header, Parameter, Pointer


class TestCimportGeneration:
    """Tests for automatic cimport statement generation."""

    def test_stdint_types_generate_cimport(self):
        """Using stdint types generates libc.stdint cimport."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="test",
                    return_type=CType(name="uint32_t"),
                    parameters=[Parameter(name="x", type=CType(name="int64_t"))],
                )
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        assert "from libc.stdint cimport" in output
        assert "uint32_t" in output
        assert "int64_t" in output

    def test_stdio_types_generate_cimport(self):
        """Using FILE type generates libc.stdio cimport."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="test",
                    return_type=CType(name="void"),
                    parameters=[Parameter(name="f", type=Pointer(pointee=CType(name="FILE")))],
                )
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        assert "from libc.stdio cimport FILE" in output

    def test_multiple_cimport_groups(self):
        """Multiple module cimports are grouped correctly."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="test",
                    return_type=CType(name="uint32_t"),
                    parameters=[Parameter(name="f", type=Pointer(pointee=CType(name="FILE")))],
                )
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        # Both cimports should be present
        assert "from libc.stdint cimport" in output
        assert "from libc.stdio cimport" in output

    def test_va_list_generates_stub_cimport(self):
        """Using va_list generates autopxd.stubs.stdarg cimport."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="vprintf_wrapper",
                    return_type=CType(name="void"),
                    parameters=[Parameter(name="args", type=CType(name="va_list"))],
                )
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        assert "from autopxd.stubs.stdarg cimport va_list" in output
        # Should NOT have the old inline declaration
        assert "ctypedef struct va_list:" not in output

    def test_cimports_before_extern(self):
        """Cimport statements appear before extern from block."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="test",
                    return_type=CType(name="uint32_t"),
                    parameters=[],
                )
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        cimport_pos = output.find("from libc.stdint cimport")
        extern_pos = output.find('cdef extern from "test.h"')

        assert cimport_pos < extern_pos, "cimport should precede extern from"

    def test_no_duplicate_cimports(self):
        """Same type used multiple times generates single cimport."""
        header = Header(
            path="test.h",
            declarations=[
                Function(
                    name="func1",
                    return_type=CType(name="uint32_t"),
                    parameters=[],
                ),
                Function(
                    name="func2",
                    return_type=CType(name="uint32_t"),
                    parameters=[Parameter(name="x", type=CType(name="uint32_t"))],
                ),
            ],
        )
        from autopxd.ir_writer import PxdWriter

        writer = PxdWriter(header)
        output = writer.write()

        # uint32_t should appear only once in cimport
        cimport_line = [line for line in output.split("\n") if "from libc.stdint cimport" in line][0]
        assert cimport_line.count("uint32_t") == 1

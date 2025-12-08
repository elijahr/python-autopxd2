"""Type conversion tests that run on both backends."""

from autopxd.ir import (
    Array,
    CType,
    Pointer,
)


class TestPointerTypes:
    """Test pointer type parsing."""

    def test_pointer_type(self, backend):
        code = "int* ptr;"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, CType)

    def test_double_pointer(self, backend):
        code = "char** argv;"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        assert isinstance(var.type.pointee, Pointer)

    def test_const_pointer(self, backend):
        code = "const char* str;"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Pointer)
        pointee = var.type.pointee
        assert isinstance(pointee, CType)


class TestArrayTypes:
    """Test array type parsing."""

    def test_array_fixed_size(self, backend):
        code = "int arr[10];"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10

    def test_array_of_pointers(self, backend):
        code = "char* argv[10];"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert isinstance(var.type, Array)
        assert var.type.size == 10
        assert isinstance(var.type.element_type, Pointer)


class TestQualifiedTypes:
    """Test type qualifier parsing."""

    def test_unsigned_types(self, backend):
        code = "unsigned long count;"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        # Both backends may handle this differently
        type_str = var.type.name if hasattr(var.type, "name") else str(var.type)
        assert "unsigned" in type_str or "unsigned" in getattr(var.type, "qualifiers", [])

    def test_long_long(self, backend):
        code = "long long value;"
        header = backend.parse(code, "test.h")
        var = header.declarations[0]
        assert "long long" in var.type.name

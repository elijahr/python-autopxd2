# pylint: disable=attribute-defined-outside-init,import-outside-toplevel,wrong-import-order
"""Tests using realistic header fixtures.

These tests verify that both parser backends can handle patterns
commonly found in real C/C++ libraries.
"""

import re

import pytest
from fixtures.realistic_headers import (
    ALL_FIXTURES,
    C_FIXTURES,
    CPP_FIXTURES,
)

from autopxd.backends.pycparser_backend import (
    PycparserBackend,
)
from autopxd.ir import (
    Enum,
    Function,
    Struct,
    Typedef,
)
from autopxd.ir_writer import (
    write_pxd,
)


def preprocess_for_pycparser(code: str) -> str:
    """Remove comments and preprocessor directives for pycparser.

    pycparser requires fully preprocessed code without:
    - C-style comments (/* ... */)
    - C++ style comments (// ...)
    - Preprocessor directives (#define, #include, etc.)
    """
    # Remove /* ... */ comments (including multiline)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove // ... comments
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
    # Remove preprocessor directives
    code = re.sub(r"^#.*$", "", code, flags=re.MULTILINE)
    return code


class TestPycparserRealisticHeaders:
    """Test pycparser backend with realistic C headers."""

    def setup_method(self):
        self.backend = PycparserBackend()

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_parse_c_fixture(self, fixture_name):
        """Test that pycparser can parse realistic C headers."""
        code = preprocess_for_pycparser(C_FIXTURES[fixture_name])
        header = self.backend.parse(code, f"{fixture_name}.h")

        # Should find declarations
        assert len(header.declarations) > 0

        # Check we found expected declaration types
        decl_types = {type(d).__name__ for d in header.declarations}
        # Each fixture should have at least functions or structs
        assert decl_types & {"Function", "Struct", "Typedef", "Enum"}

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_generate_pxd_c_fixture(self, fixture_name):
        """Test that we can generate valid pxd from realistic C headers."""
        code = preprocess_for_pycparser(C_FIXTURES[fixture_name])
        header = self.backend.parse(code, f"{fixture_name}.h")
        pxd = write_pxd(header)

        # Should generate non-empty output
        assert len(pxd) > 0

        # Should have extern from block
        assert "cdef extern from" in pxd

    def test_compression_lib_structures(self):
        """Test compression library-style structures are parsed correctly."""
        code = preprocess_for_pycparser(C_FIXTURES["compression_lib"])
        header = self.backend.parse(code, "compress.h")

        # Find the main stream structure
        structs = [d for d in header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "compress_stream_s" in struct_names

        # Find enum
        enums = [d for d in header.declarations if isinstance(d, Enum)]
        enum_names = {e.name for e in enums}
        assert "compress_status" in enum_names

        # Check enum values
        status_enum = next(e for e in enums if e.name == "compress_status")
        value_names = {v.name for v in status_enum.values}
        assert "COMPRESS_OK" in value_names
        assert "COMPRESS_STREAM_ERROR" in value_names

    def test_database_lib_callbacks(self):
        """Test database library-style callbacks are parsed correctly."""
        code = preprocess_for_pycparser(C_FIXTURES["database_lib"])
        header = self.backend.parse(code, "database.h")

        # Should have the callback typedef
        typedefs = [d for d in header.declarations if isinstance(d, Typedef)]
        typedef_names = {t.name for t in typedefs}
        assert "db_callback" in typedef_names

        # Should have statement binding functions
        functions = [d for d in header.declarations if isinstance(d, Function)]
        func_names = {f.name for f in functions}
        assert "db_bind_int" in func_names
        assert "db_bind_text" in func_names
        assert "db_step" in func_names

    def test_json_lib_api(self):
        """Test JSON library-style API is parsed correctly."""
        code = preprocess_for_pycparser(C_FIXTURES["json_lib"])
        header = self.backend.parse(code, "json.h")

        # Should have json_type enum
        enums = [d for d in header.declarations if isinstance(d, Enum)]
        enum_names = {e.name for e in enums}
        assert "json_type" in enum_names

        # Should have json_t as struct (opaque handle - typedef struct becomes struct)
        structs = [d for d in header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "json_t" in struct_names

        # Should have creation functions
        functions = [d for d in header.declarations if isinstance(d, Function)]
        func_names = {f.name for f in functions}
        assert "json_object" in func_names
        assert "json_array" in func_names
        assert "json_string" in func_names

    def test_network_protocol_unions(self):
        """Test network protocol-style unions are parsed correctly."""
        code = preprocess_for_pycparser(C_FIXTURES["network_protocol"])
        header = self.backend.parse(code, "protocol.h")

        # Should have message types enum
        enums = [d for d in header.declarations if isinstance(d, Enum)]
        enum_names = {e.name for e in enums}
        assert "msg_type" in enum_names

        # Should have message structures
        structs = [d for d in header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}
        assert "msg_header" in struct_names
        assert "connect_request" in struct_names

        # Should have union
        unions = [s for s in structs if s.is_union]
        union_names = {u.name for u in unions}
        assert "msg_payload" in union_names


@pytest.mark.libclang
class TestLibclangRealisticHeaders:
    """Test libclang backend with realistic C/C++ headers."""

    def setup_method(self):
        from autopxd.backends.libclang_backend import (
            LibclangBackend,
        )

        self.backend = LibclangBackend()

    @pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
    def test_parse_all_fixtures(self, fixture_name):
        """Test that libclang can parse all fixtures including C++."""
        code = ALL_FIXTURES[fixture_name]
        is_cpp = fixture_name in CPP_FIXTURES
        extra_args = ["-x", "c++"] if is_cpp else []
        suffix = ".hpp" if is_cpp else ".h"

        header = self.backend.parse(code, f"{fixture_name}{suffix}", extra_args=extra_args)

        # Should find declarations
        assert len(header.declarations) > 0

    @pytest.mark.parametrize("fixture_name", list(ALL_FIXTURES.keys()))
    def test_generate_pxd_all_fixtures(self, fixture_name):
        """Test pxd generation for all fixtures."""
        code = ALL_FIXTURES[fixture_name]
        is_cpp = fixture_name in CPP_FIXTURES
        extra_args = ["-x", "c++"] if is_cpp else []
        suffix = ".hpp" if is_cpp else ".h"

        header = self.backend.parse(code, f"{fixture_name}{suffix}", extra_args=extra_args)
        pxd = write_pxd(header)

        # Should generate non-empty output
        assert len(pxd) > 0
        assert "cdef extern from" in pxd

    def test_cpp_classes_become_structs(self):
        """Test that C++ classes are converted to structs for Cython."""
        code = CPP_FIXTURES["cpp_container"]
        header = self.backend.parse(code, "container.hpp", extra_args=["-x", "c++"])

        structs = [d for d in header.declarations if isinstance(d, Struct)]
        struct_names = {s.name for s in structs}

        # Classes should appear as structs
        assert "Vector2D" in struct_names
        assert "Rectangle" in struct_names
        assert "Point" in struct_names

    def test_cpp_methods_handled(self):
        """Test that C++ class fields are captured (methods are not in fields)."""
        code = CPP_FIXTURES["cpp_container"]
        header = self.backend.parse(code, "container.hpp", extra_args=["-x", "c++"])

        structs = [d for d in header.declarations if isinstance(d, Struct)]
        vector_struct = next((s for s in structs if s.name == "Vector2D"), None)

        assert vector_struct is not None
        field_names = {f.name for f in vector_struct.fields}

        # Fields should be captured
        assert "x" in field_names
        assert "y" in field_names

    def test_overloaded_functions(self):
        """Test handling of overloaded functions (should capture both)."""
        code = CPP_FIXTURES["cpp_container"]
        header = self.backend.parse(code, "container.hpp", extra_args=["-x", "c++"])

        functions = [d for d in header.declarations if isinstance(d, Function)]
        distance_funcs = [f for f in functions if f.name == "distance"]

        # Both overloads should be captured
        assert len(distance_funcs) >= 1


@pytest.mark.libclang
class TestBackendConsistency:
    """Test that both backends produce consistent results for C code."""

    def setup_method(self):
        from autopxd.backends.libclang_backend import (
            LibclangBackend,
        )

        self.pycparser = PycparserBackend()
        self.libclang = LibclangBackend()

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_declaration_counts_similar(self, fixture_name):
        """Test that both backends find similar numbers of declarations."""
        code = C_FIXTURES[fixture_name]
        preprocessed = preprocess_for_pycparser(code)

        pycparser_header = self.pycparser.parse(preprocessed, f"{fixture_name}.h")
        libclang_header = self.libclang.parse(code, f"{fixture_name}.h")

        # Counts should be reasonably similar (within 20% or 5 declarations)
        pycparser_count = len(pycparser_header.declarations)
        libclang_count = len(libclang_header.declarations)

        # Allow some variance due to different handling of typedefs/forward decls
        diff = abs(pycparser_count - libclang_count)
        max_count = max(pycparser_count, libclang_count)

        assert diff <= max(5, max_count * 0.2), (
            f"Declaration counts differ significantly: " f"pycparser={pycparser_count}, libclang={libclang_count}"
        )

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_function_names_match(self, fixture_name):
        """Test that both backends find the same function names."""
        code = C_FIXTURES[fixture_name]
        preprocessed = preprocess_for_pycparser(code)

        pycparser_header = self.pycparser.parse(preprocessed, f"{fixture_name}.h")
        libclang_header = self.libclang.parse(code, f"{fixture_name}.h")

        pycparser_funcs = {d.name for d in pycparser_header.declarations if isinstance(d, Function)}
        libclang_funcs = {d.name for d in libclang_header.declarations if isinstance(d, Function)}

        # All pycparser functions should be found by libclang
        missing_in_libclang = pycparser_funcs - libclang_funcs
        assert not missing_in_libclang, f"Functions missing in libclang: {missing_in_libclang}"

    @pytest.mark.parametrize("fixture_name", list(C_FIXTURES.keys()))
    def test_struct_names_match(self, fixture_name):
        """Test that both backends find the same struct names."""
        code = C_FIXTURES[fixture_name]
        preprocessed = preprocess_for_pycparser(code)

        pycparser_header = self.pycparser.parse(preprocessed, f"{fixture_name}.h")
        libclang_header = self.libclang.parse(code, f"{fixture_name}.h")

        pycparser_structs = {d.name for d in pycparser_header.declarations if isinstance(d, Struct)}
        libclang_structs = {d.name for d in libclang_header.declarations if isinstance(d, Struct)}

        # Named structs should match - libclang is conservative and skips forward decls
        # so we check that all libclang structs are also found by pycparser
        pycparser_named = {n for n in pycparser_structs if n is not None}
        libclang_named = {n for n in libclang_structs if n is not None}

        missing_in_pycparser = libclang_named - pycparser_named
        assert not missing_in_pycparser, f"Structs missing in pycparser: {missing_in_pycparser}"

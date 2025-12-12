"""Test that types from included headers are properly resolved."""

import pytest

from autopxd import translate
from test.cython_utils import validate_cython_compiles

pytestmark = pytest.mark.libclang


class TestDependencyResolution:
    """Test that types from included files are properly handled."""

    def test_typedef_from_include(self, tmp_path):
        """Types defined in included headers should be inlined."""
        # Create helper header with typedef
        helper_h = tmp_path / "helper.h"
        helper_h.write_text("typedef void* voidpf;\n")

        # Create main header that uses the type
        main_h = tmp_path / "main.h"
        main_h.write_text('#include "helper.h"\nvoidpf get_ptr(void);\n')

        # Generate pxd - should include the typedef
        with open(main_h) as f:
            code = f.read()
        pxd = translate(code, str(main_h), backend="libclang")

        # Verify it compiles (voidpf must be defined)
        validate_cython_compiles(pxd, tmp_path)

        # Verify typedef is present
        assert "ctypedef void* voidpf" in pxd

    def test_typedef_chain_from_include(self, tmp_path):
        """Chained typedefs from included headers should be resolved."""
        # Create helper header with typedef chain
        helper_h = tmp_path / "helper.h"
        helper_h.write_text("typedef unsigned long uLong;\n" "typedef unsigned int uInt;\n")

        # Create main header that uses these types
        main_h = tmp_path / "main.h"
        main_h.write_text('#include "helper.h"\n' "uLong checksum(uInt value);\n")

        # Generate pxd
        with open(main_h) as f:
            code = f.read()
        pxd = translate(code, str(main_h), backend="libclang")

        # Verify it compiles
        validate_cython_compiles(pxd, tmp_path)

        # Verify both typedefs are present
        assert "ctypedef unsigned long uLong" in pxd
        assert "ctypedef unsigned int uInt" in pxd

    def test_struct_typedef_from_include(self, tmp_path):
        """Struct typedefs from included headers should be resolved."""
        # Create helper header with struct typedef
        helper_h = tmp_path / "helper.h"
        helper_h.write_text(
            "typedef struct stream_s {\n" "    void* next_in;\n" "    unsigned int avail_in;\n" "} stream_t;\n"
        )

        # Create main header that uses the typedef
        main_h = tmp_path / "main.h"
        main_h.write_text('#include "helper.h"\n' "int process(stream_t* s);\n")

        # Generate pxd
        with open(main_h) as f:
            code = f.read()
        pxd = translate(code, str(main_h), backend="libclang")

        # Verify it compiles
        validate_cython_compiles(pxd, tmp_path)

        # Verify struct and typedef are present
        assert "stream_s" in pxd or "stream_t" in pxd

    def test_unused_typedef_not_included(self, tmp_path):
        """Types not used in main file should not be included."""
        # Create helper header with multiple typedefs
        helper_h = tmp_path / "helper.h"
        helper_h.write_text(
            "typedef void* voidpf;\n"
            "typedef void* voidpc;\n"  # Not used
            "typedef int unused_int;\n"  # Not used
        )

        # Create main header that uses only voidpf
        main_h = tmp_path / "main.h"
        main_h.write_text('#include "helper.h"\n' "voidpf get_ptr(void);\n")

        # Generate pxd
        with open(main_h) as f:
            code = f.read()
        pxd = translate(code, str(main_h), backend="libclang")

        # voidpf should be present (it's used)
        assert "voidpf" in pxd

        # unused_int should NOT be present
        assert "unused_int" not in pxd

    def test_deeply_nested_typedef(self, tmp_path):
        """Typedefs from deeply nested includes should be resolved."""
        # Create a chain: main.h -> level1.h -> level2.h -> types.h
        types_h = tmp_path / "types.h"
        types_h.write_text("typedef unsigned long size_type;\n")

        level2_h = tmp_path / "level2.h"
        level2_h.write_text('#include "types.h"\n')

        level1_h = tmp_path / "level1.h"
        level1_h.write_text('#include "level2.h"\n')

        main_h = tmp_path / "main.h"
        main_h.write_text('#include "level1.h"\n' "size_type get_size(void);\n")

        # Generate pxd
        with open(main_h) as f:
            code = f.read()
        pxd = translate(code, str(main_h), backend="libclang")

        # Verify it compiles
        validate_cython_compiles(pxd, tmp_path)

        # Verify typedef is present
        assert "ctypedef unsigned long size_type" in pxd

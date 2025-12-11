# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""libclang-based parser backend.

This backend uses libclang (LLVM's C/C++ parser) to parse header files.
It provides full C/C++ support including templates, namespaces, and classes.

Requirements
------------
* System libclang library must be installed
* Python clang2 bindings version must match system libclang version
  (e.g., ``clang2==18.*`` for LLVM 18)

If system libclang is not available, autopxd2 automatically falls back
to the pycparser backend (C99 only).

Advantages over pycparser
-------------------------
* Full C++ support (classes, templates, namespaces)
* Handles complex preprocessor constructs
* Uses the same parser as production compilers
* Better error messages with source locations

Limitations
-----------
* Macro extraction is limited due to Python bindings constraints
* Requires system libclang installation

Example
-------
::

    from autopxd.backends.libclang_backend import LibclangBackend

    backend = LibclangBackend()
    header = backend.parse(code, "myheader.hpp", extra_args=["-std=c++17"])
"""

import clang.cindex
from clang.cindex import (
    CursorKind,
    TypeKind,
)

from autopxd.backends import (
    register_backend,
)
from autopxd.ir import (
    Array,
    CType,
    Declaration,
    Enum,
    EnumValue,
    Field,
    Function,
    FunctionPointer,
    Header,
    Parameter,
    Pointer,
    SourceLocation,
    Struct,
    Typedef,
    TypeExpr,
    Variable,
)


def is_system_libclang_available() -> bool:
    """Check if the system libclang library is available.

    The Python clang2 package is always installed, but it requires the
    system libclang shared library (libclang.so/dylib) to function.
    This checks if that library can be loaded.

    :returns: True if system libclang is available and can be used.
    """
    try:
        # Attempt to load the library - this is the definitive test
        clang.cindex.Config().get_cindex_library()
        return True
    except clang.cindex.LibclangError:
        return False


class ClangASTConverter:
    """Converts libclang cursors to autopxd IR.

    This class walks a libclang translation unit and produces the
    equivalent autopxd IR declarations. It handles C and C++ constructs
    including structs, unions, enums, typedefs, functions, classes, and variables.

    :param filename: Source filename for filtering declarations.
        Only declarations from this file are included (system headers excluded).

    Note
    ----
    This class is internal to the libclang backend. Use
    :class:`LibclangBackend` for the public API.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.declarations: list[Declaration] = []
        # Track seen declarations to avoid duplicates
        self._seen: dict[str, bool] = {}
        # Current namespace context (for nested namespace support)
        self._namespace_stack: list[str] = []

    @property
    def _current_namespace(self) -> str | None:
        """Get current namespace as '::'-joined string, or None if global."""
        return "::".join(self._namespace_stack) if self._namespace_stack else None

    def convert(self, tu: "clang.cindex.TranslationUnit") -> Header:
        """Convert a libclang TranslationUnit to our IR Header."""
        self._process_children(tu.cursor)
        return Header(path=self.filename, declarations=self.declarations)

    def _process_children(self, cursor: "clang.cindex.Cursor") -> None:
        """Process all children of a cursor."""
        for child in cursor.get_children():
            # Only process declarations from the target file
            if not self._is_from_target_file(child):
                continue
            self._process_cursor(child)

    def _is_from_target_file(self, cursor: "clang.cindex.Cursor") -> bool:
        """Check if cursor is from the target file."""
        loc = cursor.location
        if loc.file is None:
            return False
        return bool(loc.file.name == self.filename)

    def _process_cursor(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a top-level cursor."""
        kind = cursor.kind

        if kind == CursorKind.STRUCT_DECL:
            self._process_struct(cursor, is_union=False)
        elif kind == CursorKind.UNION_DECL:
            self._process_struct(cursor, is_union=True)
        elif kind == CursorKind.ENUM_DECL:
            self._process_enum(cursor)
        elif kind == CursorKind.FUNCTION_DECL:
            self._process_function(cursor)
        elif kind == CursorKind.TYPEDEF_DECL:
            self._process_typedef(cursor)
        elif kind == CursorKind.VAR_DECL:
            self._process_variable(cursor)
        elif kind == CursorKind.CLASS_DECL:
            # C++ class - uses cppclass in Cython
            self._process_struct(cursor, is_union=False, is_cppclass=True)
        elif kind == CursorKind.NAMESPACE:
            # C++ namespace - recurse into it with namespace context
            self._process_namespace(cursor)

    def _process_namespace(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a C++ namespace declaration."""
        ns_name = cursor.spelling
        if ns_name:
            self._namespace_stack.append(ns_name)
            self._process_children(cursor)
            self._namespace_stack.pop()

    def _process_struct(self, cursor: "clang.cindex.Cursor", is_union: bool, is_cppclass: bool = False) -> None:
        """Process a struct/union/class declaration."""
        name = cursor.spelling or None

        # Skip forward declarations
        if not cursor.is_definition():
            return

        # Determine the key prefix for deduplication
        if is_cppclass:
            key_prefix = "class"
        elif is_union:
            key_prefix = "union"
        else:
            key_prefix = "struct"

        # Skip if already processed
        key = f"{key_prefix}:{name}"
        if name and key in self._seen:
            return
        if name:
            self._seen[key] = True

        fields: list[Field] = []
        methods: list[Function] = []
        for child in cursor.get_children():
            if child.kind == CursorKind.FIELD_DECL:
                field = self._convert_field(child)
                if field:
                    fields.append(field)
            elif child.kind == CursorKind.CXX_METHOD and is_cppclass:
                method = self._convert_method(child)
                if method:
                    methods.append(method)

        struct = Struct(
            name=name,
            fields=fields,
            methods=methods,
            is_union=is_union,
            is_cppclass=is_cppclass,
            namespace=self._current_namespace,
            location=self._get_location(cursor),
        )
        self.declarations.append(struct)

    def _process_enum(self, cursor: "clang.cindex.Cursor") -> None:
        """Process an enum declaration."""
        name = cursor.spelling or None

        # Skip forward declarations
        if not cursor.is_definition():
            return

        # Skip if already processed
        key = f"enum:{name}"
        if name and key in self._seen:
            return
        if name:
            self._seen[key] = True

        values: list[EnumValue] = []
        for child in cursor.get_children():
            if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                values.append(EnumValue(name=child.spelling, value=child.enum_value))

        enum = Enum(name=name, values=values, location=self._get_location(cursor))
        self.declarations.append(enum)

    def _process_function(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a function declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"function:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        return_type = self._convert_type(cursor.result_type)
        if not return_type:
            return

        parameters: list[Parameter] = []
        is_variadic = cursor.type.is_function_variadic()

        for arg in cursor.get_arguments():
            param_type = self._convert_type(arg.type)
            if param_type:
                # Skip void parameter
                if isinstance(param_type, CType) and param_type.name == "void":
                    continue
                parameters.append(Parameter(name=arg.spelling or None, type=param_type))

        func = Function(
            name=name,
            return_type=return_type,
            parameters=parameters,
            is_variadic=is_variadic,
            namespace=self._current_namespace,
            location=self._get_location(cursor),
        )
        self.declarations.append(func)

    def _convert_method(self, cursor: "clang.cindex.Cursor") -> Function | None:
        """Convert a C++ method to a Function IR node."""
        name = cursor.spelling
        if not name:
            return None

        return_type = self._convert_type(cursor.result_type)
        if not return_type:
            return None

        parameters: list[Parameter] = []
        is_variadic = cursor.type.is_function_variadic()

        for arg in cursor.get_arguments():
            param_type = self._convert_type(arg.type)
            if param_type:
                # Skip void parameter
                if isinstance(param_type, CType) and param_type.name == "void":
                    continue
                parameters.append(Parameter(name=arg.spelling or None, type=param_type))

        return Function(
            name=name,
            return_type=return_type,
            parameters=parameters,
            is_variadic=is_variadic,
            location=self._get_location(cursor),
        )

    def _process_typedef(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a typedef declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"typedef:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        underlying = cursor.underlying_typedef_type
        underlying_type = self._convert_type(underlying)
        if not underlying_type:
            return

        typedef = Typedef(
            name=name,
            underlying_type=underlying_type,
            location=self._get_location(cursor),
        )
        self.declarations.append(typedef)

    def _process_variable(self, cursor: "clang.cindex.Cursor") -> None:
        """Process a variable declaration."""
        name = cursor.spelling
        if not name:
            return

        # Skip if already processed
        key = f"var:{name}"
        if key in self._seen:
            return
        self._seen[key] = True

        var_type = self._convert_type(cursor.type)
        if not var_type:
            return

        var = Variable(name=name, type=var_type, location=self._get_location(cursor))
        self.declarations.append(var)

    def _convert_field(self, cursor: "clang.cindex.Cursor") -> Field | None:
        """Convert a field cursor to IR Field."""
        name = cursor.spelling
        if not name:
            return None

        field_type = self._convert_type(cursor.type)
        if not field_type:
            return None

        return Field(name=name, type=field_type)

    # pylint: disable=too-many-return-statements
    def _convert_type(self, clang_type: "clang.cindex.Type") -> TypeExpr | None:
        """Convert a libclang Type to our IR type expression."""
        # Get canonical type for consistency
        kind = clang_type.kind

        # Handle pointer types
        if kind == TypeKind.POINTER:
            pointee = clang_type.get_pointee()

            # Check for function pointer
            if pointee.kind == TypeKind.FUNCTIONPROTO:
                func_ptr = self._convert_function_type(pointee)
                if func_ptr:
                    return Pointer(pointee=func_ptr)
                return None

            pointee_type = self._convert_type(pointee)
            if pointee_type:
                return Pointer(pointee=pointee_type)
            return None

        # Handle array types
        if kind in (TypeKind.CONSTANTARRAY, TypeKind.INCOMPLETEARRAY, TypeKind.VARIABLEARRAY):
            element_type = self._convert_type(clang_type.element_type)
            if not element_type:
                return None

            size: int | str | None = None
            if kind == TypeKind.CONSTANTARRAY:
                size = clang_type.element_count
            # INCOMPLETEARRAY has no size (flexible array)
            # VARIABLEARRAY size is runtime-determined

            return Array(element_type=element_type, size=size)

        # Handle function types (for function pointer types)
        if kind == TypeKind.FUNCTIONPROTO:
            return self._convert_function_type(clang_type)

        # Handle elaborated types (struct X, enum Y, etc.)
        if kind == TypeKind.ELABORATED:
            # Get the underlying named type
            named_type = clang_type.get_named_type()
            return self._convert_type(named_type)

        # Handle record (struct/union) types
        if kind == TypeKind.RECORD:
            decl = clang_type.get_declaration()
            name = decl.spelling
            if decl.kind == CursorKind.UNION_DECL:
                return CType(name=f"union {name}" if name else "union")
            return CType(name=f"struct {name}" if name else "struct")

        # Handle enum types
        if kind == TypeKind.ENUM:
            decl = clang_type.get_declaration()
            name = decl.spelling
            return CType(name=f"enum {name}" if name else "enum")

        # Handle typedef types
        if kind == TypeKind.TYPEDEF:
            decl = clang_type.get_declaration()
            return CType(name=decl.spelling)

        # Handle basic types
        spelling = clang_type.spelling

        # Extract qualifiers
        qualifiers: list[str] = []
        if clang_type.is_const_qualified():
            qualifiers.append("const")
        if clang_type.is_volatile_qualified():
            qualifiers.append("volatile")

        # Clean up the spelling to get base type
        base_type = spelling
        for qual in qualifiers:
            base_type = base_type.replace(qual, "").strip()

        return CType(name=base_type, qualifiers=qualifiers)

    def _convert_function_type(self, clang_type: "clang.cindex.Type") -> FunctionPointer | None:
        """Convert a function type to FunctionPointer."""
        result_type = self._convert_type(clang_type.get_result())
        if not result_type:
            return None

        parameters: list[Parameter] = []
        is_variadic = clang_type.is_function_variadic()

        for arg_type in clang_type.argument_types():
            param_type = self._convert_type(arg_type)
            if param_type:
                # Function pointer params don't have names
                parameters.append(Parameter(name=None, type=param_type))

        return FunctionPointer(
            return_type=result_type,
            parameters=parameters,
            is_variadic=is_variadic,
        )

    def _get_location(self, cursor: "clang.cindex.Cursor") -> SourceLocation | None:
        """Get source location from a cursor."""
        loc = cursor.location
        if loc.file:
            return SourceLocation(file=loc.file.name, line=loc.line, column=loc.column)
        return None


class LibclangBackend:
    """Parser backend using libclang.

    Uses LLVM's libclang to parse C and C++ code. This backend supports
    the full C++ language including templates, classes, and namespaces.

    Properties
    ----------
    name : str
        Returns ``"libclang"``.
    supports_macros : bool
        Returns ``False`` - macro extraction is limited in Python bindings.
    supports_cpp : bool
        Returns ``True`` - full C++ support.

    Example
    -------
    ::

        from autopxd.backends.libclang_backend import LibclangBackend

        backend = LibclangBackend()

        # Parse C++ code with specific standard
        header = backend.parse(
            code,
            "myheader.hpp",
            extra_args=["-std=c++17", "-DDEBUG=1"]
        )
    """

    def __init__(self) -> None:
        self._index: clang.cindex.Index | None = None

    @property
    def name(self) -> str:
        return "libclang"

    @property
    def supports_macros(self) -> bool:
        # Limited macro support due to Python bindings
        return False

    @property
    def supports_cpp(self) -> bool:
        return True

    def _get_index(self) -> "clang.cindex.Index":
        """Get or create the clang index."""
        if self._index is None:
            self._index = clang.cindex.Index.create()
        return self._index

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: list[str] | None = None,
        extra_args: list[str] | None = None,
    ) -> Header:
        """Parse C/C++ code using libclang.

        Unlike the pycparser backend, this method handles raw (unpreprocessed)
        code and performs preprocessing internally.

        :param code: C/C++ source code to parse (raw, not preprocessed).
        :param filename: Source filename for error messages and location tracking.
        :param include_dirs: Additional include directories (converted to ``-I`` flags).
        :param extra_args: Additional compiler arguments (e.g., ``["-std=c++17"]``).
        :returns: :class:`~autopxd.ir.Header` containing parsed declarations.
        :raises RuntimeError: If parsing fails with errors.

        Example
        -------
        ::

            header = backend.parse(
                code,
                "myheader.hpp",
                include_dirs=["/usr/local/include"],
                extra_args=["-std=c++17", "-DNDEBUG"]
            )
        """
        args: list[str] = []

        # Add include directories
        if include_dirs:
            for inc_dir in include_dirs:
                args.append(f"-I{inc_dir}")

        # Add extra arguments
        if extra_args:
            args.extend(extra_args)

        # Parse the code
        index = self._get_index()
        tu = index.parse(filename, args=args, unsaved_files=[(filename, code)])

        # Check for fatal errors
        for diag in tu.diagnostics:
            if diag.severity >= clang.cindex.Diagnostic.Error:
                raise RuntimeError(f"Parse error: {diag.spelling}")

        # Collect included headers
        included_headers: set[str] = set()
        for inclusion in tu.get_includes():
            # inclusion.include is a File with name attribute
            header_path = str(inclusion.include.name)
            # Store full path - caller can extract basename if needed
            included_headers.add(header_path)

        # Convert to IR
        converter = ClangASTConverter(filename)
        header = converter.convert(tu)

        # Attach included headers to the IR
        header.included_headers = included_headers

        return header


# Only register this backend if system libclang is available
# If not available, autopxd2 falls back to pycparser automatically
if is_system_libclang_available():
    register_backend("libclang", LibclangBackend)

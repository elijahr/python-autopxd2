# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""libclang-based parser backend.

This backend uses libclang (LLVM's C/C++ parser) to parse header files.
It provides full C/C++ support and can extract #define macro values.

Requirements:
- libclang must be installed (e.g., via `pip install libclang` or system package)
- On some systems, you may need to set LIBCLANG_PATH environment variable

Advantages over pycparser:
- Full C++ support
- Handles complex preprocessor constructs
- Uses the same parser as actual compilers
- Better error messages

Limitations:
- Macro extraction is limited due to Python bindings constraints
"""

from typing import (
    Dict,
    List,
    Optional,
    Union,
)

# Try to import clang - this may fail if not installed
try:
    import clang.cindex
    from clang.cindex import (
        CursorKind,
        TypeKind,
    )

    CLANG_AVAILABLE = True
except ImportError:
    CLANG_AVAILABLE = False
    CursorKind = None  # type: ignore
    TypeKind = None  # type: ignore

from autopxd.ir import (
    Array,
    CType,
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

if CLANG_AVAILABLE:
    from autopxd.backends import (
        register_backend,
    )

    class ClangASTConverter:
        """Converts libclang cursors to autopxd IR."""

        def __init__(self, filename: str) -> None:
            self.filename = filename
            self.declarations: List[Union[Enum, Struct, Function, Typedef, Variable]] = []
            # Track seen declarations to avoid duplicates
            self._seen: Dict[str, bool] = {}

        def convert(self, tu: "clang.cindex.TranslationUnit") -> Header:
            """Convert a libclang TranslationUnit to our IR Header."""
            for cursor in tu.cursor.get_children():
                # Only process declarations from the target file
                if not self._is_from_target_file(cursor):
                    continue
                self._process_cursor(cursor)
            return Header(path=self.filename, declarations=self.declarations)

        def _is_from_target_file(self, cursor: "clang.cindex.Cursor") -> bool:
            """Check if cursor is from the target file."""
            loc = cursor.location
            if loc.file is None:
                return False
            return loc.file.name == self.filename

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
                # C++ class - treat as struct for now
                self._process_struct(cursor, is_union=False)

        def _process_struct(self, cursor: "clang.cindex.Cursor", is_union: bool) -> None:
            """Process a struct/union declaration."""
            name = cursor.spelling or None

            # Skip forward declarations
            if not cursor.is_definition():
                return

            # Skip if already processed
            key = f"{'union' if is_union else 'struct'}:{name}"
            if name and key in self._seen:
                return
            if name:
                self._seen[key] = True

            fields: List[Field] = []
            for child in cursor.get_children():
                if child.kind == CursorKind.FIELD_DECL:
                    field = self._convert_field(child)
                    if field:
                        fields.append(field)

            struct = Struct(
                name=name,
                fields=fields,
                is_union=is_union,
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

            values: List[EnumValue] = []
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

            parameters: List[Parameter] = []
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
                location=self._get_location(cursor),
            )
            self.declarations.append(func)

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

        def _convert_field(self, cursor: "clang.cindex.Cursor") -> Optional[Field]:
            """Convert a field cursor to IR Field."""
            name = cursor.spelling
            if not name:
                return None

            field_type = self._convert_type(cursor.type)
            if not field_type:
                return None

            return Field(name=name, type=field_type)

        # pylint: disable=too-many-return-statements
        def _convert_type(self, clang_type: "clang.cindex.Type") -> Optional[TypeExpr]:
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

                size: Optional[Union[int, str]] = None
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
            qualifiers: List[str] = []
            if clang_type.is_const_qualified():
                qualifiers.append("const")
            if clang_type.is_volatile_qualified():
                qualifiers.append("volatile")

            # Clean up the spelling to get base type
            base_type = spelling
            for qual in qualifiers:
                base_type = base_type.replace(qual, "").strip()

            return CType(name=base_type, qualifiers=qualifiers)

        def _convert_function_type(self, clang_type: "clang.cindex.Type") -> Optional[FunctionPointer]:
            """Convert a function type to FunctionPointer."""
            result_type = self._convert_type(clang_type.get_result())
            if not result_type:
                return None

            parameters: List[Parameter] = []
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

        def _get_location(self, cursor: "clang.cindex.Cursor") -> Optional[SourceLocation]:
            """Get source location from a cursor."""
            loc = cursor.location
            if loc.file:
                return SourceLocation(file=loc.file.name, line=loc.line, column=loc.column)
            return None

    class LibclangBackend:
        """Parser backend using libclang."""

        def __init__(self) -> None:
            self._index: Optional["clang.cindex.Index"] = None

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
            include_dirs: Optional[List[str]] = None,
            extra_args: Optional[List[str]] = None,
        ) -> Header:
            """Parse C/C++ code using libclang.

            Args:
                code: C/C++ source code to parse
                filename: Source filename for error messages
                include_dirs: Additional include directories
                extra_args: Additional compiler arguments

            Returns:
                Header containing parsed declarations
            """
            args: List[str] = []

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

            # Convert to IR
            converter = ClangASTConverter(filename)
            return converter.convert(tu)

    # Register this backend (not as default since it requires external dependency)
    register_backend("libclang", LibclangBackend)

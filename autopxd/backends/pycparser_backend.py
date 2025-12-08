# pylint: disable=cyclic-import
# Cyclic import is intentional - backends register themselves when loaded
"""pycparser-based parser backend.

This backend uses pycparser (pure Python C99 parser) to parse C header files.
It's the default backend since it requires no external dependencies beyond
the pycparser package itself.

Limitations
-----------
* C99 only - no C++ support (use libclang for C++)
* Cannot extract ``#define`` macro values (processed by preprocessor)
* Requires preprocessed input (run through ``cpp``, ``clang -E``, or ``cl.exe /E``)

Example
-------
::

    from autopxd.backends.pycparser_backend import PycparserBackend

    backend = PycparserBackend()
    header = backend.parse(preprocessed_code, "myheader.h")
"""

from pycparser import (
    c_ast,
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


class ASTConverter(c_ast.NodeVisitor):  # type: ignore[misc]
    """Converts pycparser AST to autopxd IR.

    This class walks a pycparser AST and produces the equivalent
    autopxd IR declarations. It handles all C99 constructs including
    structs, unions, enums, typedefs, functions, and variables.

    :param filename: Source filename for source location tracking.

    Note
    ----
    This class is internal to the pycparser backend. Use
    :class:`PycparserBackend` for the public API.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.declarations: list[Declaration] = []
        # Track enum values for use in array dimensions
        self.constants: dict[str, str] = {}
        # Track path through AST for naming anonymous types
        self.path: list[str] = []
        # Counter for generating unique anonymous type names
        self.anon_counter = 0

    def convert(self, ast: c_ast.FileAST) -> Header:
        """Convert a pycparser AST to our IR Header."""
        for decl in ast.ext:
            self._visit_top_level(decl)
        return Header(path=self.filename, declarations=self.declarations)

    def _visit_top_level(self, node: c_ast.Node) -> None:
        """Process a top-level declaration."""
        if isinstance(node, c_ast.Decl):
            self._handle_decl(node)
        elif isinstance(node, c_ast.Typedef):
            self._handle_typedef(node)
        elif isinstance(node, c_ast.FuncDef):
            # Function definition - extract just the declaration
            self._handle_decl(node.decl)

    def _handle_decl(self, node: c_ast.Decl) -> None:
        """Handle a declaration (variable or function)."""
        if node.name is None:
            # Anonymous declaration, likely just a struct/enum definition
            if isinstance(node.type, c_ast.Struct):
                self._handle_struct_definition(node.type)
            elif isinstance(node.type, c_ast.Union):
                self._handle_struct_definition(node.type, is_union=True)
            elif isinstance(node.type, c_ast.Enum):
                self._handle_enum_definition(node.type)
            return

        if isinstance(node.type, c_ast.FuncDecl):
            # Function declaration
            func = self._convert_function_decl(node.type, node.name)
            if func:
                self.declarations.append(func)
        else:
            # Variable declaration
            type_expr = self._convert_type(node.type)
            if type_expr:
                loc = self._get_location(node)
                self.declarations.append(Variable(name=node.name, type=type_expr, location=loc))

    def _handle_typedef(self, node: c_ast.Typedef) -> None:
        """Handle a typedef declaration."""
        name = node.name

        # Check if this is a typedef for a struct/union/enum
        if isinstance(node.type, c_ast.TypeDecl):
            inner = node.type.type
            if isinstance(inner, c_ast.Struct):
                struct = self._convert_struct(inner, is_union=False)
                if struct:
                    # If struct has same name as typedef, it's "typedef struct X X"
                    # If struct is anonymous, give it the typedef name
                    if struct.name is None:
                        struct.name = name
                    self.declarations.append(struct)
                    if struct.name != name:
                        # Also add the typedef
                        self.declarations.append(
                            Typedef(
                                name=name,
                                underlying_type=CType(f"struct {struct.name}"),
                                location=self._get_location(node),
                            )
                        )
                return
            if isinstance(inner, c_ast.Union):
                struct = self._convert_struct(inner, is_union=True)
                if struct:
                    if struct.name is None:
                        struct.name = name
                    self.declarations.append(struct)
                    if struct.name != name:
                        self.declarations.append(
                            Typedef(
                                name=name,
                                underlying_type=CType(f"union {struct.name}"),
                                location=self._get_location(node),
                            )
                        )
                return
            if isinstance(inner, c_ast.Enum):
                enum = self._convert_enum(inner)
                if enum:
                    if enum.name is None:
                        enum.name = name
                    self.declarations.append(enum)
                    if enum.name != name:
                        self.declarations.append(
                            Typedef(
                                name=name,
                                underlying_type=CType(f"enum {enum.name}"),
                                location=self._get_location(node),
                            )
                        )
                return

        # Regular typedef
        type_expr = self._convert_type(node.type)
        if type_expr:
            self.declarations.append(
                Typedef(
                    name=name,
                    underlying_type=type_expr,
                    location=self._get_location(node),
                )
            )

    def _handle_struct_definition(self, node: c_ast.Struct, is_union: bool = False) -> None:
        """Handle a standalone struct/union definition."""
        struct = self._convert_struct(node, is_union)
        if struct and (struct.name or struct.fields):
            self.declarations.append(struct)

    def _handle_enum_definition(self, node: c_ast.Enum) -> None:
        """Handle a standalone enum definition."""
        enum = self._convert_enum(node)
        if enum:
            self.declarations.append(enum)

    def _convert_type(self, node: c_ast.Node) -> TypeExpr | None:
        """Convert a type node to our IR type expression."""
        if isinstance(node, c_ast.TypeDecl):
            return self._convert_type_decl(node)
        if isinstance(node, c_ast.PtrDecl):
            return self._convert_ptr_decl(node)
        if isinstance(node, c_ast.ArrayDecl):
            return self._convert_array_decl(node)
        if isinstance(node, c_ast.FuncDecl):
            return self._convert_func_ptr(node)
        return None

    def _convert_type_decl(self, node: c_ast.TypeDecl) -> TypeExpr | None:
        """Convert a TypeDecl to a type expression."""
        inner = node.type
        qualifiers = list(node.quals) if node.quals else []

        if isinstance(inner, c_ast.IdentifierType):
            type_name = " ".join(inner.names)
            return CType(name=type_name, qualifiers=qualifiers)
        if isinstance(inner, c_ast.Struct):
            name = inner.name or self._generate_anon_name("struct")
            return CType(name=f"struct {name}", qualifiers=qualifiers)
        if isinstance(inner, c_ast.Union):
            name = inner.name or self._generate_anon_name("union")
            return CType(name=f"union {name}", qualifiers=qualifiers)
        if isinstance(inner, c_ast.Enum):
            name = inner.name or self._generate_anon_name("enum")
            return CType(name=f"enum {name}", qualifiers=qualifiers)

        return None

    def _convert_ptr_decl(self, node: c_ast.PtrDecl) -> Pointer | None:
        """Convert a PtrDecl to a Pointer type."""
        qualifiers = list(node.quals) if node.quals else []

        # Check if this is a function pointer
        if isinstance(node.type, c_ast.FuncDecl):
            func_ptr = self._convert_func_ptr(node.type)
            if func_ptr:
                return Pointer(pointee=func_ptr, qualifiers=qualifiers)
            return None

        pointee = self._convert_type(node.type)
        if pointee:
            return Pointer(pointee=pointee, qualifiers=qualifiers)
        return None

    def _convert_array_decl(self, node: c_ast.ArrayDecl) -> Array | None:
        """Convert an ArrayDecl to an Array type."""
        element_type = self._convert_type(node.type)
        if not element_type:
            return None

        size: int | str | None = None
        if node.dim is not None:
            size = self._eval_dimension(node.dim)

        return Array(element_type=element_type, size=size)

    def _convert_func_ptr(self, node: c_ast.FuncDecl) -> FunctionPointer | None:
        """Convert a FuncDecl (in pointer context) to FunctionPointer."""
        # Get return type
        return_type = self._convert_type(node.type)
        if not return_type:
            return None

        # Get parameters
        params, is_variadic = self._convert_params(node.args)

        return FunctionPointer(
            return_type=return_type,
            parameters=params,
            is_variadic=is_variadic,
        )

    def _convert_function_decl(self, node: c_ast.FuncDecl, name: str) -> Function | None:
        """Convert a function declaration to our IR Function."""
        # Get return type
        return_type = self._convert_type(node.type)
        if not return_type:
            return None

        # Get parameters
        params, is_variadic = self._convert_params(node.args)

        return Function(
            name=name,
            return_type=return_type,
            parameters=params,
            is_variadic=is_variadic,
        )

    def _convert_params(self, param_list: c_ast.ParamList | None) -> tuple[list[Parameter], bool]:
        """Convert a parameter list to IR Parameters."""
        params: list[Parameter] = []
        is_variadic = False

        if param_list is None:
            return params, is_variadic

        for param in param_list.params:
            if isinstance(param, c_ast.EllipsisParam):
                is_variadic = True
                continue

            if isinstance(param, c_ast.Decl):
                param_type = self._convert_type(param.type)
                if param_type:
                    # Skip void parameters (single void means no params)
                    if isinstance(param_type, CType) and param_type.name == "void" and param.name is None:
                        continue
                    params.append(Parameter(name=param.name, type=param_type))

            elif isinstance(param, c_ast.Typename):
                # Typename is used for anonymous parameters (e.g., in typedefs)
                param_type = self._convert_type(param.type)
                if param_type:
                    # Skip void parameters
                    if isinstance(param_type, CType) and param_type.name == "void":
                        continue
                    params.append(Parameter(name=param.name, type=param_type))

        return params, is_variadic

    def _convert_struct(self, node: c_ast.Struct, is_union: bool) -> Struct | None:
        """Convert a struct/union to our IR Struct."""
        name = node.name
        fields: list[Field] = []

        if node.decls:
            for decl in node.decls:
                if isinstance(decl, c_ast.Decl):
                    # Handle inline anonymous struct/union
                    if decl.name is None and isinstance(decl.type, c_ast.Struct | c_ast.Union):
                        # Flatten anonymous nested struct/union fields
                        nested_fields = self._flatten_anonymous_struct(decl.type)
                        fields.extend(nested_fields)
                    else:
                        field = self._convert_field(decl)
                        if field:
                            fields.append(field)

        return Struct(
            name=name,
            fields=fields,
            is_union=is_union,
            location=self._get_location(node),
        )

    def _flatten_anonymous_struct(self, node: c_ast.Struct | c_ast.Union, prefix: str = "") -> list[Field]:
        """Flatten an anonymous struct/union into a list of fields."""
        # pylint: disable=too-many-nested-blocks
        fields: list[Field] = []

        if node.decls:
            for decl in node.decls:
                if isinstance(decl, c_ast.Decl):
                    if decl.name is None and isinstance(decl.type, c_ast.Struct | c_ast.Union):
                        # Recursively flatten
                        nested = self._flatten_anonymous_struct(decl.type, prefix)
                        fields.extend(nested)
                    else:
                        field = self._convert_field(decl)
                        if field:
                            if prefix:
                                field = Field(name=prefix + field.name, type=field.type)
                            fields.append(field)

        return fields

    def _convert_field(self, decl: c_ast.Decl) -> Field | None:
        """Convert a struct/union field declaration."""
        if decl.name is None:
            return None

        type_expr = self._convert_type(decl.type)
        if type_expr:
            return Field(name=decl.name, type=type_expr)
        return None

    def _convert_enum(self, node: c_ast.Enum) -> Enum | None:
        """Convert an enum to our IR Enum."""
        name = node.name
        values: list[EnumValue] = []

        if node.values:
            last_value: int | None = None
            last_expr: str | None = None
            offset_from_expr = 0

            for enumerator in node.values.enumerators:
                enum_name = enumerator.name

                if enumerator.value:
                    value_str, value_int = self._eval_enum_value(enumerator.value)
                    last_expr = value_str
                    last_value = value_int
                    offset_from_expr = 0
                else:
                    # Auto-increment
                    if last_value is not None:
                        last_value += 1
                        value_str = str(last_value)
                    elif last_expr is not None:
                        offset_from_expr += 1
                        value_str = f"({last_expr}) + {offset_from_expr}"
                    else:
                        last_value = 0
                        value_str = "0"

                # Record this constant for array dimension references
                self.constants[enum_name] = value_str

                # Store the value (as int if known, else as string expression)
                if last_value is not None and offset_from_expr == 0:
                    values.append(EnumValue(name=enum_name, value=last_value))
                else:
                    values.append(EnumValue(name=enum_name, value=value_str))

        return Enum(name=name, values=values, location=self._get_location(node))

    def _eval_enum_value(self, node: c_ast.Node) -> tuple[str, int | None]:
        """Evaluate an enum value expression.

        Returns (string_representation, optional_int_value).
        """
        if isinstance(node, c_ast.Constant):
            return self._eval_constant(node)
        if isinstance(node, c_ast.BinaryOp):
            return self._eval_binary_op(node)
        if isinstance(node, c_ast.UnaryOp):
            return self._eval_unary_op(node)
        if isinstance(node, c_ast.ID):
            # Reference to another constant
            name = node.name
            if name in self.constants:
                return self.constants[name], None
            return name, None

        # Unknown expression type
        return "0", 0

    def _eval_constant(self, node: c_ast.Constant) -> tuple[str, int | None]:
        """Evaluate a constant node."""
        if node.type in ("int", "long int"):
            raw = node.value
            # Handle octal
            if raw.startswith("0") and len(raw) > 1 and raw[1] in "0123456789":
                value_str = "0o" + raw[1:]
            else:
                value_str = raw

            # Remove type suffixes
            clean = value_str.rstrip("lLuU")
            try:
                value_int = int(clean, base=0)
                return value_str, value_int
            except ValueError:
                return value_str, None

        if node.type == "char":
            if len(node.value) == 3 and node.value[0] == "'" and node.value[-1] == "'":
                char = node.value[1]
                value_int = ord(char)
                return f"0x{value_int:X}", value_int

        return node.value, None

    def _eval_binary_op(self, node: c_ast.BinaryOp) -> tuple[str, int | None]:
        """Evaluate a binary operation."""
        left_str, left_int = self._eval_enum_value(node.left)
        right_str, right_int = self._eval_enum_value(node.right)

        # Wrap sub-expressions in parens if needed
        if self._needs_parens(node.left, node.op):
            left_str = f"({left_str})"
        if self._needs_parens(node.right, node.op):
            right_str = f"({right_str})"

        expr = f"{left_str} {node.op} {right_str}"

        # Try to compute the value if both sides are known
        if left_int is not None and right_int is not None:
            try:
                result = self._compute_binary(left_int, node.op, right_int)
                return expr, result
            except (ValueError, ZeroDivisionError):
                pass

        return expr, None

    def _eval_unary_op(self, node: c_ast.UnaryOp) -> tuple[str, int | None]:
        """Evaluate a unary operation."""
        operand_str, operand_int = self._eval_enum_value(node.expr)

        if node.op == "-":
            if operand_int is not None:
                return f"-{operand_str}", -operand_int
            return f"-({operand_str})", None
        if node.op == "~":
            if operand_int is not None:
                return f"~{operand_str}", ~operand_int
            return f"~({operand_str})", None

        return operand_str, operand_int

    def _needs_parens(self, node: c_ast.Node, parent_op: str) -> bool:
        """Check if a sub-expression needs parentheses."""
        if isinstance(node, c_ast.Constant):
            return False
        if isinstance(node, c_ast.ID):
            return True  # Constants might be expressions
        if isinstance(node, c_ast.BinaryOp):
            # Parens not needed for chains of the same associative op
            return not (parent_op == "+" and node.op == "+")
        return True

    def _compute_binary(self, left: int, op: str, right: int) -> int:
        """Compute a binary operation on integers."""
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left // right
        if op == "%":
            return left % right
        if op == "<<":
            return left << right
        if op == ">>":
            return left >> right
        if op == "&":
            return left & right
        if op == "|":
            return left | right
        if op == "^":
            return left ^ right
        raise ValueError(f"Unknown operator: {op}")

    # pylint: disable-next=too-many-return-statements
    def _eval_dimension(self, node: c_ast.Node) -> int | str | None:
        """Evaluate an array dimension expression."""
        if isinstance(node, c_ast.Constant):
            _, value = self._eval_constant(node)
            if value is not None:
                return value
            return str(node.value)
        if isinstance(node, c_ast.ID):
            name: str = node.name
            if name in self.constants:
                # Return the expression (may be int or string)
                const_val = self.constants[name]
                try:
                    return int(const_val)
                except ValueError:
                    return const_val
            return name
        if isinstance(node, c_ast.BinaryOp):
            expr, value = self._eval_binary_op(node)
            if value is not None:
                return value
            return expr

        return None

    def _generate_anon_name(self, kind: str) -> str:
        """Generate a unique name for an anonymous type."""
        self.anon_counter += 1
        return f"_anon_{kind}_{self.anon_counter}"

    def _get_location(self, node: c_ast.Node) -> SourceLocation | None:
        """Get source location from a node."""
        if hasattr(node, "coord") and node.coord:
            return SourceLocation(
                file=node.coord.file or self.filename,
                line=node.coord.line,
                column=node.coord.column,
            )
        return None


class PycparserBackend:
    """Parser backend using pycparser.

    The default autopxd parser backend, using the pure-Python pycparser
    library. This backend has no external dependencies but requires
    preprocessed C code as input.

    Properties
    ----------
    name : str
        Returns ``"pycparser"``.
    supports_macros : bool
        Returns ``False`` - macros are consumed by the preprocessor.
    supports_cpp : bool
        Returns ``False`` - pycparser only supports C99.

    Example
    -------
    ::

        from autopxd.backends.pycparser_backend import PycparserBackend

        backend = PycparserBackend()

        # Parse preprocessed code
        preprocessed = run_cpp("myheader.h")
        header = backend.parse(preprocessed, "myheader.h")

        for decl in header.declarations:
            print(decl)
    """

    @property
    def name(self) -> str:
        return "pycparser"

    @property
    def supports_macros(self) -> bool:
        return False

    @property
    def supports_cpp(self) -> bool:
        return False

    def parse(
        self,
        code: str,
        filename: str,
        include_dirs: list[str] | None = None,  # pylint: disable=unused-argument
        extra_args: list[str] | None = None,  # pylint: disable=unused-argument
    ) -> Header:
        """Parse C code using pycparser.

        .. note::

            This method expects **preprocessed** code. Run the C preprocessor
            (``cpp``, ``clang -E``, or ``cl.exe /E``) before calling this method.

        :param code: Preprocessed C source code to parse.
        :param filename: Source filename for error messages and location tracking.
        :param include_dirs: Not used (preprocessing done by caller).
        :param extra_args: Not used (preprocessing done by caller).
        :returns: :class:`~autopxd.ir.Header` containing parsed declarations.
        :raises pycparser.plyparser.ParseError: If the code has syntax errors.
        """
        # pylint: disable=import-outside-toplevel
        from pycparser import (
            c_parser,
        )

        parser = c_parser.CParser()
        ast = parser.parse(code, filename=filename)

        converter = ASTConverter(filename)
        return converter.convert(ast)


# Register this backend as the default
register_backend("pycparser", PycparserBackend, is_default=True)

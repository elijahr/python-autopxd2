import pycparser
from pycparser import (
    c_ast,
)

from .declarations import (
    STDINT_DECLARATIONS,
)
from .keywords import (
    keywords,
)
from .nodes import (
    Array,
    Block,
    Enum,
    Function,
    IdentifierType,
    Ptr,
    PxdNode,
    Type,
)


def escape(name, include_C_name=False):
    """Avoid name collisions with Python keywords by appending an underscore.

    if include_C_name=True, additionally append the orginal name in
    quotes, e.g.:     global -> global_ "global"
    """
    if name is not None and name in keywords:
        if include_C_name:
            name = f'{name}_ "{name}"'
        else:
            name = name + "_"
    return name


def parse_enum_value(node, constants):
    if isinstance(node, c_ast.Constant):
        if node.type in ("int", "long int"):
            c_raw = node.value
            # Convert octal to Python syntax
            if c_raw[0] == "0" and len(c_raw) > 1 and c_raw[1] in "0123456789":
                value_as_str = "0o" + c_raw[1:]
            else:
                value_as_str = c_raw

            # Remove type suffixes
            if value_as_str[-1] in "lLuU":
                value_as_int = int(value_as_str[:-1], base=0)
            else:
                value_as_int = int(value_as_str, base=0)

        elif node.type == "char":
            if len(node.value) != 3 or node.value[0] != "'" or node.value[-1] != "'":
                raise ValueError(f"Invalid char constant format: {node.value!r}")

            value_as_int = ord(node.value[1])
            value_as_str = f"0x{value_as_int:X}"

        else:
            raise ValueError(f"Unsupported constant type for enum value: {node}")

    elif isinstance(node, c_ast.BinaryOp):
        # We wrap the left and right sub-expression with parenthesis to avoid
        # error when doing advanced arithmetic.
        # For instance, let's consider the following:
        # - C input code: `((1 << 2) + 3) * 4` (= 28)
        # - pycparser: BinaryOp(BinaryOp(BinaryOp(1, "<<", 2), "+", 3), "*", 4)
        # - output if we wouldn't add parenthesis: 1 << 2 + 3 * 4 (= 16384)
        #
        # Note we treat differently the case of a binary expression only composed of
        # additions in order to improve readability on this very common case (e.g.
        # `((1 + 2) + 3) + 4` -> `1 + 2 + 3 + 4`).

        def need_parenthesis(sub_node):
            if isinstance(sub_node, c_ast.Constant):
                # A scalar never need parenthesis !
                return False

            if isinstance(sub_node, c_ast.ID):
                # The ID may correspond to an expression, so we must enclose it in parenthesis
                return True

            # Parenthesis are superfluous if parent and child are both addition expressions
            if not isinstance(sub_node, c_ast.BinaryOp):
                raise ValueError(f"Unexpected node type in enum expression: {type(sub_node).__name__}")
            return node.op != "+" or sub_node.op != "+"

        left_value_as_str, _ = parse_enum_value(node.left, constants)
        if need_parenthesis(node.left):
            left_value_as_str = f"({left_value_as_str})"
        right_value_as_str, _ = parse_enum_value(node.right, constants)
        if need_parenthesis(node.right):
            right_value_as_str = f"({right_value_as_str})"
        value_as_str = f"{left_value_as_str} {node.op} {right_value_as_str}"
        value_as_int = None

    elif isinstance(node, c_ast.ID):
        try:
            value_as_str = constants[node.name]
        except KeyError as exc:
            raise ValueError(f"Enum value references an unknown constant: {node.name}") from exc
        value_as_int = None

    else:
        raise ValueError(f"Unsupported expression for enum value: {node}")

    return value_as_str, value_as_int


class AutoPxd(c_ast.NodeVisitor, PxdNode):
    def __init__(self, hdrname):
        self.hdrname = hdrname
        self.decl_stack = [[]]
        self.visit_stack = []
        self.stdint_declarations = []
        self.dimension_stack = []
        self.constants = {}

    def visit(self, node):
        self.visit_stack.append(node)
        rv = super().visit(node)
        n = self.visit_stack.pop()
        if n != node:
            raise RuntimeError(f"Visit stack mismatch: expected {node}, got {n}")
        return rv

    def visit_IdentifierType(self, node):
        for name in node.names:
            if name in STDINT_DECLARATIONS and name not in self.stdint_declarations:
                self.stdint_declarations.append(name)
        self.append(" ".join(escape(name) for name in node.names))

    def visit_Block(self, node, kind):
        type_decl = self.child_of(c_ast.TypeDecl, -2)
        type_def = type_decl and self.child_of(c_ast.Typedef, -3)
        name = node.name
        if not name:
            if type_def:
                name = self.path_name()
            elif type_decl:
                name = self.path_name(kind[0])
            else:
                # Will be flattened and inlined somewhere else
                return

        if not node.decls and type_decl:
            # not a definition, must be a reference
            self.append(name if node.name is None else escape(name))
            return

        def recursive_flatten_collect(node, prefix=""):
            if node.decls is None:
                return []

            fields = [n for n in self.collect(node) if not hasattr(n, "name") or n.name != ""]
            for n in fields:
                if hasattr(n, "name") and prefix != "":
                    n.name = prefix + n.name
                    n.name = f'{n.name.split("[")[0]} "{n.name.replace("__", ".")}"'

            for n in node.decls:
                if n.name is None and isinstance(n.type, (pycparser.c_ast.Struct, pycparser.c_ast.Union)):
                    fields.extend(recursive_flatten_collect(n.type, prefix=prefix))
            return fields

        fields = recursive_flatten_collect(node)

        # add the struct/union definition to the top level
        if type_def and node.name is None:
            self.decl_stack[0].append(Block(name, fields, kind, "ctypedef"))
        else:
            self.decl_stack[0].append(Block(escape(name, True), fields, kind, "cdef"))
            if type_decl:
                # inline struct/union, add a reference to whatever name it was
                # defined on the top level
                self.append(escape(name))

    def visit_Enum(self, node):
        items = []
        if node.values:
            maybe_last_value_as_str = None
            maybe_last_value_as_int = None
            index_since_last_str_value = 0
            for item in node.values.enumerators:
                items.append(escape(item.name, True))
                if item.value:
                    value_as_str, maybe_value_as_int = parse_enum_value(item.value, self.constants)
                    index_since_last_str_value = 0
                    maybe_last_value_as_str = value_as_str
                    maybe_last_value_as_int = maybe_value_as_int
                else:
                    if maybe_last_value_as_int is not None:
                        maybe_last_value_as_int += 1
                        value_as_str = str(maybe_last_value_as_int)
                    elif maybe_last_value_as_str is not None:
                        index_since_last_str_value += 1
                        # Given we don't know what `maybe_last_value_as_str` contains, we
                        # must enclose it in parenthesis to avoid messing with operator
                        # priority.
                        # e.g. `A + 1` if A is `2 << 3`: `2 << 3 + 1` != `(2 << 3) + 1`
                        value_as_str = f"({maybe_last_value_as_str}) + {index_since_last_str_value}"
                    else:
                        maybe_last_value_as_int = 0
                        maybe_last_value_as_str = None
                        value_as_str = "0"
                # These constants may be used as array indices:
                self.constants[item.name] = value_as_str
        type_decl = self.child_of(c_ast.TypeDecl, -2)
        type_def = type_decl and self.child_of(c_ast.Typedef, -3)
        name = node.name
        if not name:
            if type_def:
                name = self.path_name()
            elif type_decl:
                name = self.path_name("e")
        # add the enum definition to the top level
        if node.name is None and type_def and items:
            self.decl_stack[0].append(Enum(escape(name, True), items, "ctypedef"))
        else:
            if items:
                escname = name if node.name is None else escape(name, True)
                self.decl_stack[0].append(Enum(escname, items, "cpdef"))
            if type_decl:
                escname = name if node.name is None else escape(name)
                self.append(escname)

    def visit_Struct(self, node):
        return self.visit_Block(node, "struct")

    def visit_Union(self, node):
        return self.visit_Block(node, "union")

    def visit_TypeDecl(self, node):
        decls = self.collect(node)
        if not decls:
            return
        if len(decls) != 1:
            raise RuntimeError(f"Expected 1 declaration in TypeDecl, got {len(decls)}")
        # Cython supports const and volatile C type qualifiers
        for qual in ("const", "volatile"):
            if qual in node.quals:
                decls[0] = f"{qual} {decls[0]}"
        if isinstance(decls[0], str):
            include_C_name = not self.child_of(c_ast.ParamList)
            self.append(IdentifierType(escape(node.declname, include_C_name), decls[0]))
        else:
            self.append(decls[0])

    def visit_Decl(self, node):
        decls = self.collect(node)
        if not decls:
            return
        if len(decls) != 1:
            raise RuntimeError(f"Expected 1 declaration in Decl, got {len(decls)}")
        if isinstance(decls[0], str):
            include_C_name = not self.child_of(c_ast.ParamList)
            self.append(IdentifierType(escape(node.name, include_C_name), decls[0]))
        else:
            self.append(decls[0])

    def visit_FuncDecl(self, node):
        decls = self.collect(node)
        return_type = decls[-1].type_name
        fname = decls[-1].name
        args = decls[:-1]
        if len(args) == 1 and isinstance(args[0], IdentifierType) and args[0].type_name == "void":
            args = []
        if self.child_of(c_ast.PtrDecl, -2) and not self.child_of(c_ast.Typedef, -3):
            # declaring a variable or parameter
            name = self.path_name("ft")
            self.decl_stack[0].append(Type(Ptr(Function(return_type, name, args))))
            self.append(name)
        else:
            self.append(Function(return_type, fname, args))

    def visit_PtrDecl(self, node):
        decls = self.collect(node)
        if len(decls) != 1:
            raise RuntimeError(f"Expected 1 declaration in PtrDecl, got {len(decls)}")
        if isinstance(decls[0], str):
            # Cython supports const and volatile C type qualifiers
            for qual in ("const", "volatile"):
                if qual in node.quals:
                    decls[0] = f"{qual} {decls[0]}"
            self.append(decls[0])
        else:
            self.append(Ptr(decls[0], node.quals))

    def visit_ArrayDecl(self, node):
        dim = ""
        if hasattr(node, "dim"):
            if hasattr(node.dim, "value"):
                dim = node.dim.value
            elif hasattr(node.dim, "name") and node.dim.name in self.constants:
                dim = str(self.constants[node.dim.name])
        self.dimension_stack.append(dim)
        decls = self.collect(node)
        if len(decls) != 1:
            raise RuntimeError(f"Expected 1 declaration in ArrayDecl, got {len(decls)}")
        self.append(Array(decls[0], self.dimension_stack))
        self.dimension_stack = []

    def visit_Typedef(self, node):
        decls = self.collect(node)
        if len(decls) != 1:
            return
        names = str(decls[0]).split()
        if names[0] != names[1]:
            self.decl_stack[0].append(Type(decls[0]))

    def visit_Compound(self, node):
        # Do not recurse into the body of inline function definitions
        pass

    def visit_StaticAssert(self, node):
        # Just ignore asserts for now. Otherwise we get invalid output.
        pass

    def collect(self, node):
        decls = []
        self.decl_stack.append(decls)
        self.generic_visit(node)
        popped = self.decl_stack.pop()
        if popped != decls:
            raise RuntimeError("Declaration stack mismatch in collect()")
        return decls

    def path_name(self, tag=None):
        names = []
        for node in self.visit_stack[:-2]:
            if hasattr(node, "declname") and node.declname:
                names.append(node.declname)
            elif hasattr(node, "name") and node.name:
                names.append(node.name)
        if tag is None:
            return "_".join(names)
        name = "_".join(names)
        return f"_{name}_{tag}"

    def child_of(self, node_type, index=None):
        if index is None:
            return any(isinstance(node, node_type) for node in reversed(self.visit_stack))
        return isinstance(self.visit_stack[index], node_type)

    def append(self, node):
        self.decl_stack[-1].append(node)

    def lines(self):
        rv = [f'cdef extern from "{self.hdrname}":', ""]
        for decl in self.decl_stack[0]:
            for line in decl.lines():
                rv.append(self.indent + line)
            rv.append("")
        if len(rv) == 2:
            rv[1] = self.indent + "pass"
            rv.append("")
        return rv

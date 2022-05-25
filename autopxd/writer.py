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
            name = '{name}_ "{name}"'.format(name=name)
        else:
            name = name + "_"
    return name


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
        assert n == node
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
            value = "0"
            for item in node.values.enumerators:
                items.append(escape(item.name, True))
                if item.value is not None and hasattr(item.value, "value"):
                    # Store the integer literal as a string to preserve its base:
                    value = item.value.value
                    # convert octal to Python syntax:
                    if value[0] == "0" and len(value) > 1 and value[1] in "0123456789":
                        value = "0o" + value[1:]
                else:
                    # Convert to Python integer if necessary and add one:
                    if isinstance(value, str):
                        # Remove type suffixes
                        for suffix in "lLuU":
                            value = value.replace(suffix, "")
                    value = str(int(value, base=0) + 1)
                # These constants may be used as array indices:
                self.constants[item.name] = value
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
        assert len(decls) == 1
        if isinstance(decls[0], str):
            include_C_name = not self.child_of(c_ast.ParamList)
            self.append(IdentifierType(escape(node.declname, include_C_name), decls[0]))
        else:
            self.append(decls[0])

    def visit_Decl(self, node):
        decls = self.collect(node)
        if not decls:
            return
        assert len(decls) == 1
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
        assert len(decls) == 1
        if isinstance(decls[0], str):
            self.append(decls[0])
        else:
            self.append(Ptr(decls[0]))

    def visit_ArrayDecl(self, node):
        dim = ""
        if hasattr(node, "dim"):
            if hasattr(node.dim, "value"):
                dim = node.dim.value
            elif hasattr(node.dim, "name") and node.dim.name in self.constants:
                dim = str(self.constants[node.dim.name])
        self.dimension_stack.append(dim)
        decls = self.collect(node)
        assert len(decls) == 1
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
        assert self.decl_stack.pop() == decls
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
            for node in reversed(self.visit_stack):
                if isinstance(node, node_type):
                    return True
            return False
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

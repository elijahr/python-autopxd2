import six
from pycparser import c_ast

from .declarations import STDINT_DECLARATIONS
from .nodes import PxdNode, Block, Enum, IdentifierType
from .nodes import Type, Ptr, Function, Array


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
        rv = super(AutoPxd, self).visit(node)
        n = self.visit_stack.pop()
        assert n == node
        return rv

    def visit_IdentifierType(self, node):
        for name in node.names:
            if name in STDINT_DECLARATIONS and name not in self.stdint_declarations:
                self.stdint_declarations.append(name)
        self.append(' '.join(node.names))

    def visit_Block(self, node, kind):
        type_decl = self.child_of(c_ast.TypeDecl, -2)
        type_def = type_decl and self.child_of(c_ast.Typedef, -3)
        name = node.name
        if not name:
            if type_def:
                name = self.path_name()
            else:
                name = self.path_name(kind[0])
        if not node.decls:
            if self.child_of(c_ast.TypeDecl, -2):
                # not a definition, must be a reference
                self.append(name)
            return
        fields = self.collect(node)
        # add the struct/union definition to the top level
        if type_def and node.name is None:
            self.decl_stack[0].append(Block(name, fields, kind, 'ctypedef'))
        else:
            self.decl_stack[0].append(Block(name, fields, kind, 'cdef'))
            if type_decl:
                # inline struct/union, add a reference to whatever name it was
                # defined on the top level
                self.append(name)

    def visit_Enum(self, node):
        items = []
        if node.values:
            value = 0
            for item in node.values.enumerators:
                items.append(item.name)
                if item.value is not None and hasattr(item.value, 'value'):
                    value = int(item.value.value)
                else:
                    value += 1
                self.constants[item.name] = value
        type_decl = self.child_of(c_ast.TypeDecl, -2)
        type_def = type_decl and self.child_of(c_ast.Typedef, -3)
        name = node.name
        if not name:
            if type_def:
                name = self.path_name()
            elif type_def:
                name = self.path_name('e')
        # add the enum definition to the top level
        if node.name is None and type_def and len(items):
            self.decl_stack[0].append(Enum(name, items, 'ctypedef'))
        else:
            if len(items):
                self.decl_stack[0].append(Enum(name, items, 'cdef'))
            if type_decl:
                self.append(name)

    def visit_Struct(self, node):
        return self.visit_Block(node, 'struct')

    def visit_Union(self, node):
        return self.visit_Block(node, 'union')

    def visit_TypeDecl(self, node):
        decls = self.collect(node)
        if not decls:
            return
        assert len(decls) == 1
        if isinstance(decls[0], six.string_types):
            self.append(IdentifierType(node.declname, decls[0]))
        else:
            self.append(decls[0])

    def visit_Decl(self, node):
        decls = self.collect(node)
        if not decls:
            return
        assert len(decls) == 1
        if isinstance(decls[0], six.string_types):
            self.append(IdentifierType(node.name, decls[0]))
        else:
            self.append(decls[0])

    def visit_FuncDecl(self, node):
        decls = self.collect(node)
        return_type = decls[-1].type_name
        fname = decls[-1].name
        args = decls[:-1]
        if (len(args) == 1 and isinstance(args[0], IdentifierType) and
                args[0].type_name == 'void'):
            args = []
        if (self.child_of(c_ast.PtrDecl, -2) and not
                self.child_of(c_ast.Typedef, -3)):
            # declaring a variable or parameter
            name = self.path_name('ft'.format(fname))
            self.decl_stack[0].append(Type(Ptr(Function(return_type, name, args))))
            self.append(name)
        else:
            self.append(Function(return_type, fname, args))

    def visit_PtrDecl(self, node):
        decls = self.collect(node)
        assert len(decls) == 1
        if isinstance(decls[0], six.string_types):
            self.append(decls[0])
        else:
            self.append(Ptr(decls[0]))

    def visit_ArrayDecl(self, node):
        dim = ''
        if hasattr(node, 'dim'):
            if hasattr(node.dim, 'value'):
                dim = node.dim.value
            elif hasattr(node.dim, 'name') and node.dim.name in self.constants:
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

    def collect(self, node):
        decls = []
        self.decl_stack.append(decls)
        self.generic_visit(node)
        assert self.decl_stack.pop() == decls
        return decls

    def path_name(self, tag=None):
        names = []
        for node in self.visit_stack[:-2]:
            if hasattr(node, 'declname') and node.declname:
                names.append(node.declname)
            elif hasattr(node, 'name') and node.name:
                names.append(node.name)
        if tag is None:
            return '_'.join(names)
        else:
            return '_{0}_{1}'.format('_'.join(names), tag)

    def child_of(self, node_type, index=None):
        if index is None:
            for node in reversed(self.visit_stack):
                if isinstance(node, node_type):
                    return True
            return False
        else:
            return isinstance(self.visit_stack[index], node_type)

    def append(self, node):
        self.decl_stack[-1].append(node)

    def lines(self):
        rv = ['cdef extern from "{0}":'.format(self.hdrname), '']
        for decl in self.decl_stack[0]:
            for line in decl.lines():
                rv.append(self.indent + line)
            rv.append('')
        return rv

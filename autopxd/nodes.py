class PxdNode(object):
    indent = '    '

    def __str__(self):
        return '\n'.join(self.lines())


class IdentifierType(PxdNode):
    def __init__(self, name, type_name):
        self.name = name or ''
        self.type_name = type_name

    def lines(self):
        if self.name:
            return ['{0} {1}'.format(self.type_name, self.name)]
        else:
            return [self.type_name]


class Function(PxdNode):
    def __init__(self, return_type, name, args):
        self.return_type = return_type
        self.name = name
        self.args = args

    def argstr(self):
        arguments_list = []
        for arg in self.args:
            lines = arg.lines()
            assert len(lines) == 1
            arguments_list.append(lines[0])
        return ', '.join(arguments_list)

    def lines(self):
        return [
            '{0} {1}({2})'.format(self.return_type, self.name, self.argstr())
        ]


class Ptr(IdentifierType):
    def __init__(self, node):
        self.node = node

    @property
    def name(self):
        return self.node.name

    @property
    def type_name(self):
        return self.node.type_name + '*'

    def lines(self):
        if isinstance(self.node, Function):
            f = self.node
            args = f.argstr()
            return ['{0} (*{1})({2})'.format(f.return_type, f.name, args)]
        else:
            return super(Ptr, self).lines()


class Array(IdentifierType):
    def __init__(self, node, dimensions=None):
        if dimensions is None:
            dimensions = [1]
        self.node = node
        self.dimensions = dimensions

    @property
    def name(self):
        if self.dimensions:
            return self.node.name + '[' + ']['.join(
                [str(dim) for dim in self.dimensions]) + ']'
        else:
            return self.node.name

    @property
    def type_name(self):
        return self.node.type_name


class Type(PxdNode):
    def __init__(self, node):
        self.node = node

    def lines(self):
        lines = self.node.lines()
        lines[0] = 'ctypedef ' + lines[0]
        return lines


class Block(PxdNode):
    def __init__(self, name, fields, kind, statement='cdef'):
        self.name = name
        self.fields = fields
        self.kind = kind
        self.statement = statement

    def lines(self):
        rv = ['{0} {1} {2}'.format(self.statement, self.kind, self.name)]
        if self.fields:
            rv[0] += ':'
        for field in self.fields:
            for line in field.lines():
                rv.append(self.indent + line)
        return rv


class Enum(PxdNode):
    def __init__(self, name, items, statement='cdef'):
        self.name = name
        self.items = items
        self.statement = statement

    def lines(self):
        rv = []
        if self.name:
            rv.append('{0} enum {1}:'.format(self.statement, self.name))
        else:
            rv.append('cdef enum:')
        for item in self.items:
            rv.append(self.indent + item)
        return rv

from abc import (
    ABCMeta,
    abstractmethod,
)
from typing import (
    List,
    Union,
)


class PxdNode(metaclass=ABCMeta):
    indent: str = "    "

    def __str__(self):
        return "\n".join(self.lines())

    @abstractmethod
    def lines(self) -> List[str]:
        pass


class IdentifierType(PxdNode):
    __slots__ = ("name", "type_name")
    name: str
    type_name: str

    def __init__(self, name, type_name):
        self.name = name or ""
        self.type_name = type_name

    def lines(self) -> List[str]:
        if self.name:
            return [f"{self.type_name} {self.name}"]
        return [self.type_name]


class Function(PxdNode):
    __slots__ = ("return_type", "name", "args")

    return_type: str
    name: str
    args: List[PxdNode]

    def __init__(self, return_type: str, name: str, args: List[PxdNode]):
        self.return_type = return_type
        self.name = name
        self.args = args

    def argstr(self) -> str:
        arguments_list = []
        for arg in self.args:
            lines = arg.lines()
            assert len(lines) == 1
            arguments_list.append(lines[0])
        return ", ".join(arguments_list)

    def lines(self) -> List[str]:
        return [f"{self.return_type} {self.name}({self.argstr()})"]


class Ptr(IdentifierType):
    __slots__ = ("node",) + IdentifierType.__slots__

    node: PxdNode

    def __init__(self, node: IdentifierType):
        self.node = node
        if isinstance(node, Function):
            type_name = node.return_type
        else:
            type_name = self.node.type_name
        super().__init__(self.node.name, f"{type_name}*")

    def lines(self) -> List[str]:
        if isinstance(self.node, Function):
            f = self.node
            args = f.argstr()
            return [f"{f.return_type} (*{f.name})({args})"]
        return super().lines()


class Array(IdentifierType):
    __slots__ = ("node", "dimensions")

    node: PxdNode
    dimensions: List[int]

    def __init__(self, node: PxdNode, dimensions: Union[None, List[int]] = None):
        if dimensions is None:
            dimensions = [1]
        self.node = node
        self.dimensions = dimensions
        if self.dimensions:
            name = self.node.name + "[" + "][".join([str(dim) for dim in self.dimensions]) + "]"
        else:
            name = self.node.name
        super().__init__(name, self.node.type_name)


class Type(PxdNode):
    __slots__ = ("node",)

    node: PxdNode

    def __init__(self, node: PxdNode):
        self.node = node

    def lines(self) -> List[str]:
        lines = self.node.lines()
        lines[0] = "ctypedef " + lines[0]
        return lines


class Block(PxdNode):
    __slots__ = ("name", "fields", "kind", "statement")

    name: str
    fields: List[PxdNode]
    kind: str
    statement: str

    def __init__(self, name: str, fields: List[PxdNode], kind: str, statement: str = "cdef"):
        self.name = name
        self.fields = fields
        self.kind = kind
        self.statement = statement

    def lines(self) -> List[str]:
        rv = [f"{self.statement} {self.kind} {self.name}"]
        if self.fields:
            rv[0] += ":"
        for field in self.fields:
            for line in field.lines():
                rv.append(self.indent + line)
        return rv


class Enum(PxdNode):
    __slots__ = ("name", "items", "statement")

    name: str
    items: List[str]
    statement: str

    def __init__(self, name, items: List[str], statement="cdef"):
        self.name = name
        self.items = items
        self.statement = statement

    def lines(self) -> List[str]:
        rv = []
        if self.name:
            rv.append(f"{self.statement} enum {self.name}:")
        else:
            rv.append("cpdef enum:")
        for item in self.items:
            rv.append(self.indent + item)
        return rv

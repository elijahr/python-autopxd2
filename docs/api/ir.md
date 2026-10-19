# IR Module

The IR (Intermediate Representation) module provides data structures for representing C/C++ declarations in a parser-agnostic format. It is `headerkit.ir`; autopxd2 consumes it rather than defining its own.

::: headerkit.ir
    options:
      show_root_heading: true
      show_source: true
      members:
        - Header
        - CType
        - Pointer
        - Array
        - FunctionPointer
        - Field
        - Parameter
        - EnumValue
        - Enum
        - Struct
        - Function
        - Typedef
        - Variable
        - Constant
        - SourceLocation
        - ParserBackend

# Cython Binding Generators Comparison

Several tools exist to parse header files and automatically produce Cython bindings.

## Maintenance Status

| Tool | Status | Last Update (as of Dec 2025) |
|------|--------|--------------|
| [autowrap](https://github.com/uweschmitt/autowrap) | ✅ Active | v0.24.0 (2025) |
| [python-autopxd2](https://github.com/elijahr/python-autopxd2) | ✅ Active | v3.2.1 (2025) |
| [cwrap](https://github.com/geggo/cwrap) | ❌ Dead | 8163ff2 (2019) |
| [xdress](https://github.com/xdress/xdress) | ❌ Dead | eb7f0a0 (2014) |
| [cython-codegen](https://github.com/cournape/cython-codegen) | ❌ Dead | b1856d3 (2011) |
| [fwrap](https://github.com/kwmsmith/fwrap) | ❌ Dead | f2e20eb (2010) |
| [pxd-gcc-generation](https://github.com/robertwb/cython/tree/pxd-gcc-generation) | ❌ Dead | ba5c5ff (2012) |

## Automation Level

| Step | autowrap | python-autopxd2 |
|------|----------|-----------------|
| **Input required** | Hand-written .pxd | C/C++ header (unmodified) |
| Parse C/C++ header | ❌ Manual | ✅ Automatic |
| Generate .pxd declarations | ❌ Manual | ✅ Automatic |
| Generate .pyx wrappers | ✅ Automatic | ❌ Not generated |
| Generate cimport statements | ❌ Manual | ✅ Automatic |
| System include detection | ❌ Manual -I flags | ✅ Automatic |
| Recursive includes | N/A | ✅ Automatic |
| Python↔C++ type conversion | ✅ Automatic (runtime) | ❌ Not applicable |
| **Manual files to write** | .pxd + setup.py | None |

## Workflow Comparison

### python-autopxd2: Header → .pxd (fully automatic)

#### Use python-autopxd2 when:

- You want to quickly generate .pxd files from existing headers
- You don't want to write any Cython declarations by hand
- You need to wrap a large C/C++ API with minimal effort
- You want recursive processing of umbrella headers that include other headers

```bash
autopxd mylib.h mylib.pxd
```

Input: Unmodified C/C++ header
Output: C/C++ <-> Cython interface (.pxd file)
Manual work: Write Cython <-> Python interface (.pyx file)

### autowrap: Hand-written .pxd → .pyx (semi-automatic)

#### Use autowrap when:

- You need fine-grained control over Python-to-C++ type conversion
- You want automatic .pyx generation with Python special methods
- You need custom exception handling or operator overloads
- You're willing to manually write .pxd declarations with annotations

```
autowrap --out py_mylib.pyx mylib.pxd
```

Input: C/C++ <-> Cython interface (.pxd file with special comment annotations)
Output: Cython <-> Python interface (.pyx file ready to compile as an extension)
Manual work: Write C/C++ <-> Cython interface (.pxd file)

### Complementary usage:

1. Generate .pxd file with autopxd
    ```shell
    autopxd mylib.h mylib.pxd
    ```
2. [Manually annotate](https://github.com/OpenMS/autowrap/blob/master/docs/README.md) mylib.pxd for autowrap consumption
3. Generate .pyx file with autowrap
    ```shell
    autowrap --out mylib.pyx mylib.pxd
    ```
4. Integrate .pyx file into your package [build process](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#basic-setup-py)

## Language Support

| Tool               | C   | C++        | Fortran | Parser Backend             |
|--------------------|-----|------------|---------|----------------------------|
| autowrap           | ✅  | ✅         | ❌      | Cython parser (reads .pxd) |
| python-autopxd2    | ✅  | ✅         | ❌      | libclang                   |
| cwrap              | ✅  | ⚠️ Partial | ❌      | libclang / gcc_xml         |
| xdress             | ✅  | ✅         | ❌      | libclang / pycparser       |
| cython-codegen     | ✅  | ❓         | ❌      | gcc_xml                    |
| fwrap              | ❌  | ❌         | ✅      | Custom Fortran parser      |
| pxd-gcc-generation | ✅  | ✅         | ❌      | GCC plugin                 |

## Feature Comparison (Active Tools)

| Feature                | autowrap            | python-autopxd2 |
|------------------------|---------------------|-----------------|
| Classes                | ✅                  | ✅              |
| Templates              | ✅                  | ✅              |
| Namespaces             | ✅                  | ✅              |
| Enums                  | ✅                  | ✅              |
| Static methods         | ✅                  | ✅              |
| Macro extraction       | ❌                  | ✅              |
| Forward declarations   | ❌                  | ✅              |
| Exception conversion   | ✅                  | ❌              |
| Operator overloads     | ✅                  | ✅              |
| Python special methods | ✅ (__hash__, etc.) | ❌              |
| Custom type converters | ✅                  | ❌              |
| Manual code injection  | ✅                  | ❌              |
| Docker image           | ❌                  | ✅              |

(Potential pipeline: header → autopxd2 → .pxd → add annotations → autowrap → .pyx)

---
## Unmaintained Tools

### cwrap

- Original: https://github.com/enthought/cwrap (gcc_xml, 2011)
- Fork: https://github.com/geggo/cwrap (libclang, ~2021)
- C++ support noted as "rudimentary" with known issues

### xdress

https://github.com/xdress/xdress
Last release over a decade ago. 72 open issues, 13 open PRs.

### cython-codegen (xml2cython.py)

https://github.com/cournape/cython-codegen
Author states: "YOU SHOULD CONSIDER IT UNSUPPORTED" and recommends clang-based tools.

### fwrap (Fortran only)

https://github.com/kwmsmith/fwrap
Beta software from ~2011. Requires Python 2.5-2.6.

### pxd-gcc-generation

https://github.com/robertwb/cython/tree/pxd-gcc-generation
Philip Herron's 2012 GSoC project. Requires gcc-python-plugin.

### h2pxd

Script by Evan Buswell. Status unknown.
http://groups.google.com/group/cython-users/browse_thread/thread/67c3c4443a9c98ca

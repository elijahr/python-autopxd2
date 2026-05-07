"""IR writer module - re-exported from headerkit.

The PxdWriter and write_pxd are now maintained in the headerkit package.
This module provides backward-compatible imports with autopxd2's
stub cimport prefix pre-configured.
"""

from headerkit.ir import Header
from headerkit.writers.cython import PxdWriter as _BasePxdWriter

_STUB_PREFIX = "autopxd.stubs"


class PxdWriter(_BasePxdWriter):
    """PxdWriter pre-configured with autopxd2 stub cimport prefix."""

    def __init__(self, header: Header) -> None:
        super().__init__(header, stub_cimport_prefix=_STUB_PREFIX)


def write_pxd(header: Header) -> str:
    """Convert IR Header to Cython .pxd with autopxd2 stub cimports."""
    writer = PxdWriter(header)
    return writer.write()

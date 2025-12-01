"""Enable running autopxd as a module: python -m autopxd"""

import sys

from autopxd import (
    cli,
)

if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    sys.exit(cli())

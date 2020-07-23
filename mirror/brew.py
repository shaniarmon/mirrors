import logging
import os
import sys

from .inspect import current_module_name


def main(args):
    pass

if __name__ == "__main__":
    logging.root.handlers = []
    if "MIRROR_DEBUG" in os.environ:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.DEBUG)
    else:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.INFO)

    log = logging.getLogger(current_module_name())
    main(sys.argv[1:])

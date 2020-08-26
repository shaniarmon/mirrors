import sys
import logging
import os


from .inspect import current_module_name


# This verifies package was imported before __main__. Not necessarily our entrypoint though :(
if sys.argv[0] == '-m':
    logging.root.handlers = []
    if "MIRROR_DEBUG" in os.environ:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.DEBUG)
    else:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.INFO)

VERSION = "0.1.0"

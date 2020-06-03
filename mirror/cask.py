import argparse
import os
import sys
import logging
from . import download
from .inspect import current_module_name
from .config import load_config, get_config_value


def mirror_cask(cask_name, output_directory):
    pass


def mirror_casks(config_file, output_directory):
    config = load_config(config_file)
    casks = get_config_value(config, "brew.casks", [])

    for cask in casks:
        mirror_cask(cask, output_directory)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-file", "-c", default="mirror.json")
    parser.add_argument("--output-directory", "-o", default=os.getcwd())
    args = parser.parse_args(argv)

    try:
        mirror_casks(args.config_file, args.output_directory)
    except Exception as e:
        log.debug("Stacktrace:", exc_info=e)
        sys.exit(f"Fatal: {type(e).__name__}: {e}")

if __name__ == "__main__":
    del logging.root.handlers[:]
    if "MIRROR_DEBUG" in os.environ:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.DEBUG, )
    else:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.INFO)

    log = logging.getLogger(current_module_name())

    main(sys.argv[1:])

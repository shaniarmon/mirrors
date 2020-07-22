import argparse
import os
import sys
import logging
import json
import re
import hashlib

from . import download
from .inspect import current_module_name
from .config import load_config, get_config_value
from .process import run_subprocess, SubprocessFailed


def sha256(filename):
    hash = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash.hexdigest()


def mirror_cask(cask_name, output_directory, output_file):
    log.info(f"Mirroring cask '{cask_name}'")
    formula_info = run_subprocess(["brew", "cask", "info", cask_name, "--json=v1"], capture_output=True,
                                  check=True, encoding="utf8")

    formula_info = json.loads(formula_info.stdout)

    url = formula_info[0]["url"]
    version = formula_info[0]["version"]

    filename = download.get_download_name(url)
    output_file.write(f"artifact-filename: {filename}\n")
    output_file.write(f"formula: {cask_name}.rb\n")
    output_file.write(f"artifact-sha256: {formula_info[0]['sha256']}\n")

    download_path = os.path.join(output_directory, filename)
    log.debug("Downloading ")
    already_done = False
    if os.path.exists(download_path):
        downloaded_hash = sha256(download_path)
        if downloaded_hash == formula_info[0]['sha256']:
            log.info("File already exists")
            already_done = True
    
    if not already_done:
        download.download_file(url, download_path)

        downloaded_hash = sha256(download_path)
        if downloaded_hash == formula_info[0]['sha256']:
            log.info("Successfully verified download hash")
        else:
            log.error("Download hash did not match formula: %s", f"{downloaded_hash=} != {formula_info[0]['sha256']=}")
            raise ValueError(f"Hash of formule '{cask_name}' was not successfully verified")

    formula = run_subprocess(["brew", "cask", "cat", cask_name],
                             capture_output=True, check=True, encoding="utf8").stdout

    formula = re.sub("url [\"'].*[\"']", f"url '{{placeholder_for_url}}/{filename}'", formula, count=1)
    with open(os.path.join(output_directory, f"{cask_name}.rb"), "w") as f:
        f.write(formula)


def mirror_casks(config_file, output_directory):
    config = load_config(config_file)
    casks = get_config_value(config, "brew.casks", [])

    cask_directory = os.path.join(output_directory, "casks")
    if not os.path.exists(cask_directory):
        os.mkdir(cask_directory)

    os.truncate(os.path.join(output_directory, "casks.status"), 0)
    for cask in casks:
        try:
            with open(os.path.join(output_directory, "casks.status"), "a") as f:
                mirror_cask(cask, cask_directory, f)
                f.write(f"{cask}: success\n")
        except Exception as e:
            log.info(f"Could not mirror cask '{cask}'. Failed with error {e.__class__.__name__}{e.args}")
            log.debug("Exception when downloading cask ", exc_info=True)
            with open(os.path.join(output_directory, "casks.status"), "a") as f:
                f.write(f"{cask}: failed\n")
        with open(os.path.join(output_directory, "casks.status"), "a") as f:
            f.write("---\n")


def main(argv):
    log.debug("Mirror cask executed")
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

import json
from collections import namedtuple
import subprocess
import os
import argparse
import sys
from functools import lru_cache
import logging
import inspect


SUPPORTED_OPERATING_SYSTEMS = ["catalina", "mojave"]

BottleInfo = namedtuple("BottleInfo", ["name", "os", "url", "sha256"])

os.environ["HOMEBREW_FORCE_HOMEBREW_ON_LINUX"] = "1"


class SubprocessFailed(Exception):
    pass


def current_module_name():
    calling_globals = inspect.stack()[1][0].f_globals
    
    if calling_globals['__name__'] != '__main__':
        return calling_globals['__name__']

    fqmn = ""
    if calling_globals['__package__']:
        fqmn += calling_globals['__package__'] + "."
    
    fqmn += os.path.basename(calling_globals['__file__']).rsplit('.', 1)[0]
    return fqmn


def get_logger():
    logging.getLogger(current_module_name())


def run_subprocess(*args, context=None, **kwargs):
    try:
        return subprocess.run(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        cli = subprocess.list2cmdline(e.cmd)
        raise SubprocessFailed(
            f"Command '{cli}' failed with error code {e.returncode} \n\t"
            f"context: {context} \n\tstdout: {e.stdout} \n\tstderr: {e.stderr}"
        ) from e

    except OSError as e:
        cli = subprocess.list2cmdline(args[0])
        raise SubprocessFailed(
            f"Failed to execute command '{cli}' \n\tcontext: {context}\n\t"
            f"Recieved error {e.__class__.__name__}: '{e}'"
        ) from e


def brew_update():
    run_subprocess(["brew", "update"], check=True)


def parse_brew_info(formulae):
    package_metadata = {"no_bottle": [], "bottles": []}

    for formula in formulae:
        if "stable" not in formula["bottle"]:
            package_metadata["no_bottle"].append((formula["name"], "any"))
            continue

        for operating_system in SUPPORTED_OPERATING_SYSTEMS:
            if operating_system not in formula["bottle"]["stable"]["files"]:
                package_metadata["no_bottle"].append(
                    (formula["name"], operating_system)
                )
                continue

            package_metadata["bottles"].append(
                BottleInfo(
                    formula["name"],
                    operating_system,
                    formula["bottle"]["stable"]["files"][operating_system]["url"],
                    formula["bottle"]["stable"]["files"][operating_system]["sha256"],
                )
            )
    return package_metadata


def get_taps():
    taps = run_subprocess(
        ["brew", "tap"], encoding="utf8", check=True, capture_output=True
    ).stdout.split()

    return taps


def brew_prefix():
    return run_subprocess(
        ["brew", "--prefix"], encoding="utf8", check=True, capture_output=True
    ).stdout.strip()


def tap_revision(tap):
    tap_directory, tap_name = tap.split("/")
    return run_subprocess(
        ["git", "rev-parse", "HEAD"],
        encoding="utf8",
        check=True,
        capture_output=True,
        cwd=os.path.join(
            brew_prefix(), "Library", "Taps", tap_directory, f"homebrew-{tap_name}"
        ),
    ).stdout.strip()


def tap_info(tap):
    revision = tap_revision(tap)

    brew_tap_info = run_subprocess(
        ["brew", "tap-info", tap, "--json"],
        capture_output=True,
        check=True,
        encoding="utf8",
    )

    tap_metadata = json.loads(brew_tap_info.stdout)[0]
    tap_metadata["revision"] = revision
    return tap_metadata


@lru_cache(maxsize=None)
def brew_info():
    brew_info = run_subprocess(
        ["brew", "info", "--all", "--json=v1"],
        capture_output=True,
        check=True,
        encoding="utf8",
    )
    formulae = json.loads(brew_info.stdout)

    return {formula["full_name"]: formula for formula in formulae}


def formula_info(name):
    formulae = brew_info()
    return formulae[name]


def calculate_current_tap_state(tap):
    info = tap_info(tap)
    formulae = []
    for name in info["formula_names"]:
        formulae.append(formula_info(name))
    info["formulae"] = parse_brew_info(formulae)
    return info


def load_previous_revision_info(folder):
    filename = os.path.join(folder, "HEAD")
    if not os.path.exists(filename):
        return {"formulae": {"no_bottle": [], "bottles": []}, "revision": "CLEAN", "previous_revision": None}
    with open(os.path.join(folder, "HEAD")) as f:
        return json.load(f)


def calculate_backtracking_delta(current, previous):
    current_bottles = {BottleInfo(*bottle) for bottle in current["formulae"]["bottles"]}
    previous_bottles = {BottleInfo(*bottle) for bottle in previous["formulae"]["bottles"]}

    new_bottles = current_bottles - previous_bottles
    removed_bottles = previous_bottles - current_bottles

    return {
        "previous_revision": previous["previous_revision"],
        "next_revision": current["revision"],
        "remove": list(new_bottles),
        "add": list(removed_bottles)
    }


def mirror(tap, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    current_revision = calculate_current_tap_state(tap)
    previous_revision = load_previous_revision_info(output_folder)
    if current_revision["revision"] == previous_revision["revision"]:
        raise ValueError("Already up to date")

    current_revision["previous_revision"] = previous_revision["revision"]
    delta = calculate_backtracking_delta(current_revision, previous_revision)

    with open(
        os.path.join(output_folder, f"{previous_revision['revision']}.delta"),
        "w",
        encoding="utf8",
    ) as f:
        json.dump(delta, f)

    with open(os.path.join(output_folder, "HEAD"), "w") as f:
        json.dump(current_revision, f)


def argument_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--no-update", dest="update", action="store_false")
    parser.add_argument("--output-folder", "-o", default="mirror")
    parser.add_argument("tap", nargs="?")
    return parser


def mirror_taps(taps, output_folder):
    for tap in taps:
        mirror(tap, os.path.join(output_folder, tap))


def main(args):
    parser = argument_parser()
    args = parser.parse_args(args)

    if args.update:
        brew_update()

    if args.tap is None:
        taps = get_taps()
    else:
        taps = [args.tap]

    try:
        mirror_taps(taps, args.output_folder)
    except Exception as e:
        log.debug("Stacktrace:", exc_info=e)
        sys.exit(f"Fatal: {type(e).__name__}: {e}")


if __name__ == "__main__":
    logging.root.handlers = []
    if "MIRROR_DEBUG" in os.environ:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.DEBUG)
    else:
        logging.basicConfig(format='{name}:{levelname}:{message}', style='{', level=logging.INFO)

    log = logging.getLogger(current_module_name())
    main(sys.argv[1:])

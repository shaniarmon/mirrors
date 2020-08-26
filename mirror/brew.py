import argparse
import logging
import os
import sys
from collections import namedtuple
from functools import lru_cache
import shutil
import json

from .inspect import current_module_name
from .process import run_subprocess
from .download import download_file

log = logging.getLogger(current_module_name())


SUPPORTED_OPERATING_SYSTEMS = ["catalina", "mojave"]

BottleInfo = namedtuple("BottleInfo", ["name", "os", "url", "sha256"])

os.environ["HOMEBREW_FORCE_HOMEBREW_ON_LINUX"] = "1"


class SubprocessFailed(Exception):
    pass


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

def set_tap_revision(tap, revision):
    tap_directory, tap_name = tap.split("/")
    run_subprocess(
        ["git", "checkout", revision],
        encoding="utf8",
        check=True,
        capture_output=True,
        cwd=os.path.join(
            brew_prefix(), "Library", "Taps", tap_directory, f"homebrew-{tap_name}"
        ),
    )

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


#@lru_cache(maxsize=None)
def brew_info():
    brew_info = run_subprocess(
        ["brew", "info", "--all", "--json=v1"],
        capture_output=True,
        check=True,
        encoding="utf8",
    )
    formulae = json.loads(brew_info.stdout)

    return {formula["full_name"]: formula for formula in formulae}


def formula_info(name, brew_info):
    return brew_info[name]


@lru_cache
def calculate_tap_state(tap, revision=None):
    current_revision = tap_revision(tap)
    if revision not in (None, current_revision):
        set_tap_revision(tap, revision)
    
    try:
        tap_metadata = tap_info(tap)
        formulae_info = brew_info()
        formulae = []
        for name in tap_metadata["formula_names"]:
            formulae.append(formula_info(name, formulae_info))
        tap_metadata["formulae"] = parse_brew_info(formulae)
        return tap_metadata
    finally:
        set_tap_revision(tap, current_revision)


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


def update_mirror_metadata(tap, output_folder, since=None):
    current_revision = calculate_tap_state(tap)

    if since is None:
        previous_revision = load_previous_revision_info(output_folder)
    else:
        previous_revision = calculate_tap_state(tap, since)
        previous_revision["previous_revision"] = None

    if current_revision["revision"] == previous_revision["revision"]:
        return

    current_revision["previous_revision"] = previous_revision["revision"]
    delta = calculate_backtracking_delta(current_revision, previous_revision)

    with open(
        os.path.join(output_folder, f"{previous_revision['revision']}.delta"),
        "w",
        encoding="utf8",
    ) as f:
        json.dump(delta, f)

    with open(os.path.join(output_folder, "HEAD"), "w", encoding="utf8") as f:
        json.dump(current_revision, f)


def download_mirror_bottles(repository_folder, since=None):
    with open(os.path.join(repository_folder, "HEAD"), "r") as f:
        mirror_info = json.load(f)
    
    if since is not None:
        last_downloaded_revision = since
    elif not os.path.exists(os.path.join(repository_folder, "LAST_DOWNLOADED_REVISION")):
        last_downloaded_revision = 'CLEAN'
    else:
        with open(os.path.join(repository_folder, "LAST_DOWNLOADED_REVISION")) as f:
            last_downloaded_revision = f.read()

    currently_downloading_revision = mirror_info["revision"]
    previous_revision = mirror_info['previous_revision']
    next_delta_file = f"{previous_revision}.delta"
    while not currently_downloading_revision.startswith(last_downloaded_revision):
        log.info(f"Currently downloading bottles for revision {currently_downloading_revision}")
        bottle_folder = os.path.join(repository_folder, "bottles", currently_downloading_revision)
        if not os.path.exists(bottle_folder):
            os.makedirs(bottle_folder)
        with open(os.path.join(repository_folder, next_delta_file)) as f:
            delta_contents = json.load(f)
        for bottle in delta_contents["remove"]:
            try:
                download_file(bottle[2], bottle_folder)
            except Exception as e:
                log.warning(f"Could not download '{bottle[0]}' for {bottle[1]}")

        currently_downloading_revision = previous_revision
        previous_revision = delta_contents['previous_revision']
        next_delta_file = f"{previous_revision}.delta"


def mirror(tap, output_folder, since=None):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    update_mirror_metadata(tap, output_folder, since=since)

    download_mirror_bottles(output_folder, since)


def mirror_taps(taps, output_folder):
    for tap in taps:
        mirror(tap, os.path.join(output_folder, tap))


def argument_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--no-update", dest="update", action="store_false", help="Should update brew tap before mirroring")
    parser.add_argument("--output-folder", "-o", default="mirror_output")
    parser.add_argument("--zip-folder", default="zip")
    parser.add_argument("--base-revision", "-r", default=None)
    parser.add_argument("tap")
    return parser


def brew_update():
    run_subprocess(["brew", "update"], check=True)


def main(args):
    parser = argument_parser()
    args = parser.parse_args(args)

    if args.update:
        brew_update()

    try:
        mirror(args.tap, args.output_folder, since=args.base_revision)
        os.makedirs(args.zip_folder)
        run_subprocess(["zip", "-s", "2g", "-r", "-0", os.path.join(os.path.abspath(args.zip_folder), "mirror.zip"), "."], cwd=args.output_folder, check=True)
    except Exception as e:
        log.debug("Stacktrace:", exc_info=e)
        sys.exit(f"Fatal: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main(sys.argv[1:])

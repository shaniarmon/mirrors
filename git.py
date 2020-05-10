#! /usr/bin/env python

import argparse
import tarfile
import os
import json
import sys
import tempfile
import subprocess


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def create_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("config_file")
    parser.add_argument("--output-directory", "-o", default=".")

    return parser


def download_git_repository(dest, url, output_dir):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "clone", "--mirror", url, d], check=True, capture_output=True, encoding='utf8')

        output_dir = os.path.join(output_dir, os.path.dirname(dest))
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        with tarfile.open(os.path.join(output_dir, f'{os.path.basename(dest)}.tar.gz'), "w:gz") as f:
            f.add(d, arcname=os.path.basename(url))


def download_git_repositories(repository_specs, output_dir):
    for spec in repository_specs:
        try:
            download_git_repository(spec['dest'], spec['url'], output_dir)
        except subprocess.CalledProcessError as e:
            print(f"Failed to download {spec['url']} with the following error:\n", e.stderr)
        else:
            print(f"Downloaded {spec['url']} successfully" )


def main(args=sys.argv):
    args = create_parser().parse_args()
    with open(args.config_file) as f:
        config = json.load(f)

    if not "git" in config:
        sys.exit("Fatal: No git repositories to mirror specified in config file")

    download_git_repositories(config["git"], args.output_directory)


if __name__ == "__main__":
    main()

#! /usr/bin/python3

import argparse as ap
import re
import subprocess as sp
import sys
from urllib.error import URLError


PAT_CORE_VERSION = re.compile(r"\d+[.]\d+[.]\d+")

TARBALL_PATH: str = "https://www.python.org/ftp/python/{ver_tree}/Python-{ver_file}.tgz"


def download_tarball(ver):
    try:
        ver_tree = PAT_CORE_VERSION.match(ver).group(0)
    except AttributeError:  # No match, getattr() on None
        print("ERROR: Could not construct tarball download URL")
        return False

    tb_path = TARBALL_PATH.format(ver_tree=ver_tree, ver_file=ver)

    try:
        result = sp.run(
            f"wget {tb_path}",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=60,
            check=True,
            shell=True,
        )
    except sp.CalledProcessError:
        print("\n\nERROR: Process error during tarball download")
        return False
    except sp.TimeoutExpired:
        print("\n\nERROR: Timeout during tarball download")
        return False

    return True


def extract_tarball():
    pass


def delete_tarball():
    pass


def edit_ssl():
    pass


def run_configure():
    pass


def make_python():
    pass


def install_python():
    pass


def update_symlinks():
    pass


def get_params():
    prs = ap.ArgumentParser(description="Automated download/build/install of CPython")

    prs.add_argument("version", help="Version of CPython to install")

    ns = prs.parse_args()
    return vars(ns)


def main():
    params = get_params()

    if not download_tarball(params["version"]):
        return 1


if __name__ == "__main__":
    sys.exit(main())

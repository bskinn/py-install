#! /usr/bin/python3

import argparse as ap
import subprocess as sp
import sys
from urllib.error import URLError

import wget

TARBALL_PATH: str = "https://www.python.org/ftp/python/{ver}/Python-{ver}.tgz"


def download_tarball(ver):
    try:
        wget.download(TARBALL_PATH.format(ver=ver))
    except URLError:
        return False
    else:
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

    if not download_tarball(params["ver"]):
        return 1


if __name__ == "__main__":
    sys.exit(main())

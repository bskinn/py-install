#! /usr/bin/python3

import argparse as ap
import re
import subprocess as sp
import sys
import tarfile
from pathlib import Path
from urllib.error import URLError


pat_version_patch = re.compile(r"\d+[.]\d+[.]\d+")
pat_version_minor = re.compile(r"\d+[.]\d+")

TARBALL_URL: str = "https://www.python.org/ftp/python/{ver_tree}/Python-{ver_file}.tgz"
TARBALL_FNAME: str = "Python-{ver_full}.tgz"

VERSION: str = "version"
VERSION_TO_PATCH: str = "version_patch"
VERSION_TO_MINOR: str = "version_minor"


def make_tarball_fname(params):
    return TARBALL_FNAME.format(ver_full=params[VERSION])


def download_tarball(params):
    tb_path = TARBALL_URL.format(
        ver_tree=params[VERSION_TO_PATCH], ver_file=params[VERSION]
    )

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
        print("\nERROR: Process error during tarball download")
        return False
    except sp.TimeoutExpired:
        print("\nERROR: Timeout during tarball download")
        return False

    return True


def check_tarball(tf):
    """Execute basic sanity checks."""
    return (
        len([name for name in tf.getnames() if not name.lower().startswith("python")])
        == 0
    )


def extract_tarball(params):
    tf = tarfile.open(make_tarball_fname(params))

    if not check_tarball(tf):
        print("\nERROR: Validation failure on downloaded tarball")
        return False

    print("Extracting tarball...", end="")
    try:
        tf.extractall()
    except Exception as e:
        print("\nERROR: Tarball extraction failed.\n")
        print(e)
        return False
    else:
        print("Done.")

    return True


def delete_tarball(params):
    try:
        Path(make_tarball_fname(params)).unlink()
    except Exception as e:
        print("\nERROR: Tarball deletion failed.\n")
        print(e)
        return False

    return True


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

    prs.add_argument(VERSION, help="Version of CPython to install")

    ns = prs.parse_args()
    return vars(ns)


def generate_reduced_versions(params):
    ver = params[VERSION]

    mch_patch = pat_version_patch.match(ver)

    if not mch_patch:
        print("\nERROR: Could not extract 'major.minor.patch' version")
        return False

    ver_patch = mch_patch.group(0)
    params[VERSION_TO_PATCH] = ver_patch

    mch_minor = pat_version_minor.match(ver_patch)

    if not mch_minor:
        print("\nERROR: Could not extract 'major.minor' version")
        return False

    params[VERSION_TO_MINOR] = mch_minor.group(0)

    return True


def main():
    params = get_params()

    if not generate_reduced_versions(params):
        return 1

    if not download_tarball(params):
        return 1

    if not extract_tarball(params):
        return 1

    if not delete_tarball(params):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

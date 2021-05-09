#! /usr/bin/python3

import argparse as ap
import os
import re
import subprocess as sp
import sys
import tarfile
from pathlib import Path
from urllib.error import URLError


pat_version_patch = re.compile(r"\d+[.]\d+[.]\d+")
pat_version_minor = re.compile(r"\d+[.]\d+")
pat_ssl_search = re.compile(r"\n(#SSL.+\n(#.+\n){3})")

TARBALL_URL: str = "https://www.python.org/ftp/python/{ver_tree}/Python-{ver_file}.tgz"
TARBALL_FNAME: str = "Python-{ver_full}.tgz"

SRC_DIR: str = "Python-{ver_full}/"
MODULES_FILE: str = "Python-{ver_full}/Modules/Setup"

BIN_DIR: str = "~/bin/"
INSTALL_DIR: str = "~/python/{ver_full}/"

VERSION: str = "version"
VERSION_TO_PATCH: str = "version_patch"
VERSION_TO_MINOR: str = "version_minor"

DEBUG_PARAMS = {VERSION: "3.8.0rc1", VERSION_TO_PATCH: "3.8.0", VERSION_TO_MINOR: "3.8"}


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


def edit_ssl(params):
    ld_locs = [
        l
        for l in os.environ["LD_LIBRARY_PATH"].strip(":").split(":")
        if "openssl" in l.lower()
    ]

    if not len(ld_locs):
        print("\nNo custom OpenSSL in LD_LIBRARY_PATH.")
        print("Skipping modifications to Modules/Setup")
        return True

    ld_loc = ld_locs[0].rpartition("/lib")[0]

    mod_file = MODULES_FILE.format(ver_full=params[VERSION])

    if Path(mod_file + ".dist").is_file():
        mod_file += ".dist"

    data = Path(mod_file).read_text()

    mch = pat_ssl_search.search(data)

    if mch is None:
        print("\nERROR: SSL config block not found in Setup file.")
        return False

    pre, block, post = data.partition(mch.group(1))
    lines = block.splitlines()

    lines.insert(1, f"SSL={ld_loc}")
    for idx in range(2, 5):
        lines[idx] = lines[idx].lstrip("#")

    new_block = "\n".join(lines)

    Path(mod_file).write_text(pre + new_block + post)

    return True


def run_configure(params):
    install_dir = INSTALL_DIR.format(ver_full=params[VERSION])
    install_dir = str(Path(install_dir).resolve())

    try:
        result = sp.run(
            f"./configure --enable-optimizations --prefix={install_dir}",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=180,
            check=True,
            shell=True,
            cwd=SRC_DIR.format(ver_full=params[VERSION]),
        )
    except sp.CalledProcessError:
        print("\nERROR: Process error during configure")
        return False
    except sp.TimeoutExpired:
        print("\nERROR: Timeout during configure")
        return False

    if result.returncode > 0:
        return False

    return True


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

    for func in [
        generate_reduced_versions,
        download_tarball,
        extract_tarball,
        delete_tarball,
        edit_ssl,
        run_configure,
    ]:
        if not func(params):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

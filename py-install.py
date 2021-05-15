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

SSL_ENV_VAR = "ssl_var"
SSL_BLOCK = "ssl_block"
pat_ssl_search = re.compile(
    rf"""
    \n                       # Need a leading uncaptured newline
    (?P<{SSL_BLOCK}>         # Capture for the entire block
        [#]\s*               # Var name line starts commented out
        (?P<{SSL_ENV_VAR}>   # Capture for just the var name
            (OPEN)?SSL       # SSL, or OPENSSL (>= 3.10.0b1)
        )
        .+\n                 # Arbitrary to EOL
        ([#].+\n)+           # Some additional number of commented-out lines
    )
""",
    re.X,
)

TARBALL_URL: str = "https://www.python.org/ftp/python/{ver_tree}/Python-{ver_file}.tgz"
TARBALL_FNAME: str = "Python-{ver_full}.tgz"

SRC_DIR: str = "Python-{ver_full}/"
MODULES_FILE: str = "Python-{ver_full}/Modules/Setup"

LINK_FILE: str = "{home}/bin/python{ver_minor}"
INSTALL_DIR: str = "{home}/python/{ver_full}/"
EXECUTABLE_FILE: str = "{install_dir}/bin/python{ver_minor}"

VERSION: str = "version"
VERSION_TO_PATCH: str = "version_patch"
VERSION_TO_MINOR: str = "version_minor"

KEY_INSTALL_DIR = "install_dir"
KEY_SRC_DIR = "src_dir"

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

    pre, block, post = data.partition(mch.group(SSL_BLOCK))
    lines = block.splitlines()

    new_lines = [lines[0]]
    new_lines.append(f"{mch.group(SSL_ENV_VAR)}={ld_loc}")
    new_lines.append(lines[1].lstrip("#").lstrip())
    for line in lines[2:]:
        new_lines.append(line.lstrip("#"))

    new_block = "\n".join(new_lines)

    Path(mod_file).write_text(pre + new_block + post)

    return True


def run_configure(params):
    install_dir = params[KEY_INSTALL_DIR]
    src_dir = params[KEY_SRC_DIR]

    try:
        result = sp.run(
            f"./configure --enable-optimizations --prefix={install_dir}",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=180,
            check=True,
            shell=True,
            cwd=src_dir,
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


def make_python(params):
    src_dir = params[KEY_SRC_DIR]

    try:
        result = sp.run(
            "make",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=1200,
            check=True,
            shell=True,
            cwd=src_dir,
        )
    except sp.CalledProcessError:
        print("\nERROR: Process error during make")
        return False
    except sp.TimeoutExpired:
        print("\nERROR: Timeout during make")
        return False

    if result.returncode > 0:
        return False

    return True


def install_python(params):
    src_dir = params[KEY_SRC_DIR]

    try:
        result = sp.run(
            "make install",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=240,
            check=True,
            shell=True,
            cwd=src_dir,
        )
    except sp.CalledProcessError:
        print("\nERROR: Process error during 'make install'")
        return False
    except sp.TimeoutExpired:
        print("\nERROR: Timeout during 'make install'")
        return False

    if result.returncode > 0:
        return False

    return True


def update_symlink(params):
    ver = params[VERSION]
    ver_minor = params[VERSION_TO_MINOR]

    exe_file = EXECUTABLE_FILE.format(
        install_dir=params[KEY_INSTALL_DIR], ver_minor=ver_minor
    )
    link_file = LINK_FILE.format(home=Path.home(), ver_minor=ver_minor)

    try:
        result = sp.run(
            f"ln -sf {exe_file} {link_file}",
            stdout=sys.stdout,
            stderr=sp.STDOUT,
            timeout=20,
            check=True,
            shell=True,
        )
    except sp.CalledProcessError:
        print("\nERROR: Process error during symlink creation")
        return False
    except sp.TimeoutExpired:
        print("\nERROR: Timeout during symlink creation")
        return False

    if result.returncode > 0:
        return False

    return True


def get_params():
    prs = ap.ArgumentParser(description="Automated download/build/install of CPython")

    prs.add_argument(VERSION, help="Version of CPython to install")

    ns = prs.parse_args()
    return vars(ns)


def update_params(params):
    install_dir = INSTALL_DIR.format(home=Path.home(), ver_full=params[VERSION])
    params[KEY_INSTALL_DIR] = str(Path(install_dir).resolve())

    params[KEY_SRC_DIR] = SRC_DIR.format(ver_full=params[VERSION])

    return True


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


def quick_params(ver):
    params = {VERSION: ver}
    generate_reduced_versions(params)
    update_params(params)

    return params


def main():
    params = get_params()

    for func in [
        generate_reduced_versions,
        update_params,
        download_tarball,
        extract_tarball,
        delete_tarball,
        edit_ssl,
        run_configure,
        make_python,
        install_python,
        update_symlink,
    ]:
        if not func(params):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

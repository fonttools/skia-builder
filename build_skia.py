#!/usr/bin/env python
import sys

import argparse
import glob
import os
import shutil
import subprocess


# script to bootstrap virtualenv without requiring pip
GET_VIRTUALENV_URL = "https://bootstrap.pypa.io/virtualenv.pyz"

EXE_EXT = ".exe" if sys.platform == "win32" else ""

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

SKIA_SRC_DIR = os.path.join(ROOT_DIR, "skia")
SKIA_BUILD_ARGS = [
    "is_official_build=true",
    "is_debug=false",
    "skia_enable_pdf=false",
    "skia_enable_discrete_gpu=false",
    "skia_enable_skottie=false",
    "skia_enable_skshaper=false",
    "skia_use_dng_sdk=false",
    "skia_use_expat=false",
    "skia_use_freetype=false",
    "skia_use_fontconfig=false",
    "skia_use_fonthost_mac=false",
    "skia_use_harfbuzz=false",
    "skia_use_icu=false",
    "skia_use_libgifcodec=false",
    "skia_use_libjpeg_turbo_encode=false",
    "skia_use_libjpeg_turbo_decode=false",
    "skia_use_libpng_encode=false",
    "skia_use_libpng_decode=false",
    "skia_use_libwebp_encode=false",
    "skia_use_libwebp_decode=false",
    "skia_use_piex=false",
    "skia_use_sfntly=false",
    "skia_use_xps=false",
    "skia_use_zlib=false",
    "skia_enable_spirv_validation=false",
    "skia_use_libheif=false",
    "skia_use_lua=false",
]
if sys.platform != "win32":
    # On Linux, I need this flag otherwise I get undefined symbol upon importing;
    # on Windows, defining this flag creates other linker issues (SkFontMgr being
    # redefined by SkFontMgr_win_dw_factory.obj)...
    SKIA_BUILD_ARGS.append("skia_enable_fontmgr_empty=true")
    # We don't need GPU or GL support, but disabling this on Windows creates lots
    # of undefined symbols upon linking the skia.dll, so I keep them for Windows...
    SKIA_BUILD_ARGS.append("skia_enable_gpu=false")
    SKIA_BUILD_ARGS.append("skia_use_gl=false")


def make_virtualenv(venv_dir):
    from contextlib import closing
    import io

    try:
        from urllib2 import urlopen  # PY2
    except ImportError:
        from urllib.request import urlopen  # PY3

    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    venv_bin_dir = os.path.join(venv_dir, bin_dir)
    python_exe = os.path.join(venv_bin_dir, "python" + EXE_EXT)

    # bootstrap virtualenv if not already present
    if not os.path.exists(python_exe):
        if not os.path.isdir(venv_bin_dir):
            os.makedirs(venv_bin_dir)
        virtualenv_pyz = os.path.join(venv_bin_dir, "virtualenv.pyz")
        with open(virtualenv_pyz, "wb") as f:
            with closing(urlopen(GET_VIRTUALENV_URL)) as response:
                f.write(response.read())
        returncode = subprocess.Popen(
            [sys.executable, virtualenv_pyz, "--no-download", venv_dir]
        ).wait()
        if returncode != 0:
            sys.exit("failed to create virtualenv")
    assert os.path.exists(python_exe)

    # pip install ninja
    ninja_exe = os.path.join(venv_bin_dir, "ninja" + EXE_EXT)
    if not os.path.exists(ninja_exe):
        subprocess.check_call(
            [
                os.path.join(venv_bin_dir, "pip" + EXE_EXT),
                "install",
                "--only-binary=ninja",
                "ninja",
            ]
        )

    # place virtualenv bin in front of $PATH, like 'source venv/bin/activate'
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([venv_bin_dir, env.get("PATH", "")])

    return env


# as supported by shutil.make_archive
ARCHIVE_FORMATS = {
    ".zip": "zip",
    ".tar": "tar",
    ".tar.gz": "gztar",
    ".tar.bz2": "bztar",
}


def _split_archive_base_and_format(parser, fname):
    for ext in ARCHIVE_FORMATS:
        if fname.endswith(ext):
            fmt = ARCHIVE_FORMATS[ext]
            break
    else:
        parser.error(
            "Invalid archive file extension {fname!r}. "
            "Choose from {formats}".format(fname=fname, formats=list(ARCHIVE_FORMATS))
        )
    return fname.split(ext)[0], fmt


def build_skia(
    src_dir,
    build_dir,
    build_args,
    target_cpu=None,
    env=None,
    shared_lib=False,
    gn_path=None,
):
    src_dir = os.path.abspath(src_dir)
    build_dir = os.path.abspath(build_dir)
    if target_cpu:
        build_args += ['target_cpu="{}"'.format(target_cpu)]
    if shared_lib:
        build_args += ["is_component_build=true"]
    if gn_path is None:
        gn_path = os.path.join(src_dir, "bin", "gn" + EXE_EXT)

    subprocess.check_call(
        [
            gn_path,
            "gen",
            os.path.abspath(build_dir),
            "--args={}".format(" ".join(build_args)),
        ],
        env=env,
        cwd=src_dir,
    )

    subprocess.check_call(["ninja", "-C", build_dir], env=env)

    # when building skia.dll on windows with gn and ninja, the DLL import file
    # is written as 'skia.dll.lib'; however, when linking it with the extension
    # module, setuptools expects it to be named 'skia.lib'.
    if sys.platform == "win32" and shared_lib:
        for f in glob.glob(os.path.join(build_dir, "skia.dll.*")):
            os.rename(f, f.replace(".dll", ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "build_dir",
        default=os.path.join("build", "skia"),
        nargs="?",
        help="directory where to build libskia (default: %(default)s)",
    )
    parser.add_argument(
        "-s",
        "--shared-lib",
        action="store_true",
        help="build a shared library (default: static)",
    )
    parser.add_argument(
        "--target-cpu",
        default=None,
        help="The desired CPU architecture for the build (default: host)",
        choices=["x86", "x64", "arm", "arm64", "mipsel", "universal2"],
    )
    parser.add_argument("-a", "--archive-file", default=None)
    parser.add_argument("--no-virtualenv", dest="make_virtualenv", action="store_false")
    parser.add_argument("--no-sync-deps", dest="sync_deps", action="store_false")
    parser.add_argument("--no-fetch-gn", dest="fetch_gn", action="store_false")
    parser.add_argument("--gn-path", default=None)
    args = parser.parse_args()

    if args.target_cpu == "universal2" and sys.platform != "darwin":
        parser.error("--target-cpu='universal2' only works on MacOS")

    if args.archive_file is not None:
        archive_base, archive_fmt = _split_archive_base_and_format(
            parser, args.archive_file
        )

    build_base_dir = os.path.abspath(args.build_dir)
    if args.make_virtualenv:
        venv_dir = os.path.join(build_base_dir, "venv")
        env = make_virtualenv(venv_dir)
    else:
        env = os.environ.copy()

    # https://github.com/fonttools/skia-pathops/issues/41
    if sys.platform == "darwin":
        env["MACOSX_DEPLOYMENT_TARGET"] = "10.9"

    if args.sync_deps:
        subprocess.check_call(
            ["python", os.path.join("tools", "git-sync-deps")],
            env=env,
            cwd=SKIA_SRC_DIR,
        )
    elif args.fetch_gn:
        subprocess.check_call(
            ["python", os.path.join("bin", "fetch-gn")],
            env=env,
            cwd=SKIA_SRC_DIR,
        )

    is_universal2 = args.target_cpu == "universal2"

    builds = (
        [
            (os.path.join(build_base_dir, target_cpu), target_cpu)
            for target_cpu in ("x64", "arm64")
        ]
        if is_universal2
        else [(build_base_dir, args.target_cpu)]
    )

    for build_dir, target_cpu in builds:
        build_skia(
            SKIA_SRC_DIR,
            build_dir,
            SKIA_BUILD_ARGS,
            target_cpu,
            env,
            args.shared_lib,
            args.gn_path,
        )

    if is_universal2:
        # create universal binary by merging multiple archs with the 'lipo' tool:
        # https://developer.apple.com/documentation/apple-silicon/building-a-universal-macos-binary
        libname = "libskia." + ("so" if args.shared_lib else "a")
        libraries = [os.path.join(build_dir, libname) for build_dir, _ in builds]
        dest_path = os.path.join(build_base_dir, libname)
        subprocess.check_call(["lipo", "-create", "-output", dest_path] + libraries)
        # confirm that we got a 'fat' binary
        result = subprocess.check_output(["lipo", "-archs", dest_path])
        assert "x86_64 arm64" == result.decode().strip()

    if args.archive_file is not None:
        # we pack the whole build_base_dir except for the venv/ subdir
        if args.make_virtualenv:
            shutil.rmtree(venv_dir)
        shutil.make_archive(archive_base, archive_fmt, build_base_dir)

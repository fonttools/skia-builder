#!/bin/bash

set -e

PYTHON2_EXE=${PYTHON2_EXE:-python2}
ARCH=${ARCH:-x64}

if [ "$(uname)" == "Darwin" ]; then
    PLAT=mac
else
    PLAT=linux
fi

mkdir -p dist

"${PYTHON2_EXE}" build_skia.py --target-cpu ${ARCH} ${BUILD_SKIA_OPTIONS} --archive-file dist/libskia-${PLAT}-${ARCH}.zip

ls dist/*.zip

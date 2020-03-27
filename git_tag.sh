#!/bin/bash

cd skia
skia_submodule_branch=$(git rev-parse --abbrev-ref HEAD)
skia_submodule_commit=$(git rev-parse HEAD)
cd ..

tag_name="${skia_submodule_branch}@${skia_submodule_commit:0:7}"

read -r -d '' tag_msg <<- EOM
	$tag_name

	https://github.com/fonttools/skia/commit/$skia_submodule_commit
EOM

echo "$tag_msg"

git tag -s -m "${tag_msg}" $tag_name

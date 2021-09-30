#!/bin/bash
pushd ./testmedia
rm -rf *.mp4
rm -rf *.jpg

cp -f .orig/* .

popd

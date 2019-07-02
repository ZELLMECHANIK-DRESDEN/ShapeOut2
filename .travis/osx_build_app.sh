#!/bin/bash

if [ -z $1 ]; then
    echo "Please specify package name as command line argument!"
    exit 1
fi

NAME=$1
# append "App" to avoid naming conflicts with python library
SCRIPT=".travis/${1}App.py"
APP_DIST="./dist_app/${1}App.app"
APP="./dist_app/${1}App.app"
DMG="./dist_app/${1}.dmg"
TMP="./dist_app/pack.temp.dmg"
pip install pyinstaller

pyinstaller -w -y --additional-hooks-dir=".travis" $SCRIPT

# Work in a different directory, otherwise PyPI deployment on travis-CI
# tries to upload *.dmg files
mkdir -p ./dist_app
mv $APP_DIST $APP

# create temporary DMG
hdiutil create -srcfolder "${APP}" -volname "${NAME}" -fs HFS+ \
        -fsargs "-c c=64,a=16,e=16" -format UDRW "${TMP}"

# optional: edit the DMG
# https://stackoverflow.com/questions/96882/how-do-i-create-a-nice-looking-dmg-for-mac-os-x-using-command-line-tools

# create crompressed DMG
hdiutil convert "${TMP}" -format UDZO -imagekey zlib-level=9 -o "${DMG}"

# remove temporary DMG
rm $TMP


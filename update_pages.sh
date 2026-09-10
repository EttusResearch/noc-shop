#!/bin/bash
make html || exit
git checkout pages
git rm -r docs
cp -r build/html docs
touch docs/.nojekyll
git add docs

#!/bin/bash
make html
git checkout pages
git rm -r docs
cp -r build/html docs
touch docs/.nojekyll
git add docs

#!/bin/sh

mkdir -p dist

tar zcvf dist/frontend.tgz index.html index.js package.json package-lock.json assets
tar zcvf dist/backend.tgz __init__.py backend.py converter.py iir requirements.txt

rsync -arv --delete \
  dist/frontend.tgz \
  dist/backend.tgz \
  scripts/deploy.sh \
  etc \
  spin@spinorama.org:/home/spin/deploy


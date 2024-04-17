#!/bin/bash

echo "Daily update started"

python3 scraper.py

cp html/vexgen.github.io/index.html html/vexgen.github.io/archive/$(date +%Y-%m-%d).html

git add .
git commit -m "Daily update"
git push -u origin main

echo "Daily update complete"

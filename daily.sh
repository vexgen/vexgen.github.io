#!/bin/bash

echo "Daily update started"

python3 /home/jamie/development/python/nvdScrape/scraper.py

cp index.html archive/$(date +%Y-%m-%d).html

git add .
git commit -m "Daily update"
git push -u origin main

echo "Daily update complete"

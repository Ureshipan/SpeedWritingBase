#!/bin/bash

cd $(dirname "$0")

source venv/bin/activate
echo "sourced"
python app.py > /dev/null 2>&1 &
echo "started"
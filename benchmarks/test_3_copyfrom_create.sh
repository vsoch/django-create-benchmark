#!/bin/bash

# Save output file to pwd
HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT=$(dirname ${HERE})
python manage.py test_3_copyfrom_create "$ROOT/data/genes.json"  "${HERE}/test_3_copyfrom_create.csv"

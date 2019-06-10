#!/usr/bin/env sh

BASEDIR=$(dirname $0)
PYTHON_PATH=$BASEDIR/../byht/venv/bin/python3

$PYTHON_PATH $BASEDIR/../byht/byht.py $@

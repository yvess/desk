#!/bin/bash
coverage run --omit="./py27/*" --source="./,./plugin" -m unittest discover && coverage html

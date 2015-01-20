#!/bin/bash

fig run --rm foreman worker /var/py27/bin/python -m unittest discover

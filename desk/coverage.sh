#!/bin/bash

coverage run --branch -m unittest discover
coverage html
open htmlcov/index.html

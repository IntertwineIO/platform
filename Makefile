#
# Makefile for intertwine
#

PWD := $(shell pwd)
KERNEL := $(shell uname -s)
SHELL := /bin/bash
VENV := .virtualenv


prereqs:
ifeq ($(KERNEL),Darwin)
	pyenv install --skip-existing
endif

pristine:
	rm -rf $(VENV)

setup:
	[[ -d $(VENV) ]] || $(MAKE) virtualenv
	$(MAKE) dependencies

virtualenv:
	command -v deactivate && deactivate || true
	python3 -m venv --prompt=intertwine $(VENV)
	source $(VENV)/bin/activate && pip3 install --upgrade pip pip-tools

dependencies: virtualenv
	$(MAKE) pip_sync

requirements.txt: requirements.in
	source $(VENV)/bin/activate && pip-compile --no-index --output-file requirements.txt requirements.in

pip_sync: requirements.txt
	source $(VENV)/bin/activate; \
	pip-sync requirements.txt

test:
	source $(VENV)/bin/activate && \
	python -m pytest
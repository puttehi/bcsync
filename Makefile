SHELL:=/bin/bash

# Project settings
PROJECT_NAME:=bcsync
ENTRYPOINT:=src/$(PROJECT_NAME).py

# Install dir
INSTALL_DIR:=~/$(PROJECT_NAME)
LINK_DIR:=~/bin

# Shortcut
PR:=poetry run
MP:=MYPYPATH=src $(PR) mypy src
QUIET:=>> /dev/null 2>&1

install: format lint clean build copy

install-unstable: format build copy

setup:
	poetry install --no-dev

setup-dev:
	poetry install

format: setup-dev
	$(PR) black .
	$(PR) isort .

lint: setup-dev
	MYPYPATH=src \
			 $(PR) mypy \
			 src \
			 --namespace-packages \
			 --explicit-package-bases \
			 --install-types

build: setup-dev
	$(PR) pyinstaller $(ENTRYPOINT)

copy:
	cp dist/$(PROJECT_NAME)/* $(INSTALL_DIR)/ -r
	ln -si $(INSTALL_DIR)/$(PROJECT_NAME) $(LINK_DIR)/$(PROJECT_NAME)

clean:
	-@rm dist -r \
		build -r \
		out -r \
		.mypy_cache -r \
		__pycache__ -r \
		*.spec \
		src/log/ \
		src/**/__pycache__ $(QUIET)

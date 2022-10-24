SHELL:=/bin/bash

PR:=poetry run
INSTALL_DIR:=~
LINK_DIR:=~/bin

PROJECT_NAME:=bcsync
ENTRYPOINT:=$(PROJECT_NAME).py

install: setup-dev format lint	
	$(PR) pyinstaller $(ENTRYPOINT)
	cp dist/$(PROJECT_NAME)/* $(INSTALL_DIR)/$(PROJECT_NAME)/ -r
	ln -si $(INSTALL_DIR)/$(PROJECT_NAME)/$(PROJECT_NAME) $(LINK_DIR)/$(PROJECT_NAME)

install-unstable: setup-dev format
	$(PR) pyinstaller $(ENTRYPOINT)
	cp dist/$(PROJECT_NAME)/* $(INSTALL_DIR)/$(PROJECT_NAME)/ -r
	ln -si $(INSTALL_DIR)/$(PROJECT_NAME)/$(PROJECT_NAME) $(LINK_DIR)/$(PROJECT_NAME)

setup:
	poetry install --no-dev

setup-dev:
	poetry install

format: setup-dev
	$(PR) black .
	$(PR) isort .

lint: setup-dev
	$(PR) mypy --install-types
	$(PR) mypy . --namespace-packages --explicit-package-bases

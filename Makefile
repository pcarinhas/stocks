SHELL := /bin/bash
# To install go and rust, do a "make all"
all: golang rust python

define RED
\033[0;31m
endef
export RED

define GREEN
\033[0;32m
endef
export GREEN

define NOCOLOR
\033[0m
endef
export NOCOLOR

define PYENV_SH
#! /bin/bash
# Script to enable pyenv's python
export PYENV_ROOT="$(HOME)/.pyenv"
command -v pyenv >/dev/null || export PATH="$$PYENV_ROOT/bin:$$PATH"
eval "$$(pyenv init -)"
export PS1="pyenv:$$(pyenv global)$$PS1"
endef
export PYENV_SH

pyenv:
	@test -d $(HOME)/.pyenv || curl https://pyenv.run | bash
	# Install build environment for Debian/Ubuntu/Mint
	@dpkg -l build-essential libssl-dev zlib1g-dev curl git &> /dev/null \
	   || ( sudo apt update; sudo apt install build-essential libssl-dev zlib1g-dev \
	      libbz2-dev libreadline-dev libsqlite3-dev curl git libncursesw5-dev \
	      xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev )
	@# Ensure $HOME/bin exists
	@mkdir -p $(HOME)/bin
	# Install the $HOME/bin/pyenv.sh convenience script
	@test -f $(HOME)/bin/pyenv.sh || /bin/echo "$$PYENV_SH" > $(HOME)/bin/pyenv.sh ; \
	   chmod 700 $(HOME)/bin/pyenv.sh
	@echo -e "\t $${GREEN}pyenv.sh is installed, \
	 but you have to invoke it manually.$${NOCOLOR}"
	@echo -e "\t Consider installing it permanently in your shell: \n\t \
		$${RED}echo \'. ~/bin/pyenv.sh\' >> .bashrc$${NOCOLOR}"

python: pyenv
	. $(HOME)/bin/pyenv.sh && \
	   pyenv versions | grep 3.11 || \
	   pyenv install 3.11:latest
	. $(HOME)/bin/pyenv.sh && pyenv global 3.11

deps:
	pip install -r requirements.txt

install: deps
	mkdir -p $(HOME)/bin
	cp scripts/* $(HOME)/bin
	mv $(HOME)/bin/qu.py $(HOME)/bin/qu

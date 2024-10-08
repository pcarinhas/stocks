Stock Utilities
===================

The main tool is the *qu* script that gets installed to **~/bin**.

Installing the Repo
----------------------

Install this repo into your account::

   git clone https://github.com/pcarinhas/stocks
   cd stocks

Then follow the requirements and Installation section below.

Requirements
-------------

* You should be running Linux
* You must have a version of Python installed in your personal account.
  If you don't have one you may be able to use the given Makefile to install
  one::

     make python
     source ~/bin/pyenv.sh

You may wish to activate python when you login. In that case add this line to
your .bashrc file::

   source ~/bin/pyenv.sh


Installation
-------------

Installation should be easy::

   make install


Usage of *qu*
--------------

To use **qu**, open a terminal and type::

   qu amd intc




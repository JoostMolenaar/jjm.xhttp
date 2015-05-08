NAME = xhttp

PIP_NAME = xhttp
PIP_REQ = requirements.txt

MAIN ?= xhttp.test

PKG = xmlist

server: runtime-test
	cd $(ENV) ; bin/python -m xhttp.test

include build/Makefile

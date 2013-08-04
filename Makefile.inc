NAME = xhttp

PIP_NAME = xhttp
PIP_REQ = requirements.txt

MAIN ?= xhttp.test

PKG = xmlist

server:
	cd $(ENV) ; bin/python -m xhttp.test

unittest:
	cd tests ; ../$(ENV)/bin/python -m unittest testxhttp

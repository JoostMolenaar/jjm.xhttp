NAME = xhttp

PIP_NAME = jjm.xhttp
PIP_REQ = requirements.txt

MAIN ?= jjm.xhttp.test

PKG_BASE = file:///home/joost/git
PKG = jjm jjm.xml

server:
	cd $(ENV) ; bin/python -m jjm.xhttp.test

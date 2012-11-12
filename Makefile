
include Makefile.inc

ENV = env

TARGET = /srv/$(NAME)
TARGET_USER ?= www-data
TARGET_GROUP ?= www-data

DEPLOY_WEB = $(ENV)/web
DEPLOY_CONF = $(ENV)/conf

SRC = file://$(shell pwd)

PIP_CACHE = .cache

.PHONY: run

run: runtime
	$(ENV)/bin/pip uninstall $(PIP_NAME) --yes --quiet || true
	$(ENV)/bin/python -m $(MAIN)

run-pkg: deploy
	$(ENV)/bin/pip install $(SRC) 
	cd $(ENV) ; bin/python -m $(MAIN)

deploy-live: deploy
	virtualenv --relocatable $(ENV) > /dev/null
	sudo chown -R $(TARGET_USER).$(TARGET_GROUP) $(ENV)
	sudo rm -rf $(TARGET)
	sudo mv $(ENV) $(TARGET)

deploy: runtime deploy-code deploy-web deploy-conf touch-conf

runtime: $(ENV)

$(ENV):
	virtualenv $(ENV) --quiet
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) 'distribute>=0.6.30' --quiet
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) --requirement $(PIP_REQ) --quiet

deploy-code:
	$(ENV)/bin/pip install $(SRC) --quiet

deploy-web:
	@rm -rf $(DEPLOY_WEB)
	cp -r web $(DEPLOY_WEB)

deploy-conf:
	@rm -rf $(DEPLOY_CONF)
	cp -r conf $(DEPLOY_CONF)

touch-conf:
	ls $(DEPLOY_CONF)/uwsgi/* > /dev/null 2>&1 && touch $(DEPLOY_CONF)/uwsgi/* || true

clean:
	rm -rf $(ENV)

really-clean: clean
	rm -rf $(PIP_CACHE)

# - rename web to static
# - extract xml from core
# - extract sh from core
# - make repo's relative or something ... referring to file:///home/joost/git/... is not useful in other situations

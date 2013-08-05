
include Makefile.inc

ENV ?= env
ENV_VERSION ?= python2.7
SITE_PACKAGES = $(ENV)/lib/$(ENV_VERSION)/site-packages

TARGET = /srv/$(NAME)
TARGET_USER ?= www-data
TARGET_GROUP ?= www-data

ifeq ($(shell id -n -u),root)
    SUDO =
else
    SUDO = sudo
endif

QUIET ?= --quiet

PIP_CACHE = .cache

PKG_BASE ?= $(shell readlink -f ..)

.PHONY: run

#
# run the code
#

test: runtime-test
	cd $(ENV) ; bin/python -m $(MAIN)

run: runtime-live
	cd $(ENV) ; bin/python -m $(MAIN)

#
# deploy
#

deploy: runtime-live
	cp -r $(ENV) staging
	virtualenv --relocatable staging $(QUIET) >/dev/null
	$(SUDO) chown -R $(TARGET_USER).$(TARGET_GROUP) staging
	$(SUDO) rm -rf $(TARGET)
	$(SUDO) mv staging $(TARGET)

#
# runtime
#

runtime-live: $(ENV) $(ENV)/.$(PIP_REQ) unlink-pkgs unlink-code unlink-data deploy-pkgs deploy-code deploy-data

runtime-test: $(ENV) $(ENV)/.$(PIP_REQ) undeploy-pkgs undeploy-code undeploy-data link-pkgs link-code link-data

$(ENV): 
	virtualenv --python=$(ENV_VERSION) $(ENV) $(QUIET)
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) 'distribute>=0.6.30' $(QUIET)

$(ENV)/.$(PIP_REQ): $(PIP_REQ)
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) --requirement $(PIP_REQ) $(QUIET)
	@touch $@

#
# packages
#

deploy-pkgs: $(addprefix $(ENV)/.pkg-,$(PKG))

$(ENV)/.pkg-%:
	$(ENV)/bin/pip install --upgrade file://$(PKG_BASE)/$* $(QUIET)
	@touch $@

undeploy-pkgs: $(addprefix undeploy-pkg-,$(PKG))

undeploy-pkg-%:
	@test -f $(ENV)/.pkg-$* && $(ENV)/bin/pip uninstall --yes $* $(QUIET) 1>/dev/null 2>&1 || true
	@rm -f $(ENV)/.pkg-$*

link-pkgs: $(addprefix $(ENV)/.pkglink-,$(PKG))

$(ENV)/.pkglink-%:
	ln -snf $(PKG_BASE)/$*/$* $(SITE_PACKAGES)/$*
	@touch $@

unlink-pkgs: $(addprefix unlink-pkg-,$(PKG))

unlink-pkg-%:
	@test -L $(SITE_PACKAGES)/$* && rm $(SITE_PACKAGES)/$* || true
	@rm -f $(ENV)/.pkglink-$*

#
# code
#

deploy-code: $(ENV)/.pkg-$(PIP_NAME)

undeploy-code: undeploy-pkg-$(PIP_NAME)

link-code: $(ENV)/.pkglink-$(PIP_NAME)

unlink-code: unlink-pkg-$(PIP_NAME)

#
# data
#

deploy-data: $(addprefix $(ENV)/.data-,$(STATIC_DIRS))

undeploy-data: $(addprefix undeploy-dir-,$(STATIC_DIRS))

$(ENV)/.data-%: $*
	cp -r $* $(ENV)
	@touch $@

undeploy-dir-%:
	@test -f $(ENV)/.data-$* && rm -rf $(ENV)/$* || true
	@rm -f $(ENV)/.data-$*

link-data: $(addprefix $(ENV)/.datalink-,$(STATIC_DIRS))

unlink-data: $(addprefix unlink-dir-,$(STATIC_DIRS))

$(ENV)/.datalink-%:
	ln -snf $(shell pwd)/$* $(ENV)/$*
	@touch $@

unlink-dir-%:
	@test -f $(ENV)/.datalink-$* && rm -f $(ENV)/$* || true
	@rm -f $(ENV)/.datalink-$*

#
# clean
#

clean:
	rm -rf $(ENV)

really-clean: clean
	rm -rf $(PIP_CACHE)

# unit testing

unit-test: runtime-test
	cd tests ; ../$(ENV)/bin/python -m unittest discover

coverage: runtime-test
	rm -rf tests/htmlcov
	rm -f tests/.coverage
	cd tests ; ../$(ENV)/bin/coverage run --branch -m unittest discover
	cd tests ; ../$(ENV)/bin/coverage html


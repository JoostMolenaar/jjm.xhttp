
PY_VERSION ?= python2.7
PY_OPTS ?= -B 

TAG = $(subst .,,$(subst python,,$(PY_VERSION)))

ENV = env$(TAG)

COVERAGE_FILE       = .coverage$(TAG)
COVERAGE_OUTPUT_DIR = htmlcov$(TAG)

export COVERAGE_FILE
export COVERAGE_OUTPUT_DIR

TARGET = /srv/$(NAME)
TARGET_USER ?= www-data
TARGET_GROUP ?= www-data

SITE_PACKAGES = $(ENV)/lib/$(PY_VERSION)/site-packages

ifeq ($(shell id -n -u),root)
    SUDO =
else
    SUDO = sudo
endif

QUIET ?= --quiet

PIP_CACHE = .cache$(TAG)

PKG_BASE ?= $(shell readlink -f ..)

.PHONY: run

#
# run the code
#

test: runtime-test
	cd $(ENV) ; bin/python $(PY_OPTS) -m $(MAIN)

run: runtime-live
	cd $(ENV) ; bin/python $(PY_OPTS) -m $(MAIN)

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
	virtualenv --python=$(PY_VERSION) $(ENV) $(QUIET)

$(ENV)/.$(PIP_REQ): $(PIP_REQ)
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) --requirement $(PIP_REQ) $(QUIET)
	@touch $@

#
# packages
#

deploy-pkgs: $(addprefix $(ENV)/.pkg-,$(PKG))

$(ENV)/.pkg-%:
	cd $(PKG_BASE)/$* ; ./setup.py sdist $(QUIET)
	$(ENV)/bin/pip install --upgrade $(PKG_BASE)/$*/dist/$*-$(shell $(PKG_BASE)/$*/setup.py --version).tar.gz
	@touch $@

undeploy-pkgs: $(addprefix undeploy-pkg-,$(PKG))

undeploy-pkg-%:
	@test -f $(ENV)/.pkg-$* && $(ENV)/bin/pip uninstall --yes $* $(QUIET) 1>/dev/null 2>&1 || true
	@rm -f $(ENV)/.pkg-$*

link-pkgs: $(addprefix $(ENV)/.pkglink-,$(PKG))

$(ENV)/.pkglink-%:
	@IS_PACKAGE=${shell test -d $(PKG_BASE)/$*/$* && echo 1 || echo 0}
ifeq ($(IS_PACKAGE),1)
	ln -snf $(PKG_BASE)/$*/$* $(SITE_PACKAGES)/$*
else
	ln -snf $(PKG_BASE)/$*/$*.py $(SITE_PACKAGES)/$*.py
endif
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
	rm -rf tests/$(COVERAGE_OUTPUT_DIR)
	rm -f tests/$(COVERAGE_FILE)
	rm -f MANIFEST
	rm -rf dist

really-clean: clean
	rm -rf $(PIP_CACHE)

#
# unit testing
#

unit-test: runtime-test
	cd tests ; ../$(ENV)/bin/python $(PY_OPTS) -m unittest discover -v

coverage: runtime-test
	rm -rf tests/$(COVERAGE_OUTPUT_DIR)
	rm -f tests/$(COVERAGE_FILE)
	cd tests ; ../$(ENV)/bin/python $(PY_OPTS) ../$(ENV)/bin/coverage run --branch -m unittest discover -v || true
	cd tests ; ../$(ENV)/bin/python $(PY_OPTS) ../$(ENV)/bin/coverage html

continuous-%:
	inotifywait -r . -q -m -e CLOSE_WRITE | grep --line-buffered '^.*\.py$$' | while read line; do clear; date; echo $$line; echo; make $*; done

continuous: continuous-coverage

profile:
	cd tests ; ../$(ENV)/bin/python $(PY_OPTS) profile.py

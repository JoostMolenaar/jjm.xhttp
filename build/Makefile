
-include Makefile.in

PY_VERSION ?= python2.7
PY_OPTS ?= -B 

TAG = $(subst .,,$(subst python,,$(PY_VERSION)))

ENV = env$(TAG)

WHL = /tmp/pypkg$(TAG)

COVERAGE_FILE = .coverage$(TAG)
COVERAGE_OUTPUT_DIR = htmlcov$(TAG)

export COVERAGE_FILE
export COVERAGE_OUTPUT_DIR

TARGET = /srv/$(PIP_NAME)
TARGET_USER ?= www-data
TARGET_GROUP ?= www-data

ifeq ($(shell id -n -u),root)
    SUDO =
else
    SUDO = sudo
endif

QUIET ?= --quiet

.PHONY: run

#
# run the code
#

test: runtime-test
	cd $(ENV) ; bin/python $(PY_OPTS) -m $(MAIN)

run: runtime-live
	cd $(ENV) ; bin/python $(PY_OPTS) -m $(MAIN)

# test evil hack

ALL_DEPS = import pip 
ALL_DEPS += ; D = { d.key: d for d in pip.get_installed_distributions() } 
ALL_DEPS += ; F = lambda xs: sum([ F(x) if isinstance(x, list) else [x] for x in xs ], []) 
ALL_DEPS += ; R = lambda k: [k] + F([ R(r.key) for r in D[k].requires() ]) 
ALL_DEPS += ; print " ".join(R("__PKG__") if "__PKG__" in D else [])

ALL_DEPS_HACK = `cd $(ENV) ; bin/python -c '$(ALL_DEPS)'`

alldeps:
	@echo PKG = $(PKG)
	@echo STATIC_DIRS = $(STATIC_DIRS)
	@echo PIP_NAME = $(PIP_NAME)
	echo $(subst __PKG__,$(PIP_NAME),$(ALL_DEPS_HACK))

# requirements.txt

$(PIP_REQ): $(ENV) setup.py
	$(ENV)/bin/python setup.py --package-names > requirements.txt

# deploy

deploy: runtime-live
	cp -r $(ENV) staging
	virtualenv --relocatable staging $(QUIET) >/dev/null
	$(SUDO) chown -R $(TARGET_USER).$(TARGET_GROUP) staging
	$(SUDO) rm -rf $(TARGET)
	$(SUDO) mv staging $(TARGET)

# runtime

runtime-live: $(ENV) unlink-code unlink-data deploy-code 

runtime-test: $(ENV) undeploy-code link-pkgs link-code link-data

$(ENV): $(WHL)-ok
	virtualenv --python=$(PY_VERSION) $(ENV) $(QUIET)
	$(ENV)/bin/pip install --no-index --find-links=$(WHL) --use-wheel --upgrade pip setuptools wheel $(QUIET)

# packages

deploy-pkgs: $(addprefix $(ENV)/.pkg-,$(PKG))

$(ENV)/.pkg-%:
	$(ENV)/bin/pip install --no-index --find-links=$(WHL) --use-wheel --upgrade $* $(QUIET)
	@touch $@

undeploy-pkgs: $(addprefix undeploy-pkg-,$(PKG))

undeploy-pkg-%: 
	@test -f $(ENV)/.pkg-$* && $(ENV)/bin/pip uninstall --yes $(subst __PKG__,$*,$(ALL_DEPS_HACK)) $(QUIET) || true
	@rm -f $(ENV)/.pkg-$*

link-pkgs: $(addprefix $(ENV)/.pkglink-,$(PKG))

$(ENV)/.pkglink-%:
	$(ENV)/bin/pip install --no-index --find-links=$(WHL) --use-wheel --editable $(PKG_BASE)/$* $(QUIET)
	@touch $@

unlink-pkgs: $(addprefix unlink-pkg-,$(PKG))

unlink-pkg-%: 
	@test -f $(ENV)/.pkglink-$* && $(ENV)/bin/pip uninstall --yes $(subst __PKG__,$*,$(ALL_DEPS_HACK)) $(QUIET) || true
	@rm -f $(ENV)/.pkglink-*

# code

deploy-code: $(ENV)/.pkg-$(PIP_NAME)

undeploy-code: undeploy-pkg-$(PIP_NAME)

link-code: $(ENV)/.pkglink-$(PIP_NAME)

unlink-code: unlink-pkg-$(PIP_NAME)

# data

link-data: $(addprefix $(ENV)/.datalink-,$(STATIC_DIRS))

unlink-data: $(addprefix unlink-dir-,$(STATIC_DIRS))

$(ENV)/.datalink-%:
	ln -snf $(shell pwd)/$* $(ENV)/$*
	@touch $@

unlink-dir-%:
	@test -f $(ENV)/.datalink-$* && rm -f $(ENV)/$* || true
	@rm -f $(ENV)/.datalink-$*

# wheels

$(WHL)-ok:
	mkdir -p $(WHL)
	virtualenv pkg-env $(QUIET)
	pkg-env/bin/pip install --upgrade pip setuptools wheel $(QUIET)
	pkg-env/bin/pip install --no-use-wheel --download $(WHL) pip setuptools wheel $(QUIET)
	pkg-env/bin/pip wheel --no-index --find-links=$(WHL) --use-wheel --wheel-dir=$(WHL) pip setuptools wheel $(QUIET)
	rm -rf pkg-env
	touch $(WHL)-ok

download: $(ENV) $(PIP_REQ)
	$(ENV)/bin/pip install --no-use-wheel --download $(WHL) --requirement $(PIP_REQ) $(QUIET)
	$(ENV)/bin/pip wheel --no-index --find-links=$(WHL) --use-wheel --wheel-dir=$(WHL) --requirement $(PIP_REQ) $(QUIET)

MANIFEST.in: setup.py
	./setup.py --static-dirs | sed 's/^/recursive-include / ; s/$$/ *.*/' > MANIFEST.in

release: $(ENV) MANIFEST.in release-pkg-$(PIP_NAME) 

release-pkg-%:
	rm -f $(WHL)/$*-$(shell $(PKG_BASE)/$*/setup.py --version)-*.whl
	cd $(PKG_BASE)/$* ; ./setup.py sdist --dist-dir=$(WHL) $(QUIET) 1>/dev/null 2>&1 
	$(ENV)/bin/pip wheel --no-index --find-links=$(WHL) --use-wheel --wheel-dir=$(WHL) $* $(QUIET)

#
# clean
#

clean:
	rm -rf $(ENV) tests/$(COVERAGE_OUTPUT_DIR) tests/$(COVERAGE_FILE) *.egg-info MANIFEST.in $(PIP_REQ) Makefile.in
	@find . -name '*.pyc' -delete

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

pep8:
	test -f $(PIP_NAME).py && $(ENV)/bin/pep8 $(PIP_NAME).py || $(ENV)/bin/pep8 $(PIP_NAME)

continuous: continuous-coverage

profile:
	cd tests ; ../$(ENV)/bin/python $(PY_OPTS) profile.py

# caching of some things that don't change a lot

Makefile.in: setup.py
	@echo "PIP_NAME = $(shell ./setup.py --name)" > Makefile.in
	@echo "PIP_REQ = requirements.txt" >> Makefile.in
	@echo "PKG = $(shell ./setup.py --repo-names)" >> Makefile.in
	@echo "PKG_BASE = $(shell readlink -f ..)" >> Makefile.in
	@echo "STATIC_DIRS = $(shell ./setup.py --static-dirs)" >> Makefile.in


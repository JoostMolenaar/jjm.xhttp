
include Makefile.inc

ENV = env

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

SITE_PACKAGES = $(ENV)/lib/python2.7/site-packages

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

runtime-live: $(ENV) deploy-pkgs unlink-code unlink-data deploy-code deploy-data

runtime-test: $(ENV) deploy-pkgs undeploy-code undeploy-data link-code link-data

$(ENV): 
	virtualenv $(ENV) $(QUIET)
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) 'distribute>=0.6.30' $(QUIET)
	$(ENV)/bin/pip install --upgrade --download-cache $(PIP_CACHE) --requirement $(PIP_REQ) $(QUIET)

#
# packages
#

deploy-pkgs: $(addprefix $(ENV)/lib/python2.7/site-packages/.egg-,$(PKG))

$(ENV)/lib/python2.7/site-packages/.egg-%:
	$(ENV)/bin/pip install --upgrade $(PKG_BASE)/$* $(QUIET)
	@find $(ENV) -name top_level.txt -path '*$*-*' -exec sh -c 'echo $* > {}' ';'
	@touch $@

#
# code
#

deploy-code:
	$(ENV)/bin/pip install --upgrade $(PKG_BASE)/$(PIP_NAME) $(QUIET)
	@find $(ENV) -name top_level.txt -path '*$(PIP_NAME)-*' -exec sh -c 'echo $(PIP_NAME) > {}' ';'

undeploy-code:
	$(ENV)/bin/pip uninstall --yes $(PIP_NAME) $(QUIET) || true

link-code:
	ln -snf $(shell pwd)/$(subst .,/,$(PIP_NAME)) $(SITE_PACKAGES)/$(subst .,/,$(PIP_NAME))

unlink-code:
	@test -L $(SITE_PACKAGES)/$(subst .,/,$(PIP_NAME)) && rm $(SITE_PACKAGES)/$(subst .,/,$(PIP_NAME)) || true

#
# data
#

deploy-data: $(addprefix deploy-dir-,$(STATIC_DIRS))

undeploy-data: $(addprefix undeploy-dir-,$(STATIC_DIRS))

deploy-dir-%:
	cp -r $* $(ENV)

undeploy-dir-%:
	@rm -rf $(ENV)/$*

link-data: $(addprefix link-dir-,$(STATIC_DIRS))

unlink-data: $(addprefix unlink-dir-,$(STATIC_DIRS))

link-dir-%:
	ln -snf $(shell pwd)/$(subst link-dir-,,$@) $(ENV)

unlink-dir-%:
	@test -L $(ENV)/$* && rm -f $(ENV)/$* || true

#
# clean
#

clean:
	rm -rf $(ENV)

really-clean: clean
	rm -rf $(PIP_CACHE)



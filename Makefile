PROJECT=pydantic_kitbash
UV_TEST_GROUPS := "--group=dev"
UV_LINT_GROUPS := "--group=lint" "--group=types"

include common.mk

.PHONY: format
format: format-ruff format-codespell format-prettier  ## Run all automatic formatters

.PHONY: lint
lint: lint-code lint-twine  ## Run all linters

.PHONY: lint-code
lint-code: lint-ruff lint-codespell lint-mypy lint-prettier lint-pyright lint-shellcheck  ## Run code-specific linters

.PHONY: pack
pack: pack-pip  ## Build all packages

.PHONY: publish
publish: publish-pypi  ## Publish packages

.PHONY: publish-pypi
publish-pypi: clean package-pip lint-twine  ## Publish Python packages to pypi
	uv tool run twine upload dist/*

# Find dependencies that need installing
APT_PACKAGES :=
ifeq ($(wildcard /usr/include/libxml2/libxml/xpath.h),)
APT_PACKAGES += libxml2-dev
endif
ifeq ($(wildcard /usr/include/libxslt/xslt.h),)
APT_PACKAGES += libxslt1-dev
endif
ifeq ($(wildcard /usr/share/doc/python3-venv/copyright),)
APT_PACKAGES += python3-venv
endif

# Used for installing build dependencies in CI.
.PHONY: install-build-deps
install-build-deps: install-lint-build-deps
ifeq ($(APT_PACKAGES),)
else ifeq ($(shell which apt-get),)
	$(warning Cannot install build dependencies without apt.)
	$(warning Please ensure the equivalents to these packages are installed: $(APT_PACKAGES))
else
	sudo $(APT) install $(APT_PACKAGES)
endif

# If additional build dependencies need installing in order to build the linting env.
.PHONY: install-lint-build-deps
install-lint-build-deps:


# Documentation targets (added for Starbase Sphinx docs scaffold).
.PHONY: setup-docs
setup-docs:
	uv venv docs/.venv --python 3.12 --clear
	uv pip install --python docs/.venv/bin/python -r docs/requirements.txt

.PHONY: docs
docs: setup-docs
	$(MAKE) -C docs html

.PHONY: docs-lint
docs-lint: setup-docs
	$(MAKE) -C docs spelling
	$(MAKE) -C docs woke

.PHONY: docs-linkcheck
docs-linkcheck: setup-docs
	$(MAKE) -C docs linkcheck

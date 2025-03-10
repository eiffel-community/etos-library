export GOBIN := $(CURDIR)/bin
export PYBUILD := $(CURDIR)/bin
export VENVDIR := $(CURDIR)/.buildenv
export BINDINGS := $(CURDIR)/src/etos_lib/bindings
export BUILD_MESSAGING := go build --buildmode=c-shared -o $(BINDINGS)/messaging/client.so ./cmd/messaging/main.go

BUILD_PYTHON = python -m build
VIRTUALENV = $(VENVDIR)/bin/python
GOLANGCI_LINT = $(GOBIN)/golangci-lint
GOLANGCI_LINT_VERSION = v1.64.6

.PHONY: all
all: check build

.PHONY: check
check: staticcheck test

.PHONY: test
test:
	go test -cover -timeout 30s -race $(shell go list ./... | grep -v "etos-library/test")

.PHONY: tidy
tidy:
	go mod tidy

.PHONY: check-dirty
check-dirty:
	$(GIT) diff --exit-code HEAD

.PHONY: staticcheck
staticcheck: $(GOLANGCI_LINT)
	$(GOLANGCI_LINT) run

.PHONY: clean
clean:
	$(RM) $(GOBIN)/*
	$(RM) -r $(BINDINGS)
	$(RM) -r $(VENVDIR)
	$(RM) -r dist

.PHONY: build
build: build-bindings build-python

.PHONY: build-bindings
build-bindings:
	$(BUILD_MESSAGING)

.PHONY: build-python
build-python: $(BUILD_PYTHON)
	$(BUILD_PYTHON)

$(GOLANGCI_LINT):
	mkdir -p $(dir $@)
	curl -sfL \
			https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh \
		| sh -s -- -b $(GOBIN) $(GOLANGCI_LINT_VERSION)

$(BUILD_PYTHON): $(VIRTUALENV)
	mkdir -p $(dir $@)
	$(VIRTUALENV) -m pip install build

$(VIRTUALENV):
	mkdir -p $(dir $@)
	pip install virtualenv
	python -m virtualenv $(VENVDIR)

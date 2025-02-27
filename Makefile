export GOBIN := $(CURDIR)/bin
export BINDINGS := $(CURDIR)/bindings
export BUILD_MESSAGING := go build --buildmode=c-shared -o $(BINDINGS)/stream/client.so ./cmd/messaging/main.go

GOLANGCI_LINT = $(GOBIN)/golangci-lint
GOLANGCI_LINT_VERSION = v1.52.2

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
	$(RM) -r $(BINDINGS)/*

.PHONY: build
build:
	$(BUILD_MESSAGING)

$(GOLANGCI_LINT):
	mkdir -p $(dir $@)
	curl -sfL \
			https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh \
		| sh -s -- -b $(GOBIN) $(GOLANGCI_LINT_VERSION)

# Copyright Axis Communications AB.
#
# For a full list of individual contributors, please see the commit history.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for logging setup."""

from unittest.mock import Mock

import pytest

from etos_lib.logging import logger


@pytest.fixture
def exporter_mocks(monkeypatch):
    """Replace exporter setup dependencies."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_LOGS_PROTOCOL", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_PROTOCOL", raising=False)
    grpc_exporter = Mock()
    http_exporter = Mock()
    grpc_exporter_class = Mock(return_value=grpc_exporter)
    http_exporter_class = Mock(return_value=http_exporter)
    processor_class = Mock()

    monkeypatch.setattr(logger, "OTLPLogExporter", grpc_exporter_class)
    monkeypatch.setattr(logger, "HttpOTLPLogExporter", http_exporter_class)
    monkeypatch.setattr(logger, "LoggerProvider", Mock())
    monkeypatch.setattr(logger, "BatchLogRecordProcessor", processor_class)
    monkeypatch.setattr(logger, "LoggingHandler", Mock())
    monkeypatch.setattr(logger, "LoggingInstrumentor", Mock())
    monkeypatch.setattr(logger, "logging", Mock(getLogger=Mock()))

    return grpc_exporter_class, http_exporter_class, processor_class, grpc_exporter, http_exporter


def test_setup_otel_logging_defaults_to_grpc(exporter_mocks):
    """Use the gRPC exporter when no protocol is configured."""
    grpc_class, http_class, processor_class, grpc_exporter, _ = exporter_mocks

    logger.setup_otel_logging(None, None)

    grpc_class.assert_called_once_with()
    http_class.assert_not_called()
    processor_class.assert_called_once_with(grpc_exporter)


def test_setup_otel_logging_uses_generic_http_protocol(exporter_mocks, monkeypatch):
    """Use the HTTP exporter when the generic protocol is HTTP/protobuf."""
    _, http_class, processor_class, _, http_exporter = exporter_mocks
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")

    logger.setup_otel_logging(None, None)

    http_class.assert_called_once_with()
    processor_class.assert_called_once_with(http_exporter)


def test_setup_otel_logging_logs_protocol_overrides_generic(exporter_mocks, monkeypatch):
    """Use the logs-specific protocol over the generic protocol."""
    grpc_class, http_class, processor_class, grpc_exporter, _ = exporter_mocks
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_LOGS_PROTOCOL", "grpc")

    logger.setup_otel_logging(None, None)

    grpc_class.assert_called_once_with()
    http_class.assert_not_called()
    processor_class.assert_called_once_with(grpc_exporter)


def test_setup_otel_logging_rejects_unsupported_protocol(exporter_mocks, monkeypatch):
    """Raise an explicit error for unsupported protocols."""
    grpc_class, http_class, _, _, _ = exporter_mocks
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "unsupported")

    with pytest.raises(ValueError, match="Unsupported OTLP logs protocol: unsupported"):
        logger.setup_otel_logging(None, None)

    grpc_class.assert_not_called()
    http_class.assert_not_called()

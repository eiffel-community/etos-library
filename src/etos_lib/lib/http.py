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
"""ETOS Library HTTP Client."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .debug import Debug

DEFAULT_RETRY = Retry(
    total=None,
    read=0,
    connect=10,  # With 1 as backoff_factor, will retry for 1023s
    status=10,  # With 1 as backoff_factor, will retry for 1023s
    backoff_factor=1,
    other=0,
    status_forcelist=Retry.RETRY_AFTER_STATUS_CODES,  # 413, 429, 503
)


class TimeoutHTTPAdapter(HTTPAdapter):
    """Adapter for automatically setting the default timeout on requests."""

    def __init__(self, *args, **kwargs):
        """Initialize timeout with default timeout set."""
        self.timeout = kwargs.get("timeout", Debug().default_http_timeout)
        if "timeout" in kwargs:
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, timeout=None, **kwargs):  # pylint:disable=arguments-differ
        """Set timeout if provided or add the default timeout when sending request."""
        if timeout is None:
            timeout = self.timeout
        return super().send(request, timeout=timeout, **kwargs)


class Http:
    """Utility class for HTTP requests."""

    def __init__(self, retry: Retry = DEFAULT_RETRY, timeout=None):
        """Initialize a requests session and set default retry adapter."""
        self.debug = Debug()
        if timeout is None:
            timeout = self.debug.default_http_timeout

        self.__session = requests.Session()
        self.adapter = TimeoutHTTPAdapter(max_retries=retry, timeout=timeout)
        self.__session.mount("https://", self.adapter)
        self.__session.mount("http://", self.adapter)

    def get(self, url, params=None, **kwargs):
        """HTTP GET requests via requests session."""
        return self.__session.get(url, params=params, **kwargs)

    def head(self, url, **kwargs):
        """HTTP HEAD requests via requests session."""
        return self.__session.head(url, **kwargs)

    def put(self, url, data=None, **kwargs):
        """HTTP PUT requests via requests session."""
        return self.__session.put(url, data=data, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """HTTP POST requests via requests session."""
        return self.__session.post(url, data=data, json=json, **kwargs)

    def patch(self, url, data=None, **kwargs):
        """HTTP PATCH requests via requests session."""
        return self.__session.patch(url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        """HTTP DELETE requests via requests session."""
        return self.__session.delete(url, **kwargs)

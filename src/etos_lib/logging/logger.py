# Copyright 2020 Axis Communications AB.
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
"""ETOS logger.

Example::

    from uuid import uuid4
    from etos_lib.logging.logger import setup_logging, get_logger

    setup_logging("myApp", "1.0.0", "production")
    logger = get_logger(__name__, str(uuid4()))
    logger.info("Hello!")
    >>> [2020-12-16 10:35:00][cb7c8cd9-40a6-4ecc-8321-a1eae6beae35] INFO: Hello!

"""
from pathlib import Path
import logging
import logging.config
from etos_lib.logging.filter import EtosFilter
from etos_lib.lib.debug import Debug
from etos_lib.lib.config import Config

DEFAULT_CONFIG = Path(__file__).parent.joinpath("default_config.conf")
DEFAULT_LOG_PATH = Debug().default_log_path
DEFAULT_LOG_PATH.parent.mkdir(exist_ok=True, parents=True)


def setup_logging(
    application, version, environment, filename=DEFAULT_CONFIG, output=DEFAULT_LOG_PATH
):
    """Set up basic logging.

    :param application: Name of application to setup logging for.
    :type application: str
    :param version: Version of application to setup logging for.
    :type version: str
    :param environment: Environment in which this application resides.
    :type environment: str
    :param filename: Filename of logging configuration.
    :type filename: str
    :param output: Output filename for logging to file.
    :type output: str
    """
    Config().set("log_filter", EtosFilter(application, version, environment))
    logging.config.fileConfig(filename, defaults={"logfilename": output})


def get_logger(name, identifier):
    """Get a logger adapter with attached identiifer.

    :param name: Name of logger to get.
    :type name: str
    :param identifier: Unique identifier to attach to logger.
    :type identifier: str
    :return: LoggerAdapter instance.
    :rtype: :obj:`logging.LoggerAdapter`
    """
    logger = logging.getLogger(name)
    logger.addFilter(Config().get("log_filter"))
    return logging.LoggerAdapter(logger, {"identifier": identifier})

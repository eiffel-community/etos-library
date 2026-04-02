============
ETOS Library
============

.. image:: https://img.shields.io/badge/Stage-Sandbox-yellow.svg
  :target: https://github.com/eiffel-community/community/blob/master/PROJECT_LIFECYCLE.md#stage-sandbox

ETOS (Eiffel Test Orchestration System) Library


Description
===========

A collection of common tools and code used throughout the whole ETOS project.


Installation
============

   pip install etos_lib


Contribute
==========

- Issue Tracker: https://github.com/eiffel-community/etos/issues
- Source Code: https://github.com/eiffel-community/etos-library


Running tests
=============

To run the tests, you will need to have a running instance of RabbitMQ. You can use Docker to run RabbitMQ locally:

   docker run -d --rm --name rabbitmq -p 5552:5552 -p 5672:5672 -e RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS='-rabbitmq_stream advertised_host localhost' rabbitmq:4.1

And enable the stream plugin with:

   docker exec rabbitmq rabbitmq-plugins enable rabbitmq_stream

Then you can run the tests with:

   pytest

Support
=======

If you are having issues, please let us know.
There is a mailing list at: etos-maintainers@googlegroups.com or just write an Issue.

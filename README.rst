Intertwine | Platform  |Build Status|_
======================================

.. |Build Status| image:: https://travis-ci.org/brianbruggeman/oogli.svg
.. _Build Status: https://travis-ci.org/brianbruggeman/oogli


Untangling Austin's Problems


This is the basic website for `Intertwine.io <http://Intertwine.io>`_
to help foster a community of individuals who are interested in specific
social problems within the context of geography regardless of their
background.

You can run with:

    $ docker-compose up

And then point your window to:

    $ open http://$(docker-machine ip)

We use (or WIP will use) the following tech stack:

   * `Ansible <https://www.ansible.com>`_
   * `Bootstrap <http://getbootstrap.com>`_
   * `Debian <https://www.debian.org>`_
   * `Docker <https://www.docker.com>`_
   * `Flask <http://flask.pocoo.org>`_ (moving to `Python 3 <>`_ soon)
   * `NginX <https://www.nginx.com>`_
   * `PostgreSQL 9.5 <https://www.postgresql.org>`_
   * `React <https://facebook.github.io/react/>`_
   * `Sass <http://sass-lang.com>`_
   * `Sphinx <http://www.sphinx-doc.org/>`_
   * `uWSGI <https://uwsgi-docs.readthedocs.io/en/latest/>`_

Installation
------------

Download Tools
~~~~~~~~~~~~~~

First make sure that you have the required pre-requisites:

   * `git <https://git-scm.com/downloads>`_
   * `virtualbox <https://www.virtualbox.org/wiki/Downloads>`_
   * `docker-toolkit <https://www.docker.com/products/docker-toolbox>`_


Download Image
~~~~~~~~~~~~~~

We have placed an image already up on docker hub that you can start
with.  To download:

    $ docker pull intertwineio/platform


Notes
~~~~~

    * If new libraries are added to the repository, you may need to rebuild
      your local copy of the docker instance:

          $ docker-compose build

    * Reminder: Docker containers are ephemeral.  Any changes you make in
      a running instance will be lost when you start a new docker container.

    * If using vmware, you may need to setup vmnet8 for forwarding ports when
      setting up for mobile.


Configuration
~~~~~~~~~~~~~

    * The basic docker image will use run.py to execute.  The options
      for this can be found within the file.  But to use a different
      set of options, you will need to use a more complex command:

        $ docker run -v $(pwd):/opt/repos/platform -p 80:8000 -it intertwineio/platform ./run.py <options here>

      For example, to run in outside of debug mode:

        $ docker run -v $(pwd):/opt/repos/platform -p 80:8000 -it intertwineio/platform ./run.py -p 8000


License
-------
Copyright 2016, Intertwine.io - All rights reserved


Contributions
-------------

Expectations
~~~~~~~~~~~~
Internally, we expect developers to use the following technologies to
help keep development consistent:

    Python:

    * py.test
    * tox
    * pep8
    * flake8  (line length ought to be 90ish)

We currently also use `travis <https://travis-ci.org/IntertwineIO/platform>`_
to help identify issues.

We also use `slack <http://intertwine.slack.com>`_ to communicate.

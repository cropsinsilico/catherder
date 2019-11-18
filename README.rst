catherder
=========

.. image:: https://img.shields.io/pypi/v/catherder.svg
    :target: https://pypi.python.org/pypi/catherder
    :alt: Latest PyPI version

.. image:: https://travis-ci.org/cropsinsilico/catherder.png
   :target: https://travis-ci.org/cropsinsilico/catherder
   :alt: Latest Travis CI build status

A tool for syncing different project management tools.

Usage
-----

The catherder methods can be accessed via the ``catherder`` command. Which can be call optionally with one or more project names. If a project name is not provided, the default project (as defined by the configuration file) will be assumed.

**Print catherder command help (including options)**
  ``$ catherder -h``

**Configure one or more projects**
  ``$ catherder [project1 ...] --configure``

**Updating the caches of Github and Smartsheet data**
  ``$ catherder [project1 ...]``

**Updating the Github issues based on changes to the Smartsheet**
  ``$ catherder [project1 ...] --github``

**Updating the Smartsheet based on changes to the Github issues**
  ``$ catherder [project1 ...] --smartsheet``

**Sorting the project cards on the Github project board**
  ``$ catherder [project1 ...] --sort-project-cards``

**Updating the persons assigned to the Github issues**
  ``$ catherder [project1 ...] --assignees``


Installation
------------

Requirements
^^^^^^^^^^^^

- Python (>= 2.7)
- PyGithub (installed automatically in instructions below)
- smartsheet-python-sdk (installed automatically in instructions below)
- A Github authentication token (see steps for creating one `here <https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line>`__)
- A Smartsheet authentication token (see steps for creating one `here <https://smartsheet-platform.github.io/api-docs/index.html#authentication-and-access-tokens>`__)

Pre-Installation Steps
^^^^^^^^^^^^^^^^^^^^^^

It is recommended, but not required, that you use anaconda to manage your Python environment in order to avoid issues with dependency conflicts.

#. Download and run the miniconda installer for your operating system from `here <https://docs.conda.io/en/latest/miniconda.html>`_
#. Create and activate a new conda environment with Python 3.6 and a name of your choosing from the terminal on Linux/OSX or Anaconda prompt on Windows::

     $ conda create -n <name> python=3.6
     $ conda activate <name>

#. Create a Github authentication `token <https://help.github.com/en/articles/creating-a-personal-access-token-for-the-command-line>`__ and save it to a secure location.
#. Create a Smartsheets authenticaiton `token <https://smartsheet-platform.github.io/api-docs/index.html#authentication-and-access-tokens>`__ and save it to a secure location.

Installation Steps
^^^^^^^^^^^^^^^^^^

From PyPI
~~~~~~~~~

Enter the following command from your terminal prompt (or Anaconda promp on Windows).::

     $ pip install catherder

From Source
~~~~~~~~~~~

#. Clone the catherder repository.::

     $ git clone https://github.com/cropsinsilico/catherder.git

#. Enter the local repository directory and install from source in development mode.::

     $ cd catherder
     $ pip install -e .

From conda-forge
~~~~~~~~~~~~~~~~

The package has not yet been uploaded to conda-forge.

Post-Installation Steps
^^^^^^^^^^^^^^^^^^^^^^^

After installation is complete, you can run the configuration to set up a project.::

  $ catherder --configure

This will ask you to select a default project name and will ask you for information
about the project that is required to complete the entry in the config file including
your Github and Smartsheet authentication tokens and the names of the associated
Github repository, Github project, and Smartsheet sheet.

Steps to Update
^^^^^^^^^^^^^^^

From PyPI
~~~~~~~~~

Enter the following command from your terminal prompt (or Anaconda prompt on Windows).::

     $ pip install catherder -U

From Source
~~~~~~~~~~~

Enter the following command from your terminal prompt (or Anaconda prompt on Windows) from inside the cloned catherder repository.::

     $ git pull

From conda-forge
~~~~~~~~~~~~~~~~

The package has not yet been uploaded to conda-forge.

Licence
-------

This software is free to use and resdistribute under the MIT license.

Authors
-------

`catherder` was written by `Meagan lang <langmm.astro@gmail.com>`_.

Todo
----

- Make package general (e.g. 'Task Name' column coded in config file)
- Create method for getting contacts from Smartsheet
- Command for rolling back to a previous cache entry
- Directions for deploying as heroku app

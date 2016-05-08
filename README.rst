===========
git-bigfile
===========

This project is deprecated.
I used it for a while and it's still working but I won't update it.
I switched to git-lfs_ and recommend it especially if you use Gitlab_.


git-bigfile is a port to python / fork of Scott Chacon git-media_.
It allows you to use Git with large files without storing the file in Git itself.

.. _git-media: https://github.com/schacon/git-media
.. _git-lfs: https://git-lfs.github.com
.. _Gitlab: https://about.gitlab.com

Configuration
-------------

Configure the filter and transport
++++++++++++++++++++++++++++++++++

By running::

    $ git bigfile config [--global]

Or manually:

First setup the attributes filter settings::

    (once after install)
    $ git config --global filter.bigfile.clean "git-bigfile filter-clean"
    $ git config --global filter.bigfile.smudge "git-bigfile filter-smudge"

Next you need to configure git to tell it where you want to store the large files.
There are two options:

1. Storing locally in a filesystem path
2. Storing remotely via sftp (should work with any SSH server - requires
   paramiko)

Here are the relevant sections that should go either in ~/.gitconfig (for global settings)
or in clone/.git/config (for per-repo settings)::

    [git-bigfile]
        transport = <local|sftp>

    # settings for local transport
    [git-bigfile "local"]
        path = <local_filesystem_path>

    # settings for sftp transport
    [git-bigfile "sftp"]
        hostname = <host>
        username = <user>
        path = <path_on_remote_server>

All sftp settings (except path) will be passed to paramiko.SSHClient connect
method. You can set: port, password, pkey, key_filename, timeout... Refer to
paramiko API.


Setup the .gitattributes file to map extensions to the filter
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    (in repo - once)
    $ echo "*.tar.gz filter=bigfile -crlf" > .gitattributes

Staging files with those extensions will automatically copy them to the
bigfile cache area (.git/bigfile) until you run 'git bigfile push' wherein they
are uploaded.  Checkouts that reference bigfile you don't have yet will try to
retrieve them from cache, otherwise they are downloaded when you run 'git
bigfile pull'.


Usage
-----

To configure the filter and/or the transport to use::

    $ git bigfile config

Then::

    (in repo - repeatedly)
    $ (hack, stage, commit)

To push to the server any committed bigfile::

    $ git bigfile push

You can also check the status of your bigfiles via::

    $ git bigfile status

Which will show you files that are waiting to be uploaded and how much data
that is. If you want to delete the local cache of uploaded bigfiles, run::

    $ git bigfile clear

You can add a bigfile that doesn't match the extensions defined in
the .gitattributes by running::

    $ git bigfile add <huge_file>

Which will add <huge_file> to .gitattributes and to the index.

To expand a bigfile you don't have locally, run::

    $ git bigfile pull


Installing
----------

git-bigfile requires Python 2.5, 2.6 or 2.7.
It has been tested on MacOS X and linux.

To install, run::

    $ pip install paramiko (to use sftp transport)
    $ pip install git-bigfile


Copyright
---------

Original work Copyright (c) 2009 Scott Chacon.
Modified work Copyright (c) 2012-2013 Benjamin Bertrand.
See LICENSE for details.

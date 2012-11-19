# -*- coding: utf-8 -*-
"""
gitbigfile command module

This module defines git-bigfile commands.
"""

import os
import sys
import hashlib
import tempfile
import re
import errno
import shutil
from gitbigfile import util, transport

SHA_FILE_SIZE = 41
SHA_PATTERN = re.compile('^[0-9a-fA-F]+$')


def config(global_flag=False):
    """Function to help configure git-bigfile filter options"""
    if not global_flag:
        # Check that we are in a git repository
        # Following command will exit if it fails
        util.get_repo_dir()
    # filter options
    options = [('filter.bigfile.clean', 'git-bigfile filter-clean'),
              ('filter.bigfile.smudge', 'git-bigfile filter-smudge')]
    # transport options
    valid_transports = transport.MANDATORY_OPTIONS.keys()
    while True:
        t = raw_input('Enter transport [%s]: ' %
                            '|'.join(valid_transports))
        if t in valid_transports:
            options.append(('git-bigfile.transport', t))
            break
        else:
            print 'Invalid transport %s' % t
    for t_option in transport.MANDATORY_OPTIONS[t]:
        value = raw_input('Enter %s %s: ' % (t, t_option))
        options.append(('git-bigfile.%s.%s' % (t, t_option), value))
    util.set_git_options(options, global_flag)


class GitBigfile(object):

    def __init__(self):
        self._objects = util.get_bigfile_dir('objects')
        self._repo_path = util.get_repo_dir()
        self._config = util.get_git_config()
        self._transport = self._get_transport()

    def _get_relpath(self, filename):
        """Return filename relative file path from the current dir"""
        full_path = os.path.join(self._repo_path, filename)
        return os.path.relpath(full_path)

    def _get_transport(self):
        """Return the transport class to use"""
        # Get the transport to use
        try:
            t = self._config['git-bigfile.transport']
        except KeyError:
            sys.stderr.write('git-bigfile.transport is not set\n')
            sys.exit(1)
        # Get and check all transport options
        kwargs = dict([(key.split('.')[-1], value) for key, value in self._config.items()
                        if key.startswith('git-bigfile.%s.' % t)])
        try:
            mandatory_options = frozenset(transport.MANDATORY_OPTIONS[t])
        except KeyError:
            sys.stderr.write('Unknown transport: %s\n' % t)
            sys.stderr.write('Valid transports: %s\n' %
                              ' '.join(transport.MANDATORY_OPTIONS.keys()))
            sys.exit(1)
        options = frozenset(kwargs.keys())
        if not mandatory_options.issubset(options):
            missing_options = mandatory_options - options
            sys.stderr.write('Missing option(s) for %s transport:\n' % t)
            sys.stderr.write('\n'.join(['git-bigfile.%s.%s' % (t, option)
                                           for option in missing_options]))
            sys.stderr.write('\n')
            sys.exit(1)
        t_class = t[0].upper() + t[1:]
        return getattr(transport, t_class)(**kwargs)

    def _check_stdin(self):
        """Check if the data received on stdin is a sha file

        Return a tuple (data read, sha) or (data read, None)
        """
        data = sys.stdin.read(64)
        sha = data.strip()
        if len(data) == SHA_FILE_SIZE and SHA_PATTERN.match(sha):
            return (data, sha)
        else:
            return (data, None)

    def filter_clean(self):
        """The clean filter is run when a bigfile is staged.

        It replaces the bigfile received on stdin with its SHA.
        """
        data, sha = self._check_stdin()
        # if data is a sha, just output (this is an unexpanded bigfile)
        # otherwise read in buffered chunks of the data
        # calculating the SHA and copying to a temporary file
        if sha is None:
            temp = tempfile.NamedTemporaryFile(dir=util.get_bigfile_dir('tmp'), delete=False)
            hashfunc = hashlib.sha1()
            while True:
                hashfunc.update(data)
                temp.write(data)
                data = sys.stdin.read(4096)
                if not data:
                    break
            # Calculate the SHA of the data
            sha = hashfunc.hexdigest()
            # Rename the temporary file
            temp.close()
            bigfile = os.path.join(self._objects, sha)
            os.rename(temp.name, bigfile)
            sys.stderr.write('Saving bigfile: %s\n' % sha)
        print sha

    def filter_smudge(self):
        """The smudge filter is run on checkout.

        It tries to replace the SHA file with the corresponding
        bigfile.
        """
        data, sha = self._check_stdin()
        if sha:
            # Try to recover the bigfile
            bigfile = os.path.join(self._objects, sha)
            if os.path.isfile(bigfile):
                sys.stderr.write('Recovering bigfile: %s\n' % sha)
                with open(bigfile, 'rb') as f:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        sys.stdout.write(data)
            else:
                sys.stderr.write('Saving placeholder (bigfile not in cache): %s\n' % sha)
                print sha
        else:
            # If it is not a 40 character long hash, just output
            sys.stderr.write('Unknown git-bigfile format\n')
            while True:
                sys.stdout.write(data)
                data = sys.stdin.read(4096)
                if not data:
                    break

    def _get_bigfiles_status(self):
        """Return the lists of bigfiles to_expand, expanded and deleted as a tuple

        Each list includes for each bigfile the filename, sha, is_pushed bool and size
        """
        to_expand = []
        expanded = []
        deleted = []
        tree_entries = util.run('git ls-tree -l -r HEAD --full-tree').split('\n')
        bigfiles = [(entry.split()[-1], entry.split()[2])
                    for entry in tree_entries if entry.split()[-2] == str(SHA_FILE_SIZE)]
        pushed_files = self._transport.pushed()
        for filename, blob in bigfiles:
            relpath = self._get_relpath(filename)
            sha = util.run('git show %s' % blob)
            # Check is this is a sha (size is already correct)
            if not SHA_PATTERN.match(sha):
                # Not a bigfile sha
                continue
            is_pushed = sha in pushed_files
            try:
                size = os.path.getsize(relpath)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    # No such file or directory: file was deleted
                    deleted.append((relpath, sha, is_pushed, None))
                else:
                    raise
            else:
                if size == SHA_FILE_SIZE:
                    to_expand.append((relpath, sha, is_pushed, None))
                else:
                    expanded.append((relpath, sha, is_pushed, size))
        return (to_expand, expanded, deleted)

    def _get_unpushed_files(self):
        """Return the list of unpushed files"""
        pushed_files = self._transport.pushed()
        cached_files = os.listdir(self._objects)
        unpushed_files = frozenset(cached_files) - frozenset(pushed_files)
        return unpushed_files

    def status(self):
        """Display the status of all bigfiles"""
        to_expand, expanded, deleted = self._get_bigfiles_status()
        util.print_status('Unexpanded bigfiles', to_expand)
        util.print_status('Expanded bigfiles', expanded)
        util.print_status('Deleted bigfiles', deleted)

    def pull(self):
        """Expand bigfiles by pulling them from the server if needed"""
        to_expand, expanded, deleted = self._get_bigfiles_status()
        for filename, sha, is_pushed, size in to_expand:
            cache_file = os.path.join(self._objects, sha)
            if not os.path.isfile(cache_file):
                if self._transport.exists(sha):
                    print 'Downloading %s : %s' % (sha[:8], filename)
                    self._transport.get(sha, cache_file)
            try:
                print 'Expanding %s : %s' % (sha[:8], filename)
                shutil.copy(cache_file, filename)
            except IOError:
                print 'Could not get %s' % filename
            else:
                # Update the index
                util.run('git add %s' % filename)

    def push(self):
        """Push cached files to the server"""
        for sha in self._get_unpushed_files():
            print 'Uploading %s' % sha[:8]
            local_file = os.path.join(self._objects, sha)
            self._transport.put(local_file, sha)

    def clear(self):
        """Remove pushed files from cache"""
        pushed_files = self._transport.pushed()
        for sha in pushed_files:
            cache_file = os.path.join(self._objects, sha)
            try:
                os.unlink(cache_file)
                print 'Removing %s from cache' % sha[:8]
            except OSError as e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise

    def add(self, filename):
        """Add filename to .gitattributes and to the index"""
        if os.path.isfile(filename):
            gitattributes = util.get_gitattributes()
            base_name = os.path.basename(filename)
            print 'Adding %s to %s' % (base_name, gitattributes)
            with open(gitattributes, 'a') as f:
                f.write('%s filter=bigfile -crlf\n' % base_name)
            util.run('git add %s' % gitattributes)
            print 'Adding %s to the index' % filename
            util.run('git add %s' % filename)
        else:
            sys.stderr.write('%s did not match any file\n' % filename)
            sys.exit(1)

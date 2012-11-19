# -*- coding: utf-8 -*-
"""
gitbigfile util module

This module defines utility functions.
"""

import os
import sys
import shlex
import subprocess


def run(cmd):
    """Run the shell command and return the result"""
    args = shlex.split(cmd)
    try:
        result = subprocess.check_output(args)
    except subprocess.CalledProcessError as e:
        sys.stderr.write(e.output)
        sys.exit(e.returncode)
    else:
        return result.strip()


def get_repo_dir():
    """Return the current git repo absolute path or exit"""
    return run('git rev-parse --show-toplevel')


def get_bigfile_dir(name):
    """Return the path of the bigfile directory

    Directory is created if it doesn't exist
    """
    git_dir = run('git rev-parse --git-dir')
    bigfile_dir = os.path.join(git_dir, 'bigfile', name)
    if not os.path.isdir(bigfile_dir):
        os.makedirs(bigfile_dir)
    return bigfile_dir


def get_git_config():
    """Return a dictionary with all git options"""
    config = run('git config --list')
    return dict([item.split('=') for item in config.split('\n')])


def get_gitattributes():
    """Return .gitattibutes path"""
    return os.path.join(run('git rev-parse --show-cdup'), '.gitattributes')


def set_git_options(options, global_flag=False):
    """Add the given git options to the current repo or global config

    Option is only added if it's not already defined
    (with the same value)
    """
    if global_flag:
        flags = '--global'
    else:
        flags = ''
    config = get_git_config()
    for option, value in options:
        if option not in config or config[option] != value:
            run('git config %s %s "%s"' % (flags, option, value))
            print '%s set to "%s"' % (option, value)
        else:
            print '%s already set to "%s"' % (option, value)


def fmt_size(num):
    """Return the size in human readable format"""
    for x in ['B', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def print_status(title, bigfiles):
    """Pretty print the status of bigfiles"""
    if bigfiles:
        print '== %s ==' % title
        for filename, sha, is_pushed, size in bigfiles:
            if size:
                size_str = '(%s)' % fmt_size(size)
            else:
                size_str = ''
            if is_pushed:
                status = 'pushed  '
            else:
                status = 'unpushed'
            print '   %s %s %s %s' % (status, size_str.ljust(10), sha[:8], filename)

# -*- coding: utf-8 -*-
"""
gitbigfile transport module

This module defines git-bigfile transports.
Each transport should implement the methods defined in the Transport class.
"""

import os
import sys
import errno
import shutil
try:
    import paramiko
    PARAMIKO = True
except ImportError:
    PARAMIKO = False

MANDATORY_OPTIONS = {'local': ['path'],
                     'sftp': ['hostname', 'username', 'path']
                    }


class Transport(object):
    """A Transport subclass should implement the following methods"""

    def get(self, sha, local_file):
        """Copy the sha file from the server"""
        raise NotImplementedError

    def put(self, local_file, sha):
        """Copy the the local file to the server"""
        raise NotImplementedError

    def exists(self, sha):
        """Return True if the sha file exists on the server"""
        raise NotImplementedError

    def pushed(self):
        """Return the list of pushed files"""
        raise NotImplementedError


class Local(Transport):

    def __init__(self, path):
        self.path = path

    def _get_file_path(self, sha):
        """Return the path of sha on the server"""
        return os.path.join(self.path, sha)

    def get(self, sha, local_file):
        """Copy the sha file from the server"""
        shutil.copy(self._get_file_path(sha), local_file)

    def put(self, local_file, sha):
        """Copy the the local file to the server"""
        shutil.copy(local_file, self._get_file_path(sha))

    def exists(self, sha):
        """Return True if the sha file exists on the server"""
        return os.path.isfile(self._get_file_path(sha))

    def pushed(self):
        """Return the list of pushed files"""
        return os.listdir(self.path)


class Sftp(Transport):

    def __init__(self, path, **ssh_kwargs):
        self.sshclient = None
        self.sftpclient = None
        self.path = path
        self.ssh_kwargs = ssh_kwargs
        if not PARAMIKO:
            sys.stderr.write('paramiko is required to use sftp transport\n')
            sys.exit(1)

    def _connect(self):
        """Create a ssh client and a sftp client"""
        if self.sftpclient is None:
            self.sshclient = paramiko.SSHClient()
            self.sshclient.load_system_host_keys()
            self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.sshclient.connect(**self.ssh_kwargs)
            self.sftpclient = self.sshclient.open_sftp()

    def _get_file_path(self, sha):
        """Return the path of sha on the server"""
        return os.path.join(self.path, sha)

    def get(self, sha, local_file):
        """Copy the sha file from the server"""
        self._connect()
        remote_file = self._get_file_path(sha)
        self.sftpclient.get(remote_file, local_file)

    def put(self, local_file, sha):
        """Copy the the local file to the server"""
        self._connect()
        remote_file = self._get_file_path(sha)
        self.sftpclient.put(local_file, remote_file)

    def exists(self, sha):
        """Return True if the sha file exists on the server"""
        self._connect()
        remote_file = self._get_file_path(sha)
        try:
            self.sftpclient.stat(remote_file)
        except IOError, e:
            if e.errno == errno.ENOENT:
                return False
            raise
        else:
            return True

    def pushed(self):
        """Return the list of pushed files"""
        self._connect()
        return self.sftpclient.listdir(self.path)

    def close(self):
        """Close the sftp and ssh connection"""
        if self.sftpclient is not None:
            self.sftpclient.close()
            self.sshclient.close()
            self.sftpclient = None

    def __del__(self):
        """Attempt to clean up if the connection was not closed"""
        self.close()

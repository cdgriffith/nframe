#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Copyright (c) 2014 Chris Griffith - MIT License
"""
__version__ = '0.8-alpha'

from time import sleep
import json
from math import ceil
import os
import signal
import tempfile
import sys
from functools import partial, wraps
from distutils.version import LooseVersion

try:
    from socketserver import BaseRequestHandler, TCPServer
except ImportError:
    from SocketServer import BaseRequestHandler, TCPServer


class LockError(Exception):
    """ Custom error class for errors occurring within the Lock class """
    pass


class ServerError(Exception):
    """ Custom error class for errors occurring within the Server class """
    pass

_bytes = partial(bytes, encoding='utf-8') if sys.version_info > (3,) else \
    lambda x: str(x).encode('utf-8')

LOCK_FILE = os.path.join(tempfile.gettempdir(), "nframe.pid")
DATA_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         "data.json")


class Lock(object):
    """
    Simply PID based file lock context manager. Can cleanup on SIGTERM.
    """
    def __init__(self, pid_file=LOCK_FILE, timeout=0,
                 safe=False, cleanup_on_term=False):
        self.pid_file = pid_file
        self.pid = os.getpid()
        self.timeout = timeout
        self.cleanup = cleanup_on_term
        self.safe = safe
        assert isinstance(self.timeout, int) and self.timeout >= 0

    def __enter__(self):
        """
        Start the lock as a context manager, protecting a file from modification.
        """
        self.acquire()
        if self.cleanup:
            signal.signal(signal.SIGTERM, self.__exit__)

    #noinspection PyUnusedLocal
    def __exit__(self, exctype, value, tb):
        """
        On release of a context manager release the lock
        """
        self.release()

    def acquire(self):
        """
        If the file is not currently in use set the lock
        """
        while self.timeout >= 0:
            try:
                if os.path.exists(self.pid_file):
                    self.check_lock()
                else:
                    with open(self.pid_file, "wb") as pid_data:
                        pid_data.write(_bytes(str("{0}\n".format(self.pid))))
                    os.chmod(self.pid_file, 0o0444)
                break
            except LockError:
                self.timeout -= 1
                sleep(1)
        else:
            raise LockError()

    def release(self):
        """
        Safely release the lock file
        """
        try:
            self.check_lock(release=True)
        except (OSError, IOError):
            print("Pid file has been removed!")
            if self.safe:
                raise LockError("Unsafe exit, pid file not found")
        try:
            os.chmod(self.pid_file, 0o0777)
            os.unlink(self.pid_file)
        except OSError:
            print("Could not delete pid file, was already removed!")
            if self.safe:
                raise LockError("Unsafe exit, pid file not found")

    def check_lock(self, release=False):
        """
        Determine if lock is currently in use
        """
        with open(self.pid_file, "r") as pid_data:
            pid = pid_data.readline().encode('utf-8').rstrip()
        try:
            assert int(pid) >= 0
        except (ValueError, AssertionError):
            raise LockError("File is improperly formatted, cannot read")
        if int(pid) != self.pid:
            raise LockError("JSON files locked \
by process {0}".format(str(pid)))
        elif int(pid) == self.pid and self.safe and not release:
            raise LockError("Already obtained lock, safe mode prohibited")

    def force_release(self):
        """
        Forcefully remove the lock file
        """
        self.safe = False
        try:
            os.chmod(self.pid_file, 0o0777)
            os.unlink(self.pid_file)
            return True
        except OSError:
            print("Could not remove pid file")
        return False
            

class JSONModification(object):
    """Class for reusable use of saving and loading data from JSON files"""

    def __init__(self, data_file=DATA_FILE, pid_file=LOCK_FILE, timeout=0):
        self.data = {}
        self.data_file = data_file
        self.lock = None
        self.lock_file = pid_file
        self.timeout = timeout

    def __enter__(self):
        """
        Use the JSON modification as a context manager to automatically lock
        the file and load the data (creating it if it does not yet exist)
        """
        self.lock = Lock(self.lock_file, timeout=self.timeout)
        self.lock.acquire()
        self._load()
        self._save()
        return self

    #noinspection PyUnusedLocal
    def __exit__(self, exctype, value, tb):
        """
        Save the data and close exclusive access to the file
        """
        self._load()
        self._save()
        self.lock.release()

    def _save(self):
        """ Save data to local json file so it is persistent."""
        file_data = dict(data=self.data, version=__version__)
        try:
            with open(self.data_file, "w") as data_file:
                data_file.write(str(json.dumps(file_data)))
        except (ValueError, IOError):
            raise ServerError("Data could not be saved")

    def _load(self):
        """ Retrieve data from the supplied json file."""

        if not os.path.exists(self.data_file):
            return

        with open(self.data_file, "r") as file_data:
            file_data = json.loads(file_data.read())

        if file_data['version'] != __version__:
            file_data = self._upgrade_path(file_data)
        self.data = file_data['data']

    @staticmethod
    def _upgrade_path(data):
        """ Function in place for later use, when JSON objects may change and
        have to undergo a change from previous versions.
        """
        if LooseVersion(data['version']) < LooseVersion(__version__):
            # update data
            pass
        return data


def autosave(func):
    """ This decorator will take in class objects and invoke their load
    method running them, and then save method afterwards. This makes sure that
    all stored in attributes and on the file system are synchronized.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self._load()
        response = func(self, *args, **kwargs)
        self._save()
        return response
    return wrapper

    
class Server(BaseRequestHandler, JSONModification):
    """ Server is a custom Request Handler. This will handle all incoming
    requests and can store the information in local JSON files for persistent
    storage.
    """

    def __init__(self, request, client_address, tcpserver):
        """ Create the CTFServer class and set up custom class attributes."""
        self.data = {}
        self.data_file = DATA_FILE
        self.message = None
        self._load()
        self._save()
        super(Server, self).__init__(request, client_address, tcpserver)

    def _read(self):
        """ Retrieve incoming information from the socket. This will
        deal with large data chunks by reading them in sections and
        concatenating them back together.
        """
        data = self.request.recv(1024).decode('utf-8')
        recv = json.loads(data)
        self.request.send("ok".encode("utf-8"))
        incoming = ""
        for sec in range(0, recv['sections']):
            incoming += self.request.recv(1024).decode('utf-8')
        return json.loads(incoming)

    def _send(self, data):
        """ Write information to the socket. Break up all incoming data into
        blocks of 1024 bytes before sending.
        """
        write_data = _bytes(json.dumps(data))
        data_sections = int(ceil(len(write_data) / 1024.0))
        sec_data = json.dumps({'sections': data_sections})
        self.request.send(_bytes(sec_data))
        self.request.recv(2)
        for sec in range(0, data_sections):
            self.request.send(write_data[(1024 * sec):(1024 * (sec + 1))])

    @autosave
    def handle(self):
        """
        handle()
        Overloaded handle function to communicate with client.
        """
        # Read data in
        incoming = self._read()
        command = incoming['command']
        data = incoming['data']
        # do something
        if command == "get data":
            # Return all current data
            return self._send(self.data)
        else:
            # update data dict and return incoming as in
            self.data.update(data)
            return self._send(incoming)


class Data(JSONModification):
    """ Manage data in a local JSON file. """
    def __init__(self, data_file=DATA_FILE, **kwargs):
        super(Data, self).__init__(data_file=data_file, **kwargs)

    @autosave
    def export_data(self, filename="export.json"):
        """
        export_data(filename)
        Save all data to a file that can be imported.
        """
        file_data = {"version": __version__, "data": self.data}

        with open(filename, "w") as data_file:
            data_file.write(str(json.dumps(file_data, indent=2)))

    @autosave
    def import_data(self, filename="export.json"):
        """
        import_data(filename)
        Add all data in the given file to the data set.
        """
        with open(filename, "r") as data_file:
            file_data = json.loads(data_file.read())
        self.data.update(file_data['data'])

    @autosave
    def add_data(self, **kwargs):
        """
        add_data()
        Update the current data dictionary with new information provided
        """
        self.data.update(kwargs)

    @autosave
    def remove_data(self, *args):
        """
        remove_data()
        Removes the key:value pair based on the provided key(s) in a list
        """
        for arg in args:
            del self.data[arg]


def main(*args):
    """ Function invoked when the server is run as a script"""
    import argparse

    desc = "nframe server"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("-i", "--ip", default="0.0.0.0",
                        help="IP address of server")
    parser.add_argument("-p", "--port", default=7645,
                        help="Port of server")
    parser.add_argument("--import", action="store",
                        default=False, dest="import_file",
                        help="Import data before starting server")
    parser.add_argument("--export", action="store",
                        default=False, dest="export_file",
                        help="Export data then exits")
    parser.add_argument("--force-unlock", action="store_true", default=False,
                        help="Remove lock file without discretion",
                        dest="force_unlock")
    parser.add_argument("--exit", action="store_true", default=False,
                        help="perform action then exit (don't run server)",
                        dest="exit")


    pargs = parser.parse_args(args) if args else parser.parse_args()

    if pargs.force_unlock:
        Lock().force_release()

    if pargs.import_file:
        with Data(timeout=5) as import_data:
            import_data.import_data(pargs.import_file)

    if pargs.export_file:
        with Data(timeout=5) as export_data:
            export_data.export_data(pargs.export_file)
        return

    server = TCPServer((pargs.ip, pargs.port), Server)
    if pargs.exit:
        return pargs
    with Lock(timeout=5):
        try:
            server.serve_forever()
        except (SystemError, SystemExit, KeyboardInterrupt):
            server.server_close()


if __name__ == '__main__':
    main()

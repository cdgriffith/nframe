#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Copyright (c) 2014 Chris Griffith - MIT License
"""

__version__ = '0.8-alpha'

import socket
from json import dumps, loads
from math import ceil
import sys
from functools import partial

if sys.version_info > (3,):
    _bytes = partial(bytes, encoding='utf-8')
    unicode = str
else:
    _bytes = lambda x: str(x).encode('utf-8')


class Client():
    def __init__(self, server="localhost", port=7645, **kwargs):
        self.server = server
        self.port = port
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _connect(self):
        """Initiate the TCP socket connection to the server. """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server, self.port))

    def _close(self):
        """ Close the tcp socket. """
        self.socket.close()

    def _send(self, data):
        """ Send and receive information from the server. This will automate
        the process of breaking large data into chunks before sending.

        :param data: Dictionary to send to the server.
        :return: Returned result from the server.
        """
        write_data = _bytes(dumps(data))
        data_sections = int(ceil(len(write_data) / 1024.0))
        sec_data = {'sections': data_sections}
        self.socket.send(_bytes(dumps(sec_data)))
        if self.socket.recv(2).decode("utf-8") != "ok":
            raise Exception('Server raised exception')
        for index in range(0, data_sections):
            self.socket.send(write_data[(1024 * index):(1024 * (index + 1))])
        recv = loads(self.socket.recv(1024).decode('utf-8'))
        self.socket.send(_bytes("ok"))
        incoming = ""
        for index in range(0, recv['sections']):
            incoming += self.socket.recv(1024).decode('utf-8')
        return loads(incoming)

    def message(self, data):
        """
        A example function that shows how to send data to the server and receive data back.
        """
        try:
            self._connect()
        except socket.error:
            print "could not connect"
        else:
            print self._send(data)
        finally:
            self._close()

if __name__ == '__main__':
    sys.stderr.write("\nYou can't run me!\n\n\
Open a python interpreter and type in:\n\
from nframe_client import Client\n\n")
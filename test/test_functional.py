#!/usr/bin/env python
#-*- coding: utf-8 -*-
from unittest import TestCase
import os
from nframe_server import TCPServer, Server, Data, Lock, DATA_FILE
from nframe_client import Client
from threading import Thread
from multiprocessing.pool import ThreadPool


loc = os.path.abspath(os.path.dirname(__file__))

lock_file = os.path.join(loc, "test.pid")
server_port = 6758
server = TCPServer(("localhost", server_port), Server)
max_runs = 50


class Interaction(TestCase):

    lock = None

    @classmethod
    def setUpClass(cls):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)
        if os.path.exists(DATA_FILE):
            os.unlink(DATA_FILE)
        with Lock(timeout=5, pid_file=lock_file):
            mod = Data(DATA_FILE)
            mod.add_data(test_data=['test data 1', 'test data 2'])
        cls.lock = Lock(timeout=5, pid_file=os.path.join(loc, "test.pid"))
        cls.lock.acquire()
        cls.process = Thread(target=cls.run_server)
        cls.process.isDaemon()
        cls.process.start()

    @classmethod
    def tearDownClass(cls):
        server.shutdown()
        cls.lock.release()
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)
        if os.path.exists(DATA_FILE):
            os.unlink(DATA_FILE)

    @staticmethod
    def run_server():
        server.serve_forever()

    @staticmethod
    def test_message(i=0):
        conn = Client(port=server_port)
        example_data = dict(new_test_data="Example data {0}".format(i))
        msg = conn.message(example_data)
        assert "command" in msg
        assert example_data == msg['data']

    @staticmethod
    def test_get_data():
        conn = Client(port=server_port)
        msg = conn.get_data()
        assert "test_data" in msg, msg

    @staticmethod
    def test_lots_of_connections():
        conns = []
        for i in range(0, max_runs):
            conns.append(Client(port=server_port))

        for a in range(2, max_runs):
            assert conns[a].message(dict(num=a))['data'] == dict(num=a)
            assert 'num' in conns[a-1].get_data()

    def test_simultaneous_connections(self):
        pool = ThreadPool(10)
        pool.map(self.test_message, range(max_runs, max_runs*2))

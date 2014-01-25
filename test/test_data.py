#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nframe_server import Data, Lock
import os
from json import loads, dumps
import sys
from unittest import TestCase

loc = os.path.abspath(os.path.dirname(__file__))

data_file = os.path.join(loc, "data.json")
lock_file = os.path.join(loc, "test.pid")

def _bytes(sti, enc='utf-8'):
    return bytes(sti, enc) if sys.version_info > (3,) else str(sti).encode(enc)


class TestUsers(TestCase):

    @classmethod
    def setUpClass(cls):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)
        if os.path.exists(data_file):
            os.unlink(data_file)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)
        if os.path.exists(data_file):
            os.unlink(data_file)

    def setUp(self):
        with Data(data_file, pid_file=lock_file): pass

    def tearDown(self):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)
        if os.path.exists(data_file):
            os.unlink(data_file)

    def test_add_user(self):
        with Data(data_file, pid_file=lock_file) as users:
            users.add_data(new_data='test', test_data=['hi'])

        with Lock(pid_file=lock_file, timeout=3):
            with open(data_file, 'rb') as test_data:
                data = loads(test_data.read().decode('utf-8'))
                assert "hi" in data['data']['test_data'], data
                assert "test" == data['data']['new_data']
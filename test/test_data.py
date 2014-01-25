#!/usr/bin/env python
# -*- coding: utf-8 -*-
from nframe_server import Data, Lock, main
import os
from json import loads, dumps
import sys
from unittest import TestCase
from functools import partial

loc = os.path.abspath(os.path.dirname(__file__))

data_file = os.path.join(loc, "data.json")
lock_file = os.path.join(loc, "test.pid")

_bytes = partial(bytes, encoding='utf-8') if sys.version_info > (3,) else \
    lambda x: str(x).encode('utf-8')


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

    def test_add_data(self):
        with Data(data_file, pid_file=lock_file) as users:
            users.add_data(new_data='test', test_data=['hi'])

        with Lock(pid_file=lock_file, timeout=3):
            with open(data_file, 'rb') as test_data:
                data = loads(test_data.read().decode('utf-8'))
                assert "hi" in data['data']['test_data'], data
                assert "test" == data['data']['new_data']

    def test_remove_data(self):
        with Lock(pid_file=lock_file, timeout=3):
            with open(data_file, 'r+b') as test_data:
                data = loads(test_data.read().decode('utf-8'))
                data['data']['new_test_key'] = "fake data"
                test_data.seek(0)
                test_data.write(_bytes(dumps(data)))
                test_data.truncate()

        with Data(data_file, pid_file=lock_file) as users:
            users.remove_data('new_test_key')

        with Lock(pid_file=lock_file, timeout=3):
            with open(data_file, 'rb') as test_data:
                data = loads(test_data.read().decode('utf-8'))
                assert "new_test_key" not in data['data']

    def test_export(self):
        with Data(data_file, pid_file=lock_file) as users:
            users.add_data(**{"special export": True})

        export_file = "test_export"

        with Data(data_file=data_file, pid_file=lock_file) as data:
            data.export_data(export_file)

        with Lock(pid_file=lock_file, timeout=3):
            with open(export_file, 'rb') as test_data:
                data = loads(test_data.read().decode('utf-8'))
                assert "special export" in data['data']

        os.unlink(export_file)

    def test_import(self):
        export_file = "test_export"

        with Lock(pid_file=lock_file, timeout=3):
            with open(export_file, 'wb') as test_data:
                test_data.write(_bytes(dumps({'data': {"special export": True}})))

        with Data(data_file=data_file, pid_file=lock_file) as data:
            data.import_data(export_file)
            assert "special export" in data.data

        os.unlink(export_file)

    def test_main_import_export(self):
        main("--force-unlock", "--export", "test_data")
        main("--force-unlock", "--import", "test_data", "--exit")
        os.unlink("test_data")
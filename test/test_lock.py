#!/usr/bin/env python
#-*- coding: utf-8 -*-
from nframe_server import Lock, LockError
import os
from json import loads, dumps
import sys
from unittest import TestCase

loc = os.path.abspath(os.path.dirname(__file__))

lock_file = os.path.join(loc, "test.pid")

class TestLock(TestCase):

    def setUp(self):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)

    def tearDown(self):
        if os.path.exists(lock_file):
            os.chmod(lock_file, 0o0777)
            os.unlink(lock_file)

    def test_lock(self):
        with Lock(pid_file=lock_file, safe=True, cleanup_on_term=True):
            a = Lock(pid_file=lock_file, safe=True)
            self.assertRaises(LockError, a.acquire)

    def test_pid_exists(self):
        with open(lock_file, "w") as otf:
            otf.write("")
        a = Lock(pid_file=lock_file, safe=True)
        self.assertRaises(LockError, a.acquire)




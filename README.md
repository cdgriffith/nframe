nframe
======

nframe is a tech demo of a Server-Client network framework.
[![Build Status](https://travis-ci.org/cdgriffith/nframe.png?branch=master)](https://travis-ci.org/cdgriffith/nframe)

**Basis:**

* Server is constantly running and can accept n connections
* Clients connect individually to the Server only when necessary, not keeping a connection open
* Persistent data can be stored on disk in JSON files
* A simple pid based file lock prevents modification of JSON data while server is running


Server
------

```bash
usage: nframe_server.py [-h] [-i IP] [-p PORT] [--import IMPORT_FILE]
                        [--export EXPORT_FILE] [--force-unlock]

nframe server

  -h, --help            show this help message and exit
  -i IP, --ip IP        IP address of server
  -p PORT, --port PORT  Port of server
  --import IMPORT_FILE  Import data before starting server
  --export EXPORT_FILE  Export data then exits
  --force-unlock        Remove lock file without discretion
```

Client
------

```python
> from nframe_client import Client

> conn = Client()

> conn.message("test data")
# test data
```

General Info
------------

**Developed for:**

* Python 2.6+
* Python 3.2+


Copyright \& License
--------------------

Copyright (c) 2014 Chris Griffith - MIT License (see LICENSE)

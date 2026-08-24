"""Start the SS-WEBSITE Flask app via tornado WSGI server.

Replaces `python app.py` for local dev. We use tornado (not Werkzeug's
dev server) because:

1. The Werkzeug dev server binds to IPv4 (0.0.0.0) only. Windows
   resolves `localhost` to `::1` (IPv6) first, then falls back to
   127.0.0.1 — each fallback costs ~2 seconds per request, so the
   dashboard takes 2s even for a 21-byte /healthz ping. We bind both
   IPv4 and IPv6 so `localhost` connects immediately.

2. The Werkzeug dev server's auto-reloader randomly kills the worker
   when ANY file under the project changes (including jinja2/filters.py
   in site-packages), manifesting as random CONNECTION_REFUSED errors
   when the user is actively clicking things. We restart manually.

3. tornado's WSGI server is faster and more predictable than Werkzeug's
   threaded dev server.

Usage:
    set FLASK_SECRET_KEY=dev-key-for-local-testing
    python start_tornado.py
"""
import os
import sys
import socket

# Ensure imports work when run as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as flask_app
import tornado.wsgi
import tornado.httpserver
import tornado.ioloop
import tornado.netutil

if not os.environ.get('FLASK_SECRET_KEY') and not flask_app.app.config.get('DEBUG'):
    raise RuntimeError(
        'FLASK_SECRET_KEY is not set and DEBUG mode is not enabled. '
        'Set the FLASK_SECRET_KEY environment variable or enable DEBUG '
        'mode (e.g., set FLASK_ENV=development or run with --debug).'
    )

container = tornado.wsgi.WSGIContainer(flask_app.app)
http_server = tornado.httpserver.HTTPServer(container)

# Bind both IPv4 and IPv6. On Windows, `localhost` resolves to ::1 (IPv6)
# first; if the server is IPv4-only, each connect attempt waits for the
# IPv6 fallback to time out — that's the 2-second delay.
sockets_v4 = tornado.netutil.bind_sockets(5000, address='0.0.0.0')
sockets_v6 = tornado.netutil.bind_sockets(5000, address='::', family=socket.AF_INET6)
http_server.add_sockets(sockets_v4)
http_server.add_sockets(sockets_v6)

print('SS-WEBSITE listening on http://localhost:5000 (IPv4 + IPv6, tornado WSGI)')
tornado.ioloop.IOLoop.current().start()

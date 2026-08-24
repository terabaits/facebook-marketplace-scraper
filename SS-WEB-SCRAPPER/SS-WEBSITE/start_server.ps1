cd "G:\Github\SS-WEB-SCRAPPER\SS-WEBSITE"
# Use tornado WSGI server instead of the Werkzeug dev server. The dev
# server has known issues on Windows (delayed responses when binding
# IPv4-only) and the auto-reloader randomly kills the worker when ANY
# file under the project changes. tornado is fast and stable.
$env:FLASK_SECRET_KEY = "dev-key-for-local-testing"
python start_tornado.py

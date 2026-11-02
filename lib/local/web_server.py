import boto3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
import logging
from pathlib import Path
from subprocess import check_call
from threading import Thread
from time import sleep
from urllib.parse import urlsplit

# Constants:
LOG = logging.getLogger(__name__)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ROOT_PATH = Path(__file__).parents[2]
LOCAL_CONFIG_PATH = ROOT_PATH / "tests" / "resources" / "config.json"
DIST_PATH = ROOT_PATH / "dist"
ASSETS_PATH = DIST_PATH / "assets"
INDEX_PATH = DIST_PATH / "index.html"
TEST_PATH = ROOT_PATH / "tests" / "typescript" / "assets"
DELAY_SERVER_START = 0.2


class HttpRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:  # type: ignore [no-untyped-def]
        super().__init__(*args, directory=ROOT_PATH, **kwargs)  # noqa

    def call_func(self, method: str) -> None:
        content = self.rfile.read(int(self.headers["Content-Length"] or 0))
        parsed = urlsplit(self.path)
        # Call the hacked boto3 library
        response = boto3.resource.call_func(  # type: ignore[attr-defined]
            parsed.path, method, self.headers, content, parsed.query
        )
        if (response["statusCode"] == HTTPStatus.NOT_FOUND) and (method == "get"):
            super().do_GET()
        else:
            self.send_response(response["statusCode"], response.get("message"))
            for key, value in response["headers"].items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response["body"].encode())

    def do_GET(self) -> None:
        if self.path == "/config.json":
            self.send_response(HTTPStatus.OK, "Success")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with LOCAL_CONFIG_PATH.open("rb") as file_obj:
                self.wfile.write(file_obj.read())
        elif self.path.startswith("/test/"):
            path = TEST_PATH / self.path[6:]
            if path.exists():
                self.send_response(HTTPStatus.OK, "Success")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                with path.open("rb") as file_obj:
                    self.wfile.write(file_obj.read())
            else:
                self.send_response(HTTPStatus.NOT_FOUND, "Not found")
        elif self.path.startswith("/assets/"):
            path = ASSETS_PATH / self.path[8:]
            if path.exists():
                self.send_response(HTTPStatus.OK, "Success")
                self.send_header("Content-Type", "text/javascript")
                self.end_headers()
                with path.open("rb") as file_obj:
                    self.wfile.write(file_obj.read())
            else:
                self.send_response(HTTPStatus.NOT_FOUND, "Not found")
        elif self.path.startswith("/static/") or self.path.startswith("/api/"):
            self.call_func("get")
        else:
            self.send_response(HTTPStatus.OK, "Success")
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with INDEX_PATH.open("rb") as file_obj:
                self.wfile.write(file_obj.read())

    def do_POST(self) -> None:
        self.call_func("post")

    def do_DELETE(self) -> None:
        self.call_func("delete")

    def do_PUT(self) -> None:
        self.call_func("put")


@dataclass
class WebBrowser:
    port: int

    def run_main_thread(self, user_id: str | None = None) -> None:
        if user_id:
            # Launch chrome as if logged in
            check_call([CHROME, f"http://localhost:{self.port}/?auth={user_id}"])

        # Launch webserver. It's okay if the browser starts a little early... probably.
        HTTPServer(("", self.port), HttpRequestHandler).serve_forever()

    def launch_daemon(self) -> None:
        httpd = HTTPServer(("", self.port), HttpRequestHandler)
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        sleep(DELAY_SERVER_START)

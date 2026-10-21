"""Exercise cache identity across compiled standalone entry points, not mocks."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def check_inside_image():
    calls = []
    rejected = {"/api/v1/artists/9"}

    class Backend(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append((self.path, dict(self.headers)))
            status = 429 if self.path in rejected else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if status == 429:
                self.send_header("Retry-After", "42")
            self.end_headers()
            data = (
                {"id": 8, "slug": "artist-8"}
                if self.path.split("?")[0].split("/")[-1].isdigit()
                else {"count": 0, "next": None, "previous": None, "results": []}
            )
            self.wfile.write(json.dumps(data).encode())

        def log_message(self, *args):
            pass

    backend = ThreadingHTTPServer(("127.0.0.1", 18000), Backend)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    environment = os.environ | {
        "HOSTNAME": "127.0.0.1",
        "PORT": "13000",
        "DJANGO_API_BASE_URL": "http://127.0.0.1:18000/api/v1",
        "INTERNAL_API_SECRET": "test-internal",
        "CACHE_REVALIDATION_SECRET": "test-warm",
    }
    opener = urllib.request.build_opener(NoRedirect)

    def request(path, *, action=None):
        if action:
            path += f"?action={action}"
        request = urllib.request.Request("http://127.0.0.1:13000" + path)
        if action:
            request.method = "POST"
            request.data = b""
            request.add_header("Authorization", "Bearer test-warm")
        try:
            response = opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    with tempfile.TemporaryFile(mode="w+") as logs:
        node = subprocess.Popen(
            ["node", "/app/frontend/server.js"],
            env=environment,
            stdout=logs,
            stderr=logs,
        )
        try:
            deadline = time.monotonic() + 60
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", 13000), timeout=1):
                        break
                except OSError:
                    if node.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Standalone server did not start")
                    time.sleep(0.2)

            for path in ("/artists/0008", "/artists/8"):
                status, headers, body = request(path)
                assert status == 308, (path, status, body)
                assert headers["Location"].endswith("/artists/artist-8")
                time.sleep(0.25)
            assert request("/backend-api/artists/8")[0] == 200
            # Proxy runs in a separate runtime without persistent Data Cache;
            # its explicit public reads must still carry the shared budget marker.
            assert len(calls) == 3, ("Unexpected numeric/browser reads", calls)

            assert request("/artists?search=repeat")[0] == 200
            time.sleep(0.25)
            before = len(calls)
            assert request("/artists?search=repeat")[0] == 200
            assert len(calls) == before, "Repeated SSR missed its cache"
            assert all(
                headers.get("X-KpopWins-Public-Read") == "1" for _, headers in calls
            ), calls

            before = len(calls)
            status, _, body = request("/api/revalidate", action="invalidate")
            assert status == 200 and json.loads(body)["revalidated"], body
            assert len(calls) == before, "Invalidation started warming prematurely"
            status, _, body = request("/api/revalidate", action="warm")
            assert status == 200 and json.loads(body)["warmed"], body
            assert len(calls) > before
            assert all(
                "X-KpopWins-Public-Read" not in headers for _, headers in calls[before:]
            ), "Warming consumed the public allowance"
            time.sleep(0.25)
            before = len(calls)
            assert (
                request("/backend-api/artists?ordering=-total_wins,name&page=1")[0]
                == 200
            )
            assert request("/artists")[0] == 200
            assert len(calls) == before, "Public reads did not reuse warmed data"

            for path in ("/artists/9", "/backend-api/artists/9"):
                status, headers, body = request(path)
                assert status == 429, (path, status, body)
                assert headers["Retry-After"] == "42"
            rejected.clear()
            assert request("/artists/9")[0] == 308, "429 poisoned the cache"
            assert all(
                headers.get("X-KpopWins-Internal-Key") == "test-internal"
                for _, headers in calls
            ), calls
            print("Standalone cache sharing, private warming and 429 recovery passed.")
        except BaseException:
            logs.seek(0)
            print(logs.read())
            raise
        finally:
            node.terminate()
            try:
                node.wait(timeout=10)
            except subprocess.TimeoutExpired:
                node.kill()
                node.wait()
            backend.shutdown()


if __name__ == "__main__":
    if sys.argv[1] == "--inside":
        check_inside_image()
    else:
        # Loopback-only stub + Next server run together without network access.
        script = Path(__file__).resolve().as_posix()
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--volume",
                f"{script}:/tmp/check-frontend-cache.py:ro",
                sys.argv[1],
                "python",
                "/tmp/check-frontend-cache.py",
                "--inside",
            ],
            check=True,
        )

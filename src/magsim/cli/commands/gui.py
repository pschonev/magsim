import logging
import webbrowser
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Annotated

import cappa

logger = logging.getLogger(__name__)

HOSTED_URL = "https://pschonev.github.io/magsim/"
DIST_DIR = Path("web") / "dist"
HOST = "127.0.0.1"


@cappa.command(name="gui", help="Open the interactive simulator and analysis dashboard.")
@dataclass
class GuiCommand:
    port: Annotated[int, cappa.Arg(long=True, help="Local server port.")] = 8000

    def __call__(self) -> None:
        if not (DIST_DIR / "index.html").exists():
            logger.warning("No local build in %s; opening %s", DIST_DIR, HOSTED_URL)
            webbrowser.open(HOSTED_URL)
            return
        handler = partial(SimpleHTTPRequestHandler, directory=str(DIST_DIR))
        url = f"http://{HOST}:{self.port}/"
        with ThreadingHTTPServer((HOST, self.port), handler) as server:
            logger.warning("Serving %s at %s (Ctrl+C to stop)", DIST_DIR, url)
            webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                logger.warning("Stopped.")

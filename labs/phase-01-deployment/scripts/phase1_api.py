"""Load upstream API with loopback binding; workspace stays in ignored artifacts."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"DeepAnalyze/API"))
import config
config.API_HOST = "127.0.0.1"
from main import create_app
import functools, http.server, threading
Path(config.WORKSPACE_BASE_DIR).mkdir(parents=True, exist_ok=True)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=config.WORKSPACE_BASE_DIR)
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", config.HTTP_SERVER_PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
import uvicorn
uvicorn.run(create_app(), host=config.API_HOST, port=config.API_PORT)

"""Re-autorizace Gmail OAuth tokenu – vlastní HTTP server."""
import pickle
import sys
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h1>✅ Autorizace úspěšná! Můžeš zavřít toto okno.</h1>".encode("utf-8"))
        threading.Thread(target=self.server.shutdown).start()

    def log_message(self, format, *args):
        pass

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
flow.redirect_uri = "http://localhost:8080/"
auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

with open("/tmp/auth_url.txt", "w") as f:
    f.write(auth_url)

print("\n" + "="*60)
print("OTEVŘI TUTO URL VE WINDOWS BROWSERU:")
print("="*60)
print(auth_url)
print("="*60)
print("\nČekám na callback z Googlu...\n")
sys.stdout.flush()

server = HTTPServer(("0.0.0.0", 8080), CallbackHandler)
server.serve_forever()

if auth_code:
    flow.fetch_token(code=auth_code)
    creds = flow.credentials
    with open("token.pickle", "wb") as f:
        pickle.dump(creds, f)
    print("✅ Token uložen! Gmail je znovu autorizovaný.")
else:
    print("❌ Kód neodchycen.")

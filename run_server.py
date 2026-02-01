import http.server
import socketserver
import webbrowser
import os
import subprocess
import threading
import time

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def run_scraper_periodically():
    while True:
        print("Running scraper to refresh data...")
        try:
            subprocess.run(["python", "scraper.py"], check=True)
            print("Data refreshed.")
        except Exception as e:
            print(f"Error running scraper: {e}")
        
        # Scrape every 5 minutes (300 seconds) while server is running
        time.sleep(300)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == '/refresh':
            print("Manual refresh requested.")
            try:
                subprocess.run(["python", "scraper.py"], check=True)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Refreshed")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_error(404)

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    
    # Run scraper immediately in a separate thread so it doesn't block server start
    # but also continues to update in background
    scraper_thread = threading.Thread(target=run_scraper_periodically, daemon=True)
    scraper_thread.start()
    
    # Give it a second to at least start the first scrape
    time.sleep(1)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        webbrowser.open(f"http://localhost:{PORT}/index.html")
        httpd.serve_forever()

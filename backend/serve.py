#!/usr/bin/env python3

import http.server
import socketserver
import os
import sys
import webbrowser
import threading
import queue
import time
import socket
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
JSON_FILE = FRONTEND_DIR / "bitcoin_nodes.json"
DEFAULT_PORT = 8000


def find_available_port(start_port=8000, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

file_change_queue = queue.Queue()
sse_clients = []


class JSONFileHandler(FileSystemEventHandler):
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(JSON_FILE):
            file_change_queue.put(('file_changed', time.time()))
            print(f"✓ Detected change in {JSON_FILE.name}")


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/events':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            client_id = id(self)
            sse_clients.append(client_id)
            
            try:
                self.wfile.write(b'data: {"type": "connected"}\n\n')
                self.wfile.flush()
                
                last_check = time.time()
                while True:
                    try:
                        try:
                            event_type, timestamp = file_change_queue.get(timeout=1)
                            if event_type == 'file_changed':
                                self.wfile.write(f'data: {{"type": "file_changed", "timestamp": {timestamp}}}\n\n'.encode())
                                self.wfile.flush()
                        except queue.Empty:
                            if time.time() - last_check > 30:
                                self.wfile.write(b': keepalive\n\n')
                                self.wfile.flush()
                                last_check = time.time()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        break
            finally:
                if client_id in sse_clients:
                    sse_clients.remove(client_id)
        else:
            super().do_GET()


def start_file_watcher():
    event_handler = JSONFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=str(FRONTEND_DIR), recursive=False)
    observer.start()
    print(f"✓ Watching {JSON_FILE.name} for changes")
    return observer


def main():
    os.chdir(FRONTEND_DIR)
    
    observer = start_file_watcher()
    
    port = find_available_port(DEFAULT_PORT)
    if port is None:
        print(f"Error: Could not find an available port starting from {DEFAULT_PORT}")
        observer.stop()
        observer.join()
        sys.exit(1)
    
    if port != DEFAULT_PORT:
        print(f"⚠ Port {DEFAULT_PORT} is in use, using port {port} instead")
    
    try:
        with socketserver.TCPServer(("", port), CORSRequestHandler) as httpd:
            url = f"http://localhost:{port}/index.html"
            print("=" * 60)
            print("Bitcoin Node Map Server")
            print("=" * 60)
            print(f"Server running at: {url}")
            print(f"Serving files from: {FRONTEND_DIR}")
            print(f"\n✓ Real-time file watching enabled")
            print("  The map will update automatically when bitcoin_nodes.json changes")
            print("\nPress Ctrl+C to stop the server")
            print("=" * 60)
            
            webbrowser.open(url)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        observer.stop()
        observer.join()
        print("Server stopped.")
        sys.exit(0)
    except OSError as e:
        print(f"Error starting server: {e}")
        observer.stop()
        observer.join()
        sys.exit(1)


if __name__ == "__main__":
    main()


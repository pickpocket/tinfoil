#!/usr/bin/env python3
"""
Simple HTTP server to serve the API Tester app and provide file access to the current directory.
This allows the browser app to see and select files from the current working directory.
"""
import http.server
import socketserver
import os
import json
import urllib.parse
from pathlib import Path

PORT = 8080

class FileServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for serving files and directory listing API."""
    
    def do_GET(self):
        """Handle GET requests with special handling for API endpoints."""
        # Handle API requests
        if self.path.startswith('/api/'):
            self.handle_api()
            return
        
        # For all other paths, use the standard SimpleHTTPRequestHandler
        super().do_GET()
    
    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests by sending CORS headers."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        self.end_headers()
    
    def send_header(self, keyword, value):
        """Send a MIME header to the client."""
        if self.request_version != 'HTTP/0.9':
            if not hasattr(self, '_headers_buffer'):
                self._headers_buffer = []
            self._headers_buffer.append(f"{keyword}: {value}\r\n".encode('latin-1', 'strict'))
        
        if keyword.lower() == 'connection':
            if value.lower() == 'close':
                self.close_connection = True
            elif value.lower() == 'keep-alive':
                self.close_connection = False
    
    def end_headers(self):
        """Send the blank line ending the MIME headers."""
        if self.request_version != 'HTTP/0.9':
            # Add CORS headers if not an OPTIONS request (which already adds them)
            if self.command != 'OPTIONS':
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST')
                self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
            
            self._headers_buffer.append(b"\r\n")
            self.wfile.write(b"".join(self._headers_buffer))
            self._headers_buffer = []
    
    def handle_api(self):
        """Handle API requests."""
        # List files in the current directory
        if self.path == '/api/files':
            self.list_files()
        else:
            self.send_error(404, "API endpoint not found")
    
    def list_files(self):
        """List all files in the current directory and subdirectories."""
        try:
            # Get current directory
            cwd = Path.cwd()
            
            # Find all files recursively
            all_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    # Create relative path
                    file_path = os.path.join(root, file)
                    
                    # Skip hidden files and directories
                    if '/.' in file_path or '\\.' in file_path:
                        continue
                    
                    # Get file info
                    abs_path = os.path.abspath(file_path)
                    rel_path = os.path.relpath(abs_path, os.path.abspath('.'))
                    size = os.path.getsize(file_path)
                    
                    # Add to list if it's a supported audio file
                    if file.lower().endswith('.flac'):
                        all_files.append({
                            'name': file,
                            'path': rel_path,
                            'size': size,
                            'size_human': self.human_readable_size(size)
                        })
            
            # Send the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Convert to JSON and send
            self.wfile.write(json.dumps({
                'files': all_files,
                'cwd': str(cwd)
            }).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def human_readable_size(self, size, decimal_places=2):
        """Convert file size to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size < 1024.0 or unit == 'PB':
                break
            size /= 1024.0
        return f"{size:.{decimal_places}f} {unit}"


def run_server():
    """Run the HTTP server."""
    handler = FileServerHandler
    
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"API Tester available at http://localhost:{PORT}/tinfoil_api_tester.html")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()


if __name__ == "__main__":
    run_server()
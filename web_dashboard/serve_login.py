#!/usr/bin/env python3
"""
Simple HTTP server to serve login.html with Supabase config injected
"""

import os
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")


class LoginHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/login.html' or self.path == '/static/login.html':
            # Serve login.html with config injected
            login_path = Path(__file__).parent / 'static' / 'login.html'
            if login_path.exists():
                with open(login_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Inject Supabase config as a script tag
                config_script = f"""
    <script data-supabase-config type="application/json">
{json.dumps({"url": SUPABASE_URL, "key": SUPABASE_ANON_KEY})}
    </script>
"""
                # Insert before the existing script tag
                content = content.replace('<script>', config_script + '\n    <script>', 1)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
                return
        
        # Serve other files normally
        return super().do_GET()


def main():
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, LoginHandler)
    
    print(f"Serving login.html on http://localhost:{port}/login.html")
    print(f"Supabase URL: {SUPABASE_URL}")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == '__main__':
    main()


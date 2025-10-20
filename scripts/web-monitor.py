#!/usr/bin/env python3
"""
Simple web-based monitoring dashboard for Kindle Sync service.
"""

import json
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from pathlib import Path


class MonitorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_dashboard_html().encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.get_status_data()).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def get_status_data(self):
        """Get current service status data."""
        try:
            # Service status
            result = subprocess.run(
                ["systemctl", "is-active", "kindle-sync.service"],
                capture_output=True,
                text=True,
            )
            service_status = result.stdout.strip()

            # Service uptime
            result = subprocess.run(
                [
                    "systemctl",
                    "show",
                    "kindle-sync.service",
                    "--property=ActiveEnterTimestamp",
                    "--value",
                ],
                capture_output=True,
                text=True,
            )
            uptime_start = result.stdout.strip()

            # File count
            sync_dir = Path("/home/hayden/obsidian-vault/Kindle Sync")
            file_count = len(list(sync_dir.glob("*"))) if sync_dir.exists() else 0
            md_count = len(list(sync_dir.glob("*.md"))) if sync_dir.exists() else 0
            pdf_count = len(list(sync_dir.glob("*.pdf"))) if sync_dir.exists() else 0

            # Recent logs
            result = subprocess.run(
                [
                    "journalctl",
                    "-u",
                    "kindle-sync.service",
                    "--no-pager",
                    "-n",
                    "10",
                    "--since",
                    "5 minutes ago",
                ],
                capture_output=True,
                text=True,
            )
            recent_logs = result.stdout.strip()

            return {
                "service_status": service_status,
                "uptime_start": uptime_start,
                "file_count": file_count,
                "md_count": md_count,
                "pdf_count": pdf_count,
                "recent_logs": recent_logs,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_dashboard_html(self):
        """Generate HTML dashboard."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Kindle Sync Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-ok { color: #28a745; }
        .status-error { color: #dc3545; }
        .status-warning { color: #ffc107; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric { text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; }
        .logs { background: #f8f9fa; padding: 15px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #0056b3; }
        .header { text-align: center; margin-bottom: 30px; }
        .last-updated { text-align: center; color: #6c757d; margin-top: 20px; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateDashboard(data);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }

        function updateDashboard(data) {
            if (data.error) {
                document.getElementById('error').textContent = data.error;
                return;
            }

            // Service status
            const statusEl = document.getElementById('service-status');
            statusEl.textContent = data.service_status;
            statusEl.className = data.service_status === 'active' ? 'status-ok' : 'status-error';

            // File counts
            document.getElementById('file-count').textContent = data.file_count;
            document.getElementById('md-count').textContent = data.md_count;
            document.getElementById('pdf-count').textContent = data.pdf_count;

            // Recent logs
            document.getElementById('recent-logs').textContent = data.recent_logs || 'No recent activity';

            // Last updated
            document.getElementById('last-updated').textContent = 'Last updated: ' + new Date().toLocaleString();
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);

        // Load data on page load
        window.onload = refreshData;
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Kindle Sync Monitor</h1>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh</button>
        </div>

        <div id="error" class="status-error"></div>

        <div class="grid">
            <div class="card">
                <h3>📊 Service Status</h3>
                <div class="metric">
                    <div class="metric-value" id="service-status">Loading...</div>
                    <div>Kindle Sync Service</div>
                </div>
            </div>

            <div class="card">
                <h3>📁 File Statistics</h3>
                <div class="grid">
                    <div class="metric">
                        <div class="metric-value" id="file-count">-</div>
                        <div>Total Files</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="md-count">-</div>
                        <div>Markdown</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="pdf-count">-</div>
                        <div>PDF Files</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>📋 Recent Activity</h3>
            <div class="logs" id="recent-logs">Loading...</div>
        </div>

        <div class="last-updated" id="last-updated">Loading...</div>
    </div>
</body>
</html>
        """


if __name__ == "__main__":
    import sys

    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    server = HTTPServer(("0.0.0.0", port), MonitorHandler)
    print(f"Kindle Sync Monitor starting on http://0.0.0.0:{port}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down monitor...")
        server.shutdown()

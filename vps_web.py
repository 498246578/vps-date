import json
import os
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from vps_manager import VPSManager


class VPSRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/services':
            manager = VPSManager()
            return self.send_json(200, manager.vps_data)
        return super().do_GET()

    def do_PUT(self):
        if self.path != '/api/services':
            return self.send_error(404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            services = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(services, list):
                raise ValueError('services 必须是数组')
            for service in services:
                if not isinstance(service, dict) or not str(service.get('name', '')).strip():
                    raise ValueError('每条记录必须包含服务器名称')
            manager = VPSManager()
            manager.vps_data = services
            manager.save_vps_data()
            return self.send_json(200, {'ok': True, 'count': len(services)})
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json(400, {'ok': False, 'error': str(exc)})
        except Exception as exc:
            return self.send_json(500, {'ok': False, 'error': str(exc)})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f'[网页管理] {fmt % args}')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    address = ('127.0.0.1', 8765)
    server = ThreadingHTTPServer(address, VPSRequestHandler)
    url = f'http://{address[0]}:{address[1]}/index.html'
    print(f'VPS 网页管理已启动：{url}')
    print('关闭此窗口即可停止服务。')
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    server.serve_forever()

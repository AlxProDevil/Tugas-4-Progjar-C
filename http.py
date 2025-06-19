import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import urllib.parse
import traceback

class HttpServer:
    def __init__(self):
        self.sessions={}
        self.types={}
        self.types['.pdf']='application/pdf'
        self.types['.jpg']='image/jpeg'
        self.types['.jpeg']='image/jpeg'
        self.types['.txt']='text/plain'
        self.types['.html']='text/html'
        self.base_dir = "server_files"
        os.makedirs(self.base_dir, exist_ok=True)

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk in headers:
            resp.append(f"{kk}:{headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = ''.join(resp)
        
        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()

        response = response_headers.encode() + messagebody
        return response

    def proses(self, data_bytes):
        
        header_end = data_bytes.find(b"\r\n\r\n")
        if header_end == -1:
            return self.response(400, 'Bad Request', 'Malformed request: no end of headers', {})

        headers_part_bytes = data_bytes[:header_end]
        raw_body = data_bytes[header_end + 4:]

        try:
            headers_part_str = headers_part_bytes.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            return self.response(400, 'Bad Request', 'Malformed request: unreadable headers', {})
        
        request_lines = headers_part_str.split("\r\n")
        
        if not request_lines:
            return self.response(400, 'Bad Request', 'Empty request line', {})

        baris = request_lines[0]
        all_headers_raw = [n for n in request_lines[1:] if n] # All header lines as strings
        
        headers = {}
        for line in all_headers_raw:
            if ":" in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
                
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = urllib.parse.unquote(j[1].strip())

            if method == 'GET':
                return self.http_get(object_address, headers)
            elif method == 'POST':
                return self.http_post(object_address, headers, raw_body)
            elif method == 'DELETE':
                return self.http_delete(object_address, headers)
            else:
                return self.response(405, 'Method Not Allowed', '', {})
        except IndexError:
            return self.response(400, 'Bad Request', 'Malformed request line', {})
        except Exception as e:
            traceback.print_exc()
            return self.response(500, 'Internal Server Error', f"Server error: {e}", {})

    def http_get(self, object_address, headers):
        if object_address == '/':
            return self.response(200, 'OK', 'Welcome to the HTTP Server! Try /list_files, /upload_file, /delete_file, /download/<filename>', {})

        if object_address == '/list_files':
            return self.list_files()
        
        if object_address.startswith('/download/'):
            filename = object_address.replace('/download/', '', 1)
            return self.download_file(filename)

        filepath = os.path.join(self.base_dir, object_address.lstrip('/'))
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as fp: # Read in binary mode
                    isi = fp.read()
                
                fext = os.path.splitext(filepath)[1]
                content_type = self.types.get(fext, 'application/octet-stream')
                
                headers = {'Content-type': content_type}
                return self.response(200, 'OK', isi, headers)
            except Exception as e:
                return self.response(500, 'Internal Server Error', f"Error reading file: {e}", {})
        else:
            return self.response(404, 'Not Found', '', {})

    def http_post(self, object_address, headers, body): # 'body' is now bytes
        if object_address == '/upload_file':
            filename = headers.get('x-filename')
            if not filename:
                return self.response(400, 'Bad Request', "Missing X-Filename header for upload.", {})

            filepath = os.path.join(self.base_dir, filename)
            try:
                with open(filepath, 'wb') as f:
                    f.write(body) # Write the raw bytes directly
                return self.response(200, 'OK', f"File '{filename}' uploaded successfully.", {})
            except Exception as e:
                return self.response(500, 'Internal Server Error', f"Error uploading file: {e}", {})
        else:
            return self.response(404, 'Not Found', '', {})

    def http_delete(self, object_address, headers):
        if object_address.startswith('/delete_file/'):
            filename = object_address.replace('/delete_file/', '', 1)
            filepath = os.path.join(self.base_dir, filename)

            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    os.remove(filepath)
                    return self.response(200, 'OK', f"File '{filename}' deleted successfully.", {})
                except Exception as e:
                    return self.response(500, 'Internal Server Error', f"Error deleting file: {e}", {})
            else:
                return self.response(404, 'Not Found', f"File '{filename}' not found.", {})
        else:
            return self.response(404, 'Not Found', '', {})

    def list_files(self):
        try:
            files = os.listdir(self.base_dir)
            file_list_html = "<h1>Files on Server:</h1><ul>"
            for f in files:
                file_list_html += f"<li><a href='/download/{urllib.parse.quote(f)}'>{f}</a></li>"
            file_list_html += "</ul>"
            return self.response(200, 'OK', file_list_html, {'Content-type': 'text/html'})
        except Exception as e:
            return self.response(500, 'Internal Server Error', f"Error listing files: {e}", {})

    def download_file(self, filename):
        filepath = os.path.join(self.base_dir, filename)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                fext = os.path.splitext(filepath)[1]
                content_type = self.types.get(fext, 'application/octet-stream')
                return self.response(200, 'OK', content, {'Content-type': content_type})
            except Exception as e:
                return self.response(500, 'Internal Server Error', f"Error reading file for download: {e}", {})
        else:
            return self.response(404, 'Not Found', f"File '{filename}' not found.", {})

if __name__ == "__main__":
    httpserver = HttpServer()
    d = httpserver.proses(b'GET testing.txt HTTP/1.0\r\nHost: localhost\r\n\r\n')
    print(d)
    d = httpserver.proses(b'GET donalbebek.jpg HTTP/1.0\r\nHost: localhost\r\n\r\n')
    print(d)
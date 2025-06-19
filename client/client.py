import sys
import socket
import logging
import os
import urllib.parse

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
def make_socket(destination_address, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_addr = (destination_address, port)
        logging.warning(f"Connecting to {server_addr}")
        sock.connect(server_addr)
        return sock
    except Exception as ee:
        logging.warning(f"Error connecting: {str(ee)}")
        return None

def send_http_request(method, path, server_host, server_port, custom_headers=None, body_bytes=None):
    sock = make_socket(server_host, server_port)
    if sock is None:
        print(f"Could not connect to {server_host}:{server_port}. Ensure server is running.")
        return b""

    try:
        headers_dict = custom_headers if custom_headers else {}
        headers_dict['Host'] = f"{server_host}:{server_port}"
        headers_dict['User-Agent'] = 'MyCustomClient/1.0'
        
        if body_bytes:
            headers_dict['Content-Length'] = str(len(body_bytes))
        
        request_line = f"{method} {path} HTTP/1.1\r\n"
        headers_str = "".join([f"{k}: {v}\r\n" for k, v in headers_dict.items()])
        
        full_request_bytes = request_line.encode('utf-8')
        full_request_bytes += headers_str.encode('utf-8')
        full_request_bytes += b"\r\n"
        if body_bytes:
            full_request_bytes += body_bytes

        logging.warning(f"Sending request: \n{full_request_bytes.decode('utf-8', errors='ignore').strip()}")
        sock.sendall(full_request_bytes)
        
        received_data = b""
        eoh_marker = b"\r\n\r\n"
        headers_parsed = False
        content_length = 0
        current_header_bytes_len = 0

        while True:
            data = sock.recv(4096)
            if not data:
                break

            received_data += data

            if not headers_parsed:
                eoh_pos = received_data.find(eoh_marker)
                if eoh_pos != -1:
                    headers_part_bytes = received_data[:eoh_pos]
                    current_header_bytes_len = eoh_pos + len(eoh_marker)
                    
                    try:
                        headers_str_response = headers_part_bytes.decode('utf-8', errors='ignore')
                        for line in headers_str_response.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                try:
                                    content_length = int(line.split(':', 1)[1].strip())
                                    break
                                except ValueError:
                                    logging.warning("Malformed Content-Length header received in response. Will read until connection closes.")
                                    content_length = -1
                                    break
                        headers_parsed = True
                    except UnicodeDecodeError:
                        logging.warning("Could not decode headers from server response.")
                        break

            if headers_parsed:
                if content_length != -1:
                    expected_total_len = current_header_bytes_len + content_length
                    if len(received_data) >= expected_total_len:
                        break

        logging.warning("Data received from server:")
        return received_data
    except Exception as ee:
        logging.error(f"Error during request: {str(ee)}")
        return b""
    finally:
        sock.close()

def parse_http_response(raw_response_bytes):
    """Parses raw HTTP response bytes into status line, headers, and body."""
    if not raw_response_bytes:
        return "", {}, b""

    eoh_marker = b"\r\n\r\n"
    eoh_pos = raw_response_bytes.find(eoh_marker)

    if eoh_pos == -1:
        headers_part_bytes = raw_response_bytes
        body_content = b""
    else:
        headers_part_bytes = raw_response_bytes[:eoh_pos]
        body_content = raw_response_bytes[eoh_pos + len(eoh_marker):]

    try:
        headers_str = headers_part_bytes.decode('utf-8', errors='ignore')
    except UnicodeDecodeError:
        logging.error("Failed to decode response headers to string.")
        headers_str = ""

    lines = headers_str.split('\r\n')
    status_line = lines[0] if lines else ""
    
    headers_dict = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers_dict[key.strip().lower()] = value.strip()
            
    return status_line, headers_dict, body_content


def pause_for_next_step():
    """Fungsi untuk menjeda eksekusi dan menunggu user menekan Enter."""
    input("\nTekan Enter untuk melanjutkan...")
    print("\n" + "="*40 + "\n")

def run_all_tests(server_host, server_port, server_type_name):
    print(f"\n\n--- Testing with {server_type_name.upper()} Server (Port {server_port}) ---")
    
    input(f"\nPress Enter to begin {server_type_name} Server tests...")

    local_test_file = "test_client_upload.txt"
    local_another_file = "another_client_file.txt"
    with open(local_test_file, "w") as f:
        f.write(f"This is a test file for upload from the {server_type_name} client.\n")
    with open(local_another_file, "w") as f:
        f.write(f"This is another {server_type_name} test file.")

    print("--- 1. Melihat daftar file awal ---")
    raw_response = send_http_request('GET', '/list_files', server_host, server_port)
    status_line, headers, body = parse_http_response(raw_response)
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print("\nBody:")
    try:
        print(body.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body[:100]}...") # Print a snippet for binary
    pause_for_next_step()

    remote_uploaded_file = f"remote_{server_type_name}_client_upload.txt"
    print(f"--- 2. Mengunggah file '{local_test_file}' sebagai '{remote_uploaded_file}' ---")
    with open(local_test_file, 'rb') as f:
        file_content_bytes = f.read()
    
    upload_headers = {'X-Filename': urllib.parse.quote(remote_uploaded_file)}
    raw_response = send_http_request('POST', '/upload_file', server_host, server_port, custom_headers=upload_headers, body_bytes=file_content_bytes)
    status_line, headers, body = parse_http_response(raw_response)
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print("\nBody:")
    try:
        print(body.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body[:100]}...")
    pause_for_next_step()

    print("--- 3. Melihat daftar file setelah diunggah ---")
    raw_response = send_http_request('GET', '/list_files', server_host, server_port)
    status_line, headers, body = parse_http_response(raw_response)
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print("\nBody:")
    try:
        print(body.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body[:100]}...")
    pause_for_next_step()

    remote_file_to_delete = f"delete_me_{server_type_name}_client.txt"
    with open(local_another_file, 'rb') as f:
        another_file_content_bytes = f.read()
    upload_headers_delete = {'X-Filename': urllib.parse.quote(remote_file_to_delete)}
    print(f"--- Uploading '{local_another_file}' as '{remote_file_to_delete}' for deletion test ---")
    raw_response_upload_delete_test = send_http_request('POST', '/upload_file', server_host, server_port, custom_headers=upload_headers_delete, body_bytes=another_file_content_bytes)
    status_line_upload, _, body_upload = parse_http_response(raw_response_upload_delete_test)
    if "200 OK" not in status_line_upload:
        logging.error(f"Failed to upload file for deletion test: {status_line_upload} - {body_upload.decode('utf-8', errors='ignore')}")

    raw_response = send_http_request('GET', '/list_files', server_host, server_port)
    print("\nList Files (before deletion confirmation):")
    _, _, body_list_before_delete = parse_http_response(raw_response)
    try:
        print(body_list_before_delete.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body_list_before_delete[:100]}...")
    pause_for_next_step()

    print(f"--- 4. Menghapus file '{remote_file_to_delete}' ---")
    raw_response = send_http_request('DELETE', f'/delete_file/{urllib.parse.quote(remote_file_to_delete)}', server_host, server_port)
    status_line, headers, body = parse_http_response(raw_response)
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print("\nBody:")
    try:
        print(body.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body[:100]}...")
    pause_for_next_step()

    print("--- 5. Melihat daftar file setelah dihapus ---")
    raw_response = send_http_request('GET', '/list_files', server_host, server_port)
    status_line, headers, body = parse_http_response(raw_response)
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print("\nBody:")
    try:
        print(body.decode('utf-8', errors='replace'))
    except UnicodeDecodeError:
        print(f"Binary content (first 100 bytes): {body[:100]}...")
    pause_for_next_step()

    print(f"--- 6. Mengunduh file '{remote_uploaded_file}' ---")
    download_save_path = f"downloaded_{server_type_name}_{remote_uploaded_file}"
    raw_response = send_http_request('GET', f'/download/{urllib.parse.quote(remote_uploaded_file)}', server_host, server_port)
    status_line, headers, body = parse_http_response(raw_response)
    
    print(f"Status: {status_line}")
    print("Headers:")
    for k, v in headers.items():
        print(f"  {k}: {v}")
    
    if "200 OK" in status_line:
        try:
            with open(download_save_path, 'wb') as f:
                f.write(body)
            print(f"\nSuccessfully downloaded '{remote_uploaded_file}' to '{download_save_path}'.")
            try:
                with open(download_save_path, 'r') as f_read:
                    print(f"Content of downloaded file: {f_read.read()}")
            except UnicodeDecodeError:
                print(f"Downloaded file '{download_save_path}' is binary, cannot print content directly.")
        except Exception as e:
            print(f"Error saving downloaded file: {e}")
    else:
        print(f"\nFailed to download. Server response body:\n{body.decode('utf-8', errors='replace')}")
    pause_for_next_step()

    if os.path.exists(local_test_file):
        os.remove(local_test_file)
    if os.path.exists(local_another_file):
        os.remove(local_another_file)
    if os.path.exists(download_save_path):
        os.remove(download_save_path)


if __name__ == '__main__':
    thread_pool_config = ('172.16.16.101', 8885, 'thread_pool')
    process_pool_config = ('172.16.16.101', 8889, 'process_pool')

    run_all_tests(*thread_pool_config)

    run_all_tests(*process_pool_config)

    print("\n--- Selesai Menjalankan Semua Tes ---")
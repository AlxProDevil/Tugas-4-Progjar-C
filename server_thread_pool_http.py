from socket import *
import socket
import time
import sys
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer

httpserver = HttpServer()

#untuk menggunakan threadpool executor, karena tidak mendukung subclassing pada process,
#maka class ProcessTheClient dirubah dulu menjadi function, tanpda memodifikasi behaviour didalamnya

def ProcessTheClient(connection,address):
    rcv_buffer = b""
    content_length = 0
    headers_parsed = False

    while True:
        try:
            data = connection.recv(4096)
            if not data:
                break

            rcv_buffer += data

            if not headers_parsed:
                eoh_marker = b"\r\n\r\n"
                eoh_pos = rcv_buffer.find(eoh_marker)

                if eoh_pos != -1:
                    headers_part_bytes = rcv_buffer[:eoh_pos]
                    
                    try:
                        headers_part_str = headers_part_bytes.decode('utf-8', errors='ignore')
                        
                        for line in headers_part_str.split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                try:
                                    content_length = int(line.split(':', 1)[1].strip())
                                    break
                                except ValueError:
                                    logging.error("Invalid Content-Length header.")
                                    connection.sendall(b"HTTP/1.0 400 Bad Request\r\nContent-Length: 26\r\n\r\nInvalid Content-Length\r\n\r\n")
                                    connection.close()
                                    return
                        headers_parsed = True
                    except UnicodeDecodeError:
                        logging.error("Could not decode headers part.")
                        connection.sendall(b"HTTP/1.0 400 Bad Request\r\nContent-Length: 23\r\n\r\nMalformed headers\r\n\r\n")
                        connection.close()
                        return

            if headers_parsed:
                expected_total_len = eoh_pos + len(eoh_marker) + content_length
                
                if len(rcv_buffer) >= expected_total_len:
                    
                    hasil = httpserver.proses(rcv_buffer)
                    connection.sendall(hasil)
                    connection.close()
                    return

        except OSError as e:
            logging.error(f"Socket error in ProcessTheClient: {e}")
            break
        except Exception as e:
            logging.error(f"General error in ProcessTheClient: {e}")
            import traceback
            traceback.print_exc()
            break
    
    connection.close()
    return



def Server():
	the_clients = []
	my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	my_socket.bind(('0.0.0.0', 8885))
	my_socket.listen(1)

	with ThreadPoolExecutor(20) as executor:
		while True:
				connection, client_address = my_socket.accept()
				logging.warning("connection from {}".format(client_address))
				p = executor.submit(ProcessTheClient, connection, client_address)
				the_clients.append(p)
				#menampilkan jumlah process yang sedang aktif
				jumlah = ['x' for i in the_clients if i.running()==True]
				print(jumlah)





def main():
	Server()

if __name__=="__main__":
	main()


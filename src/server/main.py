import socket
import threading
import os
import json
import hashlib

# Server configuration
HOST = '127.0.0.1'
PORT = 12345
CHUNK_SIZE = 1024
FILES_DIR = 'files'  # Directory containing the files to be sent

# Load the file list from server_files.txt
def load_file_list():
    file_list = {}
    with open('server_files.txt', 'r') as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) == 2:
                filename, size = parts
                file_list[filename] = {'size': size}
    return file_list

# Generate checksum for data
def generate_checksum(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()

# Handle client connection
def handle_client(conn, addr, file_list):
    print(f'Connected by {addr}')
    
    # Send the file list to the client
    conn.sendall(json.dumps(file_list).encode())

    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            request = json.loads(data.decode())
            if request.get('action') == 'shutdown':
                print(f'Client {addr} is shutting down.')
                break
            if request.get('action') == 'download':
                files_to_download = request['files']

                # Sort the files to download by priority in descending order
                files_to_download.sort(key=lambda x: x['priority'], reverse=True)

                for file_info in files_to_download:
                    filename = file_info['name']
                    if filename in file_list:
                        file_path = os.path.join(FILES_DIR, filename)
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)

                            # Send start of file marker
                            conn.sendall(json.dumps({'type': 'start', 'filename': filename, 'size': file_size}).encode())

                            with open(file_path, 'rb') as f:
                                while chunk := f.read(CHUNK_SIZE):
                                    checksum = generate_checksum(chunk)
                                    conn.sendall(json.dumps({'type': 'chunk', 'filename': filename, 'chunk': chunk.decode('latin1'), 'checksum': checksum}).encode())

                            # Send end of file marker
                            conn.sendall(json.dumps({'type': 'end', 'filename': filename}).encode())
                        else:
                            conn.sendall(json.dumps({'type': 'error', 'message': f'{filename} not found in {FILES_DIR}'}).encode())
                    else:
                        conn.sendall(json.dumps({'type': 'error', 'message': f'{filename} not found in file list'}).encode())
        except Exception as e:
            print(f'Error: {e}')
            break
                    
    conn.close()

# Main server function
def main():
    file_list = load_file_list()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr, file_list)).start()

if __name__ == "__main__":
    main()

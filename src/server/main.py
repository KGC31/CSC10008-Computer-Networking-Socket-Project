import socket
import threading
import os
import json
import hashlib
import signal
import sys

# Server configuration
HOST = '192.168.1.172'
PORT = 8000

CHUNK_SIZE = 1024
FILES_DIR = 'test_files'

# Flag to signal server shutdown
shutdown_flag = threading.Event()

def convert_to_bytes(size_str):
    size_str = size_str.upper()
    size_units = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
    size, unit = float(size_str[:-2]), size_str[-2:]
    return int(size * size_units[unit])

# Load the file list from server_files.txt
def load_file_list():
    file_list = {}
    for filename in os.listdir(FILES_DIR):
        file_path = os.path.join(FILES_DIR, filename)
        if os.path.isfile(file_path):  # Ensure it's a file and not a directory
            file_size = os.path.getsize(file_path)  # Get the file size in bytes
            file_list[filename] = {'size': file_size}
    return file_list

# Generate checksum for data
def generate_checksum(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()

# Handle client connection
def handle_client(conn, addr, file_list):
    print(f'Connected by {addr}')
    
    # Send the file list to the client
    conn.sendall(json.dumps(file_list).encode())

    while not shutdown_flag.is_set():
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

                # Open all files and prepare iterators for each
                file_iters = {}
                for file_info in files_to_download:
                    filename = file_info['name']
                    priority = file_info.get('priority', 1)  # Default priority is 1 (normal)
                    priority_chunk_size = CHUNK_SIZE * priority

                    if filename in file_list:
                        file_path = os.path.join(FILES_DIR, filename)
                        if os.path.exists(file_path):
                            file_iters[filename] = {
                                'file': open(file_path, 'rb'),
                                'size': file_list[filename]['size'],
                                'sent': 0,  # Keep track of how many bytes have been sent
                                'priority_chunk_size': priority_chunk_size  # Store the chunk size based on priority
                            }
                            # Send start of file marker
                            conn.sendall(json.dumps({'type': 'start', 'filename': filename, 'size': file_list[filename]['size']}).encode())
                        else:
                            conn.sendall(json.dumps({'type': 'error', 'message': f'{filename} not found in {FILES_DIR}'}).encode())
                    else:
                        conn.sendall(json.dumps({'type': 'error', 'message': f'{filename} not found in file list'}).encode())

                # Send chunks in an alternating manner
                while file_iters:
                    for filename in list(file_iters.keys()):
                        file_info = file_iters[filename]
                        file = file_info['file']
                        chunk_size = file_info['priority_chunk_size']
                        chunk = file.read(chunk_size)

                        if not chunk:  # If file is fully sent
                            file.close()
                            conn.sendall(json.dumps({'type': 'end', 'filename': filename}).encode())
                            del file_iters[filename]
                        else:
                            checksum = generate_checksum(chunk)
                            conn.sendall(json.dumps({
                                'type': 'chunk',
                                'filename': filename,
                                'chunk': chunk.decode('latin1'),  # Encode binary data as latin1
                                'checksum': checksum
                            }).encode())
                            file_info['sent'] += len(chunk)

        except Exception as e:
            print(f'Error: {e}')
            break

    if shutdown_flag.is_set():
        conn.sendall(json.dumps({'type': 'shutdown', 'message': 'Server is shutting down.'}).encode())
                    
    conn.close()

# Signal handler to stop the server gracefully
def signal_handler(sig, frame):
    print('\nServer is shutting down...')
    shutdown_flag.set()  # Set the shutdown flag
    sys.exit(0)

# Main server function
def main():
    # Register the signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    file_list = load_file_list()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')

        while not shutdown_flag.is_set():
            try:
                s.settimeout(1.0)  # Check for shutdown every 1 second
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr, file_list)).start()
            except socket.timeout:
                continue

if __name__ == "__main__":
    main()

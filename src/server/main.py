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
FILES_LIST = 'files_list.txt'

# Flag to signal server shutdown
shutdown_flag = threading.Event()

def load_file_list(files_list_path):
    """Load the list of available files from a file."""
    file_list = {}
    try:
        with open(files_list_path, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        filename = parts[0]
                        size_str = ' '.join(parts[1:])
                        file_list[filename] = {'size': size_str}
    except FileNotFoundError:
        print(f"File {files_list_path} not found.")
    return file_list

def generate_checksum(data):
    """Generate an MD5 checksum for a chunk of data."""
    return hashlib.md5(data, usedforsecurity=False).hexdigest()

def send_file_start(conn, filename, size):
    """Send the start of file marker to the client."""
    conn.sendall(json.dumps({'type': 'start', 'filename': filename, 'size': size}).encode())

def send_file_chunk(conn, filename, chunk):
    """Send a file chunk to the client."""
    checksum = generate_checksum(chunk)
    conn.sendall(json.dumps({
        'type': 'chunk',
        'filename': filename,
        'chunk': chunk.decode('latin1'),
        'checksum': checksum
    }).encode())

def send_file_end(conn, filename):
    """Send the end of file marker to the client."""
    conn.sendall(json.dumps({'type': 'end', 'filename': filename}).encode())

def send_error(conn, message):
    """Send an error message to the client."""
    conn.sendall(json.dumps({'type': 'error', 'message': message}).encode())

def handle_file_downloads(conn, queue):
    """Handle the file download requests from the client."""
    file_iters = {}

    # Prepare file iterators
    for file_info in queue:
        filename = file_info['name']
        priority = file_info.get('priority', 1)
        priority_chunk_size = CHUNK_SIZE * priority

        file_path = os.path.join(FILES_DIR, filename)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            file_iters[filename] = {
                'file': open(file_path, 'rb'),
                'size': size,
                'sent': 0,
                'priority_chunk_size': priority_chunk_size
            }
            send_file_start(conn, filename, size)
        else:
            send_error(conn, f'{filename} not found in {FILES_DIR}')

    # Send file chunks
    while file_iters:
        for filename in list(file_iters.keys()):
            file_info = file_iters[filename]
            file = file_info['file']
            chunk_size = file_info['priority_chunk_size']
            chunk = file.read(chunk_size)

            if not chunk:
                file.close()
                send_file_end(conn, filename)
                del file_iters[filename]
            else:
                send_file_chunk(conn, filename, chunk)

def handle_client(conn, addr):
    """Handle the communication with a connected client."""
    print(f'Connected by {addr}')
    file_list = load_file_list(FILES_LIST)
    
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
                queue = request['files']
                queue.sort(key=lambda x: x['priority'], reverse=True)
                handle_file_downloads(conn, queue)
        except Exception as e:
            print(f'Error: {e}')
            break

    if shutdown_flag.is_set():
        conn.sendall(json.dumps({'type': 'shutdown', 'message': 'Server is shutting down.'}).encode())
                    
    conn.close()

def signal_handler(sig, frame):
    """Signal handler to stop the server gracefully."""
    print('\nServer is shutting down...')
    shutdown_flag.set()  # Set the shutdown flag
    sys.exit(0)

def start_server():
    """Start the file server."""
    signal.signal(signal.SIGINT, signal_handler)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}')

        while not shutdown_flag.is_set():
            try:
                s.settimeout(1.0)  # Check for shutdown every 1 second
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue

if __name__ == "__main__":
    start_server()

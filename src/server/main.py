import socket
import os
import json
import hashlib
import signal

# Server configuration
HOST = "192.168.1.172"
PORT = 8000
CHUNK_SIZE = 1024
FILES_DIR = 'test_files'
FILES_LIST = 'files_list.txt'

# Global flag for shutting down the server
shutdown_flag = False
client_conn = None  # Keep track of the client connection to send shutdown signal

def load_file_list(files_list_path):
    """Load the list of available files from a file."""
    file_list = {}
    try:
        with open(files_list_path, 'r') as f:
            for line in f:
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

def send_file_list(conn, file_list):
    """Send the list of available files to the client."""
    conn.sendall(json.dumps(file_list).encode())

def send_file_start(conn, file_name, file_size):
    """Send the start of file marker to the client."""
    conn.sendall(json.dumps({'type': 'start', 'filename': file_name, 'size': file_size}).encode())

def send_file_chunk(conn, file_name, chunk):
    """Send a file chunk to the client."""
    checksum = generate_checksum(chunk)
    conn.sendall(json.dumps({
        'type': 'chunk',
        'filename': file_name,
        'chunk': chunk.decode('latin1'),
        'checksum': checksum
    }).encode())

def send_file_end(conn, file_name):
    """Send the end of file marker to the client."""
    conn.sendall(json.dumps({'type': 'end', 'filename': file_name}).encode())

def handle_download_request(conn, file_list, files_to_download):
    """Handle a download request from the client."""
    for file_name in files_to_download:
        if file_name in file_list:
            file_path = os.path.join(FILES_DIR, file_name)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                send_file_start(conn, file_name, file_size)
                
                with open(file_path, 'rb') as f:
                    while chunk := f.read(CHUNK_SIZE):
                        send_file_chunk(conn, file_name, chunk)

                send_file_end(conn, file_name)
            else:
                send_error(conn, f'{file_name} not found in {FILES_DIR}')
        else:
            send_error(conn, f'{file_name} not found in file list')

def send_error(conn, message):
    """Send an error message to the client."""
    conn.sendall(json.dumps({'type': 'error', 'message': message}).encode())

def handle_client(conn, addr, file_list):
    """Handle the communication with a connected client."""
    global client_conn
    client_conn = conn  # Store the client connection globally
    print(f'Connected by {addr}')
    send_file_list(conn, file_list)
    
    while not shutdown_flag:
        try:
            data = conn.recv(1024)
            if not data:
                break
            request = json.loads(data.decode())
            if request.get('action') == 'shutdown':
                print(f'Client {addr} is shutting down.')
                break
            elif request.get('action') == 'download':
                handle_download_request(conn, file_list, request['files'])
        except Exception as e:
            if not shutdown_flag:
                print(f'Error: {e}')
            break

    conn.close()

def signal_client_shutdown(conn):
    """Signal the connected client to shut down."""
    try:
        if conn:
            conn.sendall(json.dumps({'action': 'shutdown'}).encode())
    except Exception as e:
        print(f"Error signaling client shutdown: {e}")

def signal_handler(sig, frame):
    """Signal handler to set the shutdown flag on Ctrl+C."""
    global shutdown_flag
    print("Shutting down the server...")
    signal_client_shutdown(client_conn)  # Signal the client before shutting down
    shutdown_flag = True

def start_server():
    """Start the file server."""
    global shutdown_flag
    file_list = load_file_list(FILES_LIST)

    signal.signal(signal.SIGINT, signal_handler)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)  # Allow only 1 client at a time
        print(f'Server listening on {HOST}:{PORT}')

        while not shutdown_flag:
            try:
                server_socket.settimeout(1.0)
                conn, addr = server_socket.accept()
                handle_client(conn, addr, file_list)
            except socket.timeout:
                continue

if __name__ == "__main__":
    start_server()

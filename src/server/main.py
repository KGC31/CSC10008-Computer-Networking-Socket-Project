import socket
import os
import json
import hashlib
import signal

# Server configuration
HOST = "192.168.1.172"
PORT = 8000
CHUNK_SIZE = 1024
FILES_DIR = 'files'

# Flag for shutting down the server
shutdown_flag = False

# Load the file list from the directory
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

    while not shutdown_flag:
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

                for file_name in files_to_download:
                    if file_name in file_list:
                        file_path = os.path.join(FILES_DIR, file_name)
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)

                            # Send start of file marker
                            conn.sendall(json.dumps({'type': 'start', 'filename': file_name, 'size': file_size}).encode())

                            with open(file_path, 'rb') as f:
                                while chunk := f.read(CHUNK_SIZE):
                                    checksum = generate_checksum(chunk)
                                    conn.sendall(json.dumps({'type': 'chunk', 'filename': file_name, 'chunk': chunk.decode('latin1'), 'checksum': checksum}).encode())

                            # Send end of file marker
                            conn.sendall(json.dumps({'type': 'end', 'filename': file_name}).encode())
                        else:
                            conn.sendall(json.dumps({'type': 'error', 'message': f'{file_name} not found in {FILES_DIR}'}).encode())
                    else:
                        conn.sendall(json.dumps({'type': 'error', 'message': f'{file_name} not found in file list'}).encode())
        except Exception as e:
            if not shutdown_flag:
                print(f'Error: {e}')
            break
                    
    conn.close()

# Signal handler to set shutdown flag on Ctrl+C
def signal_handler(sig, frame):
    global shutdown_flag
    print("Shutting down the server...")
    shutdown_flag = True

# Main server function
def main():
    global shutdown_flag
    file_list = load_file_list()

    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)  # Allow only 1 client at a time
        print(f'Server listening on {HOST}:{PORT}')

        while not shutdown_flag:
            try:
                s.settimeout(1.0)
                conn, addr = s.accept()
                handle_client(conn, addr, file_list)
            except socket.timeout:
                continue

if __name__ == "__main__":
    main()

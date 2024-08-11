import socket
import json
import os
import time
from tqdm import tqdm
import hashlib
import math

# Client configuration
HOST = "192.168.1.172"
PORT = 8000
CHUNK_SIZE = 1024
INPUT_FILE = 'input.txt'
OUTPUT_DIR = 'downloads'

downloaded = []
queue = []

def receive_file_list(client_socket):
    """Receive and display the list of available files from the server."""
    file_list_data = client_socket.recv(1024)
    file_list = json.loads(file_list_data.decode())
    print("Available files from server:")
    for file_name, info in file_list.items():
        print(f"{file_name} - {info['size']}")
    return file_list

def read_input_file():
    """Read file priorities from input.txt and return a list of files with priorities."""
    file_priorities = []
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                file_name, priority = parts
                priority = {
                    'NORMAL': 1,
                    'HIGH': 10,
                    'CRITICAL': 20
                }.get(priority, 1)  # Default to NORMAL if priority is unknown
                file_priorities.append({
                    'name': file_name,
                    'priority': priority
                })
    return file_priorities

def generate_checksum(data):
    """Generate an MD5 checksum for the given data."""
    return hashlib.md5(data, usedforsecurity=False).hexdigest()

def check_existing_files(file_list):
    """Prompt user to replace existing files and return the list of files to download."""
    confirmed_files = []
    for file in file_list:
        file_path = os.path.join(OUTPUT_DIR, file['name'])
        if os.path.exists(file_path):
            while True:
                user_input = input(f"File '{file['name']}' already exists. Replace it? (y/n): ").strip().lower()
                if user_input == 'y':
                    confirmed_files.append(file)
                    break
                elif user_input == 'n':
                    break
                else:
                    print("Please enter 'y' for yes or 'n' for no.")
        else:
            confirmed_files.append(file)
    return confirmed_files

def handle_file_download(client_socket, progress_bars):
    """Handle the file download process from the server."""
    buffer = b''

    while queue:
        client_socket.settimeout(2.0)
        try:
            data = client_socket.recv(CHUNK_SIZE)
            buffer += data

            while True:
                try:
                    response, offset = json.JSONDecoder().raw_decode(buffer.decode())
                    buffer = buffer[offset:]  # Keep any remaining data in the buffer

                    if response['type'] == 'start':
                        file_name = response['filename']
                        file_path = os.path.join(OUTPUT_DIR, file_name)
                        file_size = int(response['size'])
                        progress_bars[file_name] = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name)
                        with open(file_path, 'wb') as f:
                            f.close()  # Create an empty file first
                    elif response['type'] == 'chunk':
                        file_name = response['filename']
                        chunk = response['chunk'].encode('latin1')
                        checksum = response['checksum']
                        if generate_checksum(chunk) == checksum:
                            with open(os.path.join(OUTPUT_DIR, file_name), 'ab') as f:
                                f.write(chunk)
                            progress_bars[file_name].update(len(chunk))
                    elif response['type'] == 'end':
                        file_name = response['filename']
                        downloaded.append(file_name)
                        progress_bars[file_name].close()
                        queue[:] = [f for f in queue if f['name'] != file_name]
                    elif response['type'] == 'shutdown':
                        print("Server is shutting down. Closing connection.")
                        queue.clear()
                        return
                    elif response['type'] == 'error':
                        print(response['message'])
                except json.JSONDecodeError:
                    break
        except socket.timeout:
            break

def start_client():
    """Start the client, connect to the server, and manage file downloads."""
    global queue
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print("Connected to the server.")

    receive_file_list(client_socket)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        while True:
            input_files = read_input_file()

            for file in input_files:
                if file['name'] not in downloaded and file not in queue:
                    queue.append(file)

            if queue:
                # Check for existing files and prompt user
                queue = check_existing_files(queue)

                if queue:
                    # Send the list of files to download to the server
                    client_socket.sendall(json.dumps({'action': 'download', 'files': queue}).encode())

                    progress_bars = {}
                    handle_file_download(client_socket, progress_bars)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nClient is shutting down...")
        client_socket.sendall(json.dumps({'action': 'shutdown'}).encode())
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()

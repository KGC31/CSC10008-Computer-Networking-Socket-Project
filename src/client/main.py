import socket
import json
import os
import time
from tqdm import tqdm
import hashlib

queue = []
# Client config
HOST = "192.168.56.1"
PORT = 12345
CHUNK_SIZE = 1024
INPUT_FILE = 'input.txt'
OUTPUT_DIR = 'download'

# Read file priorities from input.txt
def read_input_file():
    file_priorities = []
    with open(INPUT_FILE, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                file_name, priority = parts
                priority = {
                    'NORMAL': 1,
                    'HIGH': 4,
                    'CRITICAL': 10
                }[priority]
                file_priorities.append({
                    'name': file_name,
                    'priority': priority
                })
    return file_priorities

def generate_checksum(data):
    return hashlib.md5(data, usedforsecurity=False).hexdigest()

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print("Connected to the server.")

    # Receive file list from server
    file_list_data = client_socket.recv(1024)
    file_list = json.loads(file_list_data.decode())
    print("Available files from server:")
    for file_name, info in file_list.items():
        print(f"{file_name} - {info['size']}")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    file_priorities = read_input_file()

    # Send the list of files to download to the server
    client_socket.sendall(json.dumps({'action': 'download', 'files': file_priorities}).encode())

    buffer = b''
    file = None
    pbar = None

    try:
        while True:
            data = client_socket.recv(CHUNK_SIZE)
            if not data:
                break
            buffer += data

            # Process complete JSON objects from the buffer
            while True:
                try:
                    response, offset = json.JSONDecoder().raw_decode(buffer.decode())
                    buffer = buffer[offset:]  # Keep any remaining data in the buffer

                    if response['type'] == 'start':
                        file_name = response['filename']
                        file_path = os.path.join(OUTPUT_DIR, file_name)
                        file_size = response['size']
                        file = open(file_path, 'wb')
                        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name)
                    elif response['type'] == 'chunk':
                        file_name = response['filename']
                        chunk = response['chunk'].encode('latin1')
                        checksum = response['checksum']
                        if generate_checksum(chunk) == checksum:
                            file.write(chunk)
                            pbar.update(len(chunk))
                    elif response['type'] == 'end':
                        file_name = response['filename']
                        file.close()
                        pbar.close()
                        print(f"Download complete: {file_name}")
                    elif response['type'] == 'error':
                        print(response['message'])
                except json.JSONDecodeError:
                    # Not a complete JSON object, wait for more data
                    break

    except KeyboardInterrupt:
        print("\nClient is shutting down...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()

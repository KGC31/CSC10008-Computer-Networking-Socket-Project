import socket
import json
import os
import hashlib
import time
from tqdm import tqdm

# Client configuration
HOST = "192.168.1.172"
PORT = 8000
CHUNK_SIZE = 1024
INPUT_FILE = 'input.txt'
OUTPUT_DIR = 'downloads'

downloaded = []

# Read file list from input.txt
def read_input_file():
    with open(INPUT_FILE, 'r') as f:
        files_to_download = [line.strip() for line in f if line.strip()]
    return files_to_download

def generate_checksum(data):
    return hashlib.md5(data).hexdigest()

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print("Connected to the server.")

    # Receive file list from server
    file_list_data = client_socket.recv(1024)
    file_list = json.loads(file_list_data.decode())
    print("Available files from server:")
    for file_name, info in file_list.items():
        print(f"{file_name} - {info['size']} bytes")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        while True:
            files_to_download = read_input_file()

            # Filter out already downloaded files
            files_to_download = [file for file in files_to_download if file not in downloaded]

            if files_to_download:
                # Send the list of files to download to the server
                client_socket.sendall(json.dumps({'action': 'download', 'files': files_to_download}).encode())

                buffer = b''
                file = None
                pbar = None

                while files_to_download:
                    data = client_socket.recv(CHUNK_SIZE)
                    buffer += data

                    # Process complete JSON objects from the buffer
                    while True:
                        try:
                            response, offset = json.JSONDecoder().raw_decode(buffer.decode('latin1'))
                            buffer = buffer[offset:]

                            if response['type'] == 'start':
                                file_name = response['filename']
                                file_path = os.path.join(OUTPUT_DIR, file_name)
                                file_size = response['size']
                                file = open(file_path, 'wb')
                                pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name)

                            elif response['type'] == 'chunk':
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
                                downloaded.append(file_name)
                                files_to_download.remove(file_name)

                        except json.JSONDecodeError:
                            # Not a complete JSON object, wait for more data
                            break

            time.sleep(2)  # Check the input file periodically

    except KeyboardInterrupt:
        print("\nClient is shutting down...")
        client_socket.sendall(json.dumps({'action': 'shutdown'}).encode())
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()

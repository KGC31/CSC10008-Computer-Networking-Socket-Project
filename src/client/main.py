import socket
import json
import os
import hashlib
from tqdm import tqdm

# Client configuration
HOST = "192.168.1.172"
PORT = 8000
CHUNK_SIZE = 1024
INPUT_FILE = 'input.txt'
OUTPUT_DIR = 'downloads'

downloaded = []

def read_input_file():
    """Read the list of files to download from the input file."""
    with open(INPUT_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def generate_checksum(data):
    """Generate an MD5 checksum for the given data."""
    return hashlib.md5(data).hexdigest()

def receive_file_list(client_socket):
    """Receive and display the list of available files from the server."""
    file_list_data = client_socket.recv(1024)
    file_list = json.loads(file_list_data.decode())
    print("Available files from server:")
    for file_name, info in file_list.items():
        print(f"{file_name} - {info['size']}")
    return file_list

def setup_output_directory():
    """Create the output directory if it does not exist."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def check_existing_files(files_to_download):
    """Check if files already exist in the output directory and prompt user."""
    filtered_files = []
    for file_name in files_to_download:
        file_path = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(file_path):
            user_input = input(f"File '{file_name}' already exists. Overwrite? (y/n): ").strip().lower()
            if user_input == 'y':
                filtered_files.append(file_name)
        else:
            filtered_files.append(file_name)
    return filtered_files

def send_download_request(client_socket, files_to_download):
    """Send the download request to the server."""
    client_socket.sendall(json.dumps({'action': 'download', 'files': files_to_download}).encode())

def process_server_response(client_socket, files_to_download):
    """Process the server's response to download the files."""
    buffer = b''
    file = None
    pbar = None

    while files_to_download:
        data = client_socket.recv(CHUNK_SIZE)
        buffer += data

        while True:
            try:
                response, offset = json.JSONDecoder().raw_decode(buffer.decode('latin1'))
                buffer = buffer[offset:]

                if response['type'] == 'start':
                    file_name, file, pbar = start_file_transfer(response)

                elif response['type'] == 'chunk':
                    process_file_chunk(response, file, pbar)

                elif response['type'] == 'end':
                    complete_file_transfer(response, file, pbar, files_to_download)

                elif response.get('action') == 'shutdown':
                    print("Server is shutting down. Closing client.")
                    return

            except json.JSONDecodeError:
                break

def start_file_transfer(response):
    """Handle the start of a file transfer."""
    file_name = response['filename']
    file_path = os.path.join(OUTPUT_DIR, file_name)
    file_size = response['size']
    file = open(file_path, 'wb')
    pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=file_name)
    return file_name, file, pbar

def process_file_chunk(response, file, pbar):
    """Process a chunk of data received from the server."""
    chunk = response['chunk'].encode('latin1')
    checksum = response['checksum']
    if generate_checksum(chunk) == checksum:
        file.write(chunk)
        pbar.update(len(chunk))

def complete_file_transfer(response, file, pbar, files_to_download):
    """Handle the completion of a file transfer."""
    file_name = response['filename']
    file.close()
    pbar.close()
    print(f"Download complete: {file_name}")
    downloaded.append(file_name)
    files_to_download.remove(file_name)

def start_client():
    """Start the client to connect to the server and download files."""
    global downloaded

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print("Connected to the server.")

    file_list = receive_file_list(client_socket)
    setup_output_directory()

    try:
        while True:
            queue = read_input_file()
            queue = [file for file in queue if file not in downloaded]

            if queue:
                queue = check_existing_files(queue)
                if queue:  # Only proceed if there are files left to download
                    send_download_request(client_socket, queue)
                    process_server_response(client_socket, queue)

    except KeyboardInterrupt:
        print("Client interrupted. Closing connection.")
        client_socket.close()

if __name__ == "__main__":
    start_client()

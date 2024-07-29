import socket

HOST="127.0.0.1"
PORT=12345

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print("Server started and listening for connections...")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connected to client: {client_address}")
            try:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    print(f"Received from {client_address}: {data.decode()}")
                    client_socket.sendall(data)
            except ConnectionResetError:
                print(f"Connection with {client_address} was reset.")
            finally:
                client_socket.close()
                print(f"Connection with {client_address} closed.")
    except KeyboardInterrupt:
        print("\nServer is shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
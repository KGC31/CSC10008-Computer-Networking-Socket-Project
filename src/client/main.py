import socket

HOST="127.0.0.1"
PORT=12345
xinxin
def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while True:
        try:
            client_socket.connect((HOST, PORT))
            print("Connected to the server.")
            break
        except ConnectionRefusedError:
            print("Server is busy. Retrying...")
            break

    try:
        while True:
            message = input("Enter message to send to server: ")
            client_socket.sendall(message.encode())
            data = client_socket.recv(1024)
            print(f"Received from server: {data.decode()}")
    except KeyboardInterrupt:
        print("\nClient is shutting down...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()

import re
import socket

HOST='127.0.0.1'
PORT=12345

def receive_file(filename, client_socket):
    with open(filename, 'wb') as f:
        while (chunk := client_socket.recv(1024)):
            if not chunk:
                break
            f.write(chunk)
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
        filename = input("Enter filename to send to server: ")
        client_socket.sendall(filename.encode())
        receive_file(filename,client_socket)
       
            
      
    except KeyboardInterrupt:
        print("\nClient is shutting down...")
     
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()

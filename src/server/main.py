import socket 

# Define network address for server
HOST = '127.0.0.1'  
PORT = 8000 

# Init socket for server that listens at most n clients
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(2)

def main():
    while True:
        client, addr = s.accept()
        
        try:
            print('Connected by', addr)
            while True:
                data = client.recv(1024)
                str_data = data.decode("utf8")
                if str_data == "quit":
                    break
                """if not data:
                    break
                """
                print("Client: " + str_data)

                msg = input("Server: ")
                    
        finally:
            client.close()

    s.close()

if __name__ == '__main__':
    main()
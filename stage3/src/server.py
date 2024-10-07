# server.py
import socket

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 65432))
    server_socket.listen()

    print("Server is listening on port 65432")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected by {addr}")

        data = client_socket.recv(1024).decode('utf-8')
        print(f"Received data: {data}")

        # ここでデータを処理し、返信を作成します
        response = f"Received: {data}"
        client_socket.sendall(response.encode('utf-8'))

        client_socket.close()

if __name__ == '__main__':
    start_server()
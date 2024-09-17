import socket
import secrets
import time
import threading


# class TCPServer:
#     def __init__(self, server_address, server_port):
#         self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#         self.server_address = server_address
#         self.server_port = server_port
#         print('Starting up on {}'.format(self.server_address))
#         self.sock.bind((server_address, server_port))
    
#     def main(self):
#         self.sock.listen()
#         while True:
#             connection, client_address = self.sock.accept()
#             try:
#                 print('connection from', client_address)
#                 byte_data = connection.recv(4096)

#                 header = byte_data[:32]
#                 room_name_size = int.from_bytes(header[:1], "big")
#                 operation = int.from_bytes(header[1:2], "big")
#                 state = int.from_bytes(header[2:3], "big")
#                 operation_payload_size = int.from_bytes(header[3:32], "big")

#                 print('Received header from client.')
#                 print(f'room_name_size: {room_name_size}')
#                 print(f'operation: {operation}')
#                 print(f'state: {state}')
#                 print(f'operation_payload_size: {operation_payload_size}')

#                 body = byte_data[32:]
#                 room_name = body[:room_name_size].decode("utf-8")
#                 operation_payload = body[room_name_size : room_name_size + operation_payload_size].decode("utf-8")

#                 print(f'room_name: {room_name}')
#                 print(f'operation_payload: {operation_payload}')

#                 token 

#                 if operation == 1:
                    

                    

#                 elif operation == 2:


#             except Exception as e:
#                 print('Error: ' + str(e))

#             finally:
#                 print("Closing current connection")
#                 connection.close()


import socket
import time

# class UDPServer:
#     def __init__(self):

# AF_INETを使用し、UDPソケットを作成
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = '0.0.0.0'
server_port = 9001
print('starting up on port {}'.format(server_port))

# ソケットを特殊なアドレス0.0.0.0とポート9001に紐付け
sock.bind((server_address, server_port))

clients = {}

# クライアントの最後のメッセージ送信時刻を更新
def update_client_last_message_sent_time(client_address):
    clients[client_address] = time.time()

# 5分間メッセージを送信していない場合、リレーシステムから削除
def remove_inactive_clients():
    while True:
        current_time = time.time()
        for client_address in clients.keys():
            if current_time - clients[client_address] > 300:
                del clients[client_address]
                print(f"{client_address} has timed out")
        time.sleep(60)

# メッセージをリレー
def relay_message(full_message, sender_address, username):
    for client_address in clients.keys():
        if client_address != sender_address:
            sent = sock.sendto(full_message, client_address)
            print('sent {} bytes back to {}'.format(sent, client_address))

threading.Thread(target=remove_inactive_clients, daemon=True).start()

while True:
    print('\nwaiting to receive message')
    full_message, client_address = sock.recvfrom(4096)
    usernamelen = full_message[0]
    username = full_message[1:usernamelen+1]
    message = full_message[usernamelen+1:]
    print('received {} bytes from {}'.format(len(message), username))
    print(message)
    update_client_last_message_sent_time(client_address)
    if message:
        relay_message(full_message, client_address, username)
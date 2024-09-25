import socket
import secrets
import time
import threading

class TCPServer:
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        print('Starting up on {}'.format(server_address))
        self.sock.bind((server_address, server_port))
        self.sock.listen()
    
    def handle_message(self):
        while True:
            connection, client_address = self.sock.accept()
            try:
                print('connection from', client_address)
                byte_data = connection.recv(4096)

                header = byte_data[:32]
                room_name_size = int.from_bytes(header[:1], "big")
                operation = int.from_bytes(header[1:2], "big")
                state = int.from_bytes(header[2:3], "big")
                operation_payload_size = int.from_bytes(header[3:32], "big")

                # print('Received header from client.')
                # print(f'room_name_size: {room_name_size}')
                # print(f'operation: {operation}')
                # print(f'state: {state}')
                # print(f'operation_payload_size: {operation_payload_size}')

                body = byte_data[32:]
                room_name = body[:room_name_size].decode("utf-8")
                operation_payload = body[room_name_size : room_name_size + operation_payload_size].decode("utf-8")

                # print(f'room_name: {room_name}')
                # print(f'operation_payload: {operation_payload}')

                token = secrets.token_bytes(255)

                if operation == 1:
                    chat_room.create_room(room_name, operation_payload, token, client_address[0])
                    connection.send(token)
                
                elif operation == 2:
                    chat_room.join_room(room_name, operation_payload, token, client_address[0])
                    connection.send(token)

            except Exception as e:
                print('Error: ' + str(e))

            finally:
                print("Closing current connection")
                connection.close()



class ChatRoom:
    def __init__(self):
        self.chat_rooms = {}
    
    def create_room(self, room_name, operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            raise ValueError(f'{room_name}は既に存在しています')
        else:
            self.chat_rooms[room_name] = {'host' : None,  'members' : None}
            self.chat_rooms[room_name]['host'] = {token : (operation_payload, client_address)}
            self.chat_rooms[room_name]['members'] = {token : (operation_payload, client_address)}
        
        print(self.chat_rooms)
    
    def join_room(self, room_name, operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            self.chat_rooms[room_name]['members'][token] = (operation_payload, client_address)
        else:
            raise KeyError(f'{room_name}は見つかりませんでした')
        
        print(self.chat_rooms)


# UDPサーバークラスの定義
class UDPServer:
    def __init__(self, host, port, chat_room):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.chat_room = chat_room
        self.sock.bind(self.server_address)
        self.clients = {}
        self.client_last_active = {}

    def update_client_last_message_sent_time(self, client_address):
        self.client_last_active[client_address] = time.time()

    def remove_inactive_clients(self):
        while True:
            current_time = time.time()
            for client_address in list(self.client_last_active.keys()):
                if current_time - self.client_last_active[client_address] > 60:
                    print(f"Removing inactive client: {client_address}")
                    del self.client_last_active[client_address]
                    del self.clients[client_address]
            time.sleep(30)


# メッセージをリレー
    def relay_message(self, full_message, sender_address, username):
        for client_address in self.clients.keys():
            if client_address != sender_address:
                sent = self.sock.sendto(full_message, client_address)
                print('sent {} bytes back to {}'.format(sent, client_address))
                
    def start(self):
        threading.Thread(target=self.remove_inactive_clients, daemon=True).start()
        while True:
            print('\nwaiting to receive message')
            full_message, client_address = self.sock.recvfrom(4096)
            room_name_size = full_message[0]
            token_size = full_message[1]
            room_name = full_message[2: 2+room_name_size].decode()
            token = full_message[2+room_name_size: 2+room_name_size+token_size]
            message = full_message[2+room_name_size+token_size:].decode()
            print('received {} bytes from {}'.format(len(message), self.user_name))
            print(message)
            self.update_client_last_message_sent_time(client_address)
            if message:
                self.relay_message(full_message, client_address, self.user_name) 

    def handle_message(self):
        print("UDP server listening for messages...")
        while True:
            data, addr = self.sock.recvfrom(4096)
            print(f"Received message from {addr}: {data.decode('utf-8')}")
            
if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    udp_server_port = 9002
    chat_room = ChatRoom()
    tcp_server = TCPServer(server_address, tcp_server_port)
    udp_server = UDPServer(server_address, udp_server_port, chat_room)
    thread_tcp_server = threading.Thread(target=tcp_server.handle_message)
    thread_udp_server = threading.Thread(target=udp_server.handle_message)
    thread_tcp_server.start()
    thread_udp_server.start()
    thread_tcp_server.join()
    thread_udp_server.join()
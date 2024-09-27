import socket
import secrets
import time
import threading
import copy
import struct

TIMEOUT = 300

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

                token = secrets.token_bytes(3)
                token_len_bytes = len(token).to_bytes(1, "big")
                ip_bytes = socket.inet_aton(client_address[0])
                ip_bytes_len = len(ip_bytes).to_bytes(1, "big")
                port_bytes = struct.pack('!H', client_address[1])
                data = token_len_bytes + ip_bytes_len + token + ip_bytes + port_bytes

                if operation == 1:
                    chat_rooms_obj.create_room(room_name, operation_payload, token, client_address)
                    connection.send(data)
                
                elif operation == 2:
                    chat_rooms_obj.join_room(room_name, operation_payload, token, client_address)
                    connection.send(data)

            except Exception as e:
                print('Error: ' + str(e))

            finally:
                print("Closing current connection")
                connection.close()


class UDPServer:
    def __init__(self, server_address, server_port, chat_rooms_obj):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = server_address
        self.server_port = server_port
        self.chat_rooms_obj = chat_rooms_obj
        self.TIMEOUT = 300
        self.sock.bind((server_address, server_port))
    
    def handle_message(self):
        while True:
            # クライアントからのメッセージ受信
            data, client_address = self.sock.recvfrom(4096)

            header = data[:2]
            room_name_size = int.from_bytes(header[:1], "big")
            token_size = int.from_bytes(header[1:2], "big")

            body = data[2:]
            room_name = body[:room_name_size].decode("utf-8")
            token = body[room_name_size : room_name_size + token_size]
            message = body[room_name_size + token_size:].decode("utf-8")

            user_name = self.chat_rooms_obj.chat_rooms[room_name]['members'][token][0][0]
            user_name_bytes = user_name.encode("utf-8")
            user_name_bytes_len = len(user_name_bytes)
            print(f"[{user_name}] {message}")

            # クライアントからの最新メッセージ受信時間を更新
            self.chat_rooms_obj.chat_rooms[room_name]['members'][token][1] = time.time()

            # 各クライアントへメッセージ送信
            message_bytes = message.encode("utf-8")
            data = user_name_bytes_len.to_bytes(1, "big") + user_name_bytes + message_bytes

            for client_token in self.chat_rooms_obj.chat_rooms[room_name]['members'].keys():
                if client_token != token:
                    destination_client_address = self.chat_rooms_obj.chat_rooms[room_name]['members'][client_token][0][1]
                    try:
                        self.sock.sendto(data, destination_client_address)
                    except Exception as e:
                        print(f"クライアントへメッセージを送信できませんでした: {e}")
            

    
    def remove_inactive_clients(self):
        while True:
            current_time = time.time()
            copy_chat_rooms = copy.deepcopy(self.chat_rooms_obj.chat_rooms)
            for chat_room in copy_chat_rooms.keys():
                for client_token in copy_chat_rooms[chat_room]['members'].keys():
                    if current_time - copy_chat_rooms[chat_room]['members'][client_token][1] > TIMEOUT:
                        print(f"クライアント {copy_chat_rooms[chat_room]['members'][client_token][0][1]} がタイムアウトしました。")
                        message = "timeout".encode("utf-8")
                        # 削除されたクライアントがホストの場合はチャットルームも閉じる
                        if client_token in copy_chat_rooms[chat_room]['host']:
                            for client_token_sub in copy_chat_rooms[chat_room]['members'].keys():
                                self.sock.sendto(message, (copy_chat_rooms[chat_room]['members'][client_token_sub][0][1], self.client_port))
                            del self.chat_rooms[chat_room]
                        else:
                            self.sock.sendto(message, (copy_chat_rooms[chat_room]['members'][client_token_sub][0][1], self.client_port))
                            del self.chat_rooms_obj[chat_room]['members'][client_token]

            time.sleep(1)

class ChatRoom:
    def __init__(self):
        self.chat_rooms = {}
    
    def create_room(self, room_name, operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            raise ValueError(f'{room_name}は既に存在しています')
        else:
            self.chat_rooms[room_name] = {'host' : None,  'members' : None}
            self.chat_rooms[room_name]['host'] = {token : (operation_payload, client_address)}
            self.chat_rooms[room_name]['members'] = {token : [(operation_payload, client_address), time.time()]}
        
        print(self.chat_rooms)
    
    def join_room(self, room_name, operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            self.chat_rooms[room_name]['members'][token] = [(operation_payload, client_address), time.time()]
        else:
            raise KeyError(f'{room_name}は見つかりませんでした')
        
        print(self.chat_rooms)



if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    udp_server_port = 9002
    chat_rooms_obj = ChatRoom()
    tcp_server = TCPServer(server_address, tcp_server_port)
    udp_server = UDPServer(server_address, udp_server_port, chat_rooms_obj)
   
    thread_tcp_server = threading.Thread(target=tcp_server.handle_message)    
    thread_udp_server = threading.Thread(target=udp_server.handle_message)
    thread_tcp_server.start()
    threading.Thread(target=udp_server.remove_inactive_clients, daemon=True).start() 
    thread_udp_server.start()
    thread_tcp_server.join()
    thread_udp_server.join()

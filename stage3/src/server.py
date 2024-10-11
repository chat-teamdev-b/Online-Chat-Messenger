import socket
import secrets
import time
import threading
import copy
import struct
import os
import json
import hashlib


class TCPServer:
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        print('Starting up on {}'.format(server_address))

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((server_address, server_port))
        self.sock.listen()
    
    def handle_message(self):
        while True:
            connection, client_address = self.sock.accept()
            try:
                print('connection from', client_address)

                header = connection.recv(32)

                room_name_size = int.from_bytes(header[:1], "big")
                operation = int.from_bytes(header[1:2], "big")
                state = int.from_bytes(header[2:3], "big")
                json_operation_payload_size = int.from_bytes(header[3:32], "big")
                print(f"state: {state}")

                body = connection.recv(room_name_size + json_operation_payload_size)
                room_name = body[:room_name_size].decode("utf-8")
                json_operation_payload = json.loads(body[room_name_size:].decode("utf-8"))

                token = secrets.token_bytes(3)
                token_len_bytes = len(token).to_bytes(1, "big")
                ip_bytes = socket.inet_aton(client_address[0])
                ip_bytes_len = len(ip_bytes).to_bytes(1, "big")
                port_bytes = struct.pack('!H', client_address[1])
                data = token_len_bytes + ip_bytes_len + token + ip_bytes + port_bytes
                if state == 0x01: # リクエスト
                    if operation == 1:
                        chat_rooms_obj.create_room(room_name, json_operation_payload, token, client_address)
                    
                    elif operation == 2:
                        chat_rooms_obj.join_room(room_name, json_operation_payload, token, client_address)
                    
                    response_state = bytes([0x00]) # 成功
                    data = response_state + data
                    connection.send(data)
            
            except ValueError as ve:
                print('Error: ' + str(ve))
                if str(ve) == f'ルーム{room_name}は既に存在しています':
                    response_state = bytes([0x03]) # ルームは既に存在します。
                else:
                    response_state = bytes([0x04]) # パスワードが間違っています。

                connection.send(response_state)
            
            except KeyError as ke:
                print('Error: ' + str(ke))
                response_state = bytes([0x05]) # ルームが見つかりません。
                connection.send(response_state)


            except Exception as e:
                print('Error: ' + str(e))
                response_state = bytes([0x06]) # エラー
                connection.send(response_state)

            finally:
                print("Closing current connection")
                connection.close()

class ChatRoom:
    def __init__(self):
        self.chat_rooms = {}
    
    # チャットルーム作成
    def create_room(self, room_name, json_operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            raise ValueError(f'ルーム{room_name}は既に存在しています')
        else:
            user_name = json_operation_payload.get('user_name')
            password = json_operation_payload.get('password')
            if password == None:
                hashed_password = None
            else:
                password_bytes = password.encode('utf-8')
                hash_object = hashlib.sha256(password_bytes)
                hashed_password = hash_object.hexdigest()

            self.chat_rooms[room_name] = {'host' : None,  'members' : None, 'hashed_password' : hashed_password}
            self.chat_rooms[room_name]['host'] = {token : (user_name, client_address)}
            self.chat_rooms[room_name]['members'] = {token : [(user_name, client_address), time.time()]}
        
        print(self.chat_rooms)
    
    # チャットルーム参加
    def join_room(self, room_name, json_operation_payload, token, client_address):
        if room_name in self.chat_rooms:
            password = json_operation_payload.get('password')
            if password == None:
                hashed_password = None
            else:
                password_bytes = password.encode('utf-8')
                hash_object = hashlib.sha256(password_bytes)
                hashed_password = hash_object.hexdigest()

            if self.chat_rooms[room_name]['hashed_password'] == hashed_password:
                user_name = json_operation_payload.get('user_name')
                self.chat_rooms[room_name]['members'][token] = [(user_name, client_address), time.time()]
            else:
                raise ValueError("パスワードが間違っています。")
        else:
            raise KeyError(f'ルーム{room_name}は見つかりませんでした')
        
        print(self.chat_rooms)



if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    udp_server_port = 9002
    chat_rooms_obj = ChatRoom()
    tcp_server = TCPServer(server_address, tcp_server_port)
    # udp_server = UDPServer(server_address, udp_server_port, chat_rooms_obj)
    thread_tcp_server = threading.Thread(target=tcp_server.handle_message)    
    # thread_udp_server = threading.Thread(target=udp_server.handle_message)
    thread_tcp_server.start()
    # threading.Thread(target=udp_server.remove_inactive_clients, daemon=True).start() 
    # thread_udp_server.start()
    thread_tcp_server.join()
    # thread_udp_server.join()
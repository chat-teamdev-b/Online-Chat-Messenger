import socket
import secrets
import time
import threading
import copy
import struct
import os
import json
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP


class TCPServer:
    def __init__(self, server_address, server_port, chat_rooms_obj, server_public_key):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.chat_rooms_obj = chat_rooms_obj
        self.server_public_key = server_public_key
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
                port_bytes_len = len(port_bytes).to_bytes(1, "big")
                ex_server_public_key = self.server_public_key.export_key()

                data = token_len_bytes + ip_bytes_len + port_bytes_len + token + ip_bytes + port_bytes + ex_server_public_key

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




class UDPServer:
    def __init__(self, server_address, server_port, chat_rooms_obj, server_private_key):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = server_address
        self.server_port = server_port
        self.chat_rooms_obj = chat_rooms_obj
        self.server_private_key = server_private_key
        self.TIMEOUT = 30
        self.sock.bind((server_address, server_port))
    
    # クライアントからのメッセージを受信し、同じルーム内の全てのクライアントへ転送
    def handle_message(self):
        while True:
            # クライアントからのメッセージ受信
            cipherdata, client_address = self.sock.recvfrom(4096)

            decipher_rsa = PKCS1_OAEP.new(self.server_private_key)
            data = decipher_rsa.decrypt(cipherdata)

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

            # グループメンバーの情報を送信
            if message == 'getMembers':
                members = [value[0][0] for value in self.chat_rooms_obj.chat_rooms[room_name]['members'].values()]
                members_bytes =  json.dumps({'type': 'members', 'data': members}).encode("utf-8")
                ciphermessage = self.encrypt(members_bytes, room_name, token)
                self.sock.sendto(ciphermessage, client_address)
                continue
                

            # 各クライアントへメッセージ送信
            message_bytes = message.encode("utf-8")
            data = user_name_bytes_len.to_bytes(1, "big") + user_name_bytes + message_bytes

            for client_token in self.chat_rooms_obj.chat_rooms[room_name]['members'].keys():
                if client_token != token:
                    destination_client_address = self.chat_rooms_obj.chat_rooms[room_name]['members'][client_token][0][1]
                    print(destination_client_address)
                    cipherdata = self.encrypt(data, room_name, client_token)
                    try:
                        self.sock.sendto(cipherdata, destination_client_address)
                        print("送信完了")
                    except Exception as e:
                        print(f"クライアントへメッセージを送信できませんでした: {e}")


    # 各クライアントの公開鍵でメッセージを暗号化
    def encrypt(self, data, room_name, client_token):
        public_key_data = self.chat_rooms_obj.chat_rooms[room_name]['members'][client_token][0][2]
        public_key = RSA.import_key(public_key_data)
        cipher_rsa = PKCS1_OAEP.new(public_key)
        cipherdata = cipher_rsa.encrypt(data)
        
        return cipherdata          


    # 非アクティブなクライアントの退出処理
    def remove_inactive_clients(self):
        while True:
            current_time = time.time()
            copy_chat_rooms = copy.deepcopy(self.chat_rooms_obj.chat_rooms)
            for chat_room in copy_chat_rooms.keys():
                for client_token in copy_chat_rooms[chat_room]['members'].keys():

                    # クライアントからのメッセージ送信が一定時間されない場合、そのクライアントを退出させる
                    if current_time - copy_chat_rooms[chat_room]['members'][client_token][1] > self.TIMEOUT:
                        print(f"クライアント {copy_chat_rooms[chat_room]['members'][client_token][0][1]} がタイムアウトしました。")
                        message = "timeout".encode("utf-8")

                        # 削除されたクライアントがホストの場合はチャットルームごと閉じる
                        if client_token in copy_chat_rooms[chat_room]['host']:
                            for client_token_sub in copy_chat_rooms[chat_room]['members'].keys():
                                if client_token_sub != client_token:
                                    message = "nohost".encode("utf-8")
                                ciphermessage = self.encrypt(message, chat_room, client_token_sub)
                                self.sock.sendto(ciphermessage, copy_chat_rooms[chat_room]['members'][client_token_sub][0][1])
                            del self.chat_rooms_obj.chat_rooms[chat_room]

                        # それ以外の場合は対象のクライアントのみ退出させる
                        else:
                            ciphermessage = self.encrypt(message, chat_room, client_token)
                            self.sock.sendto(ciphermessage, copy_chat_rooms[chat_room]['members'][client_token][0][1])
                            del self.chat_rooms_obj.chat_rooms[chat_room]['members'][client_token]

            time.sleep(1)





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
            client_publicKey = json_operation_payload.get('client_publicKey')

            if password == None:
                hashed_password = None
            else:
                password_bytes = password.encode('utf-8')
                hash_object = hashlib.sha256(password_bytes)
                hashed_password = hash_object.hexdigest()

            self.chat_rooms[room_name] = {'host' : None,  'members' : None, 'hashed_password' : hashed_password}
            self.chat_rooms[room_name]['host'] = {token : (user_name, client_address)}
            self.chat_rooms[room_name]['members'] = {token : [(user_name, client_address, client_publicKey), time.time()]}
        
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
                client_publicKey = json_operation_payload.get('client_publicKey')
                self.chat_rooms[room_name]['members'][token] = [(user_name, client_address, client_publicKey), time.time()]
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

    # 秘密鍵と公開鍵作成
    server_private_key = RSA.generate(2048)
    server_public_key = server_private_key.publickey()

    tcp_server = TCPServer(server_address, tcp_server_port, chat_rooms_obj, server_public_key)
    udp_server = UDPServer(server_address, udp_server_port, chat_rooms_obj, server_private_key)
    thread_tcp_server = threading.Thread(target=tcp_server.handle_message)    
    thread_udp_server = threading.Thread(target=udp_server.handle_message)
    thread_tcp_server.start()
    threading.Thread(target=udp_server.remove_inactive_clients, daemon=True).start() 
    thread_udp_server.start()
    thread_tcp_server.join()
    thread_udp_server.join()
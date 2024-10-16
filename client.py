import socket
import sys
import threading
import os
import struct
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

class TCPClient:
    def __init__(self, server_address, server_port, public_key):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.public_key = public_key
        self.info = {}
    
    # ヘッダー作成
    def protocol_header(self, room_name_bytes_size, operation, state, json_string_payload_bytes_size):
        return room_name_bytes_size.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1,"big") + json_string_payload_bytes_size.to_bytes(29, "big")

    # ユーザー名入力
    def input_user_name(self):
        try:
            user_name = input("ユーザー名を入力してください: ")
            self.info["user_name"] =  user_name
            user_name_bytes = user_name.encode('utf-8')
            if len(user_name_bytes) > 2**29:
                print("ユーザー名は2**29バイト以下にしてください。")
                return self.input_user_name()
            elif len(user_name_bytes) == 0:
                return self.input_user_name()
            else:
                return user_name
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return self.input_user_name()

    # オペレーション入力    
    def input_operation(self):
        try:
            operation = int(input("1または2を入力してください (1 : チャットルームを作成, 2 : チャットルームに参加): "))
            if operation != 1 and operation != 2:
                return self.input_operation()
            return operation
        except ValueError:
            return self.input_operation()
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            return self.input_operation()
    
    # ルーム名入力
    def input_room_name(self, operation):
        if operation == 1:
            room_name = input("作成したいルーム名を入力してください: ")
        elif operation == 2:
            room_name = input("参加したいルーム名を入力してください: ")
        
        self.info["room_name"] = room_name
        room_name_bytes = room_name.encode('utf-8')

        if len(room_name_bytes) > 2**8:
            print("ルーム名は2**8バイト以下にしてください")
            return self.input_room_name(operation)
        elif len(room_name_bytes) == 0:
            return self.input_room_name(operation)
        
        return room_name_bytes
    
    def input_password(self, operation):
        if operation == 1:
            try:
                option = input("パスワードを設定しますか(y/n): ").strip().lower()
                if option != "y" and option != "n":
                    return self.input_password()
                
                if option == "y":
                    while True:
                        password = input("パスワードを入力してください: ").strip()
                        if password:
                            return password
                        else:
                            print("パスワードは空にできません。もう一度入力してください。")
                else:
                    return None
                
            except Exception as e:
                print(f"エラーが発生しました: {e}")
                return self.input_password(operation)
        elif operation == 2:
            password = input("パスワードを入力してください(設定されていない場合は空白のままEnterを押してください): ").strip() or None
            return password

    

    # リクエスト送信    
    def send_message(self):
        user_name = self.input_user_name()
        operation = self.input_operation()
        room_name_bytes = self.input_room_name(operation)
        room_name_bytes_size = len(room_name_bytes)

        password = self.input_password(operation)
        public_key = self.public_key.export_key().decode('utf-8')

        json_payload = {
            "user_name": user_name,
            "password": password,
            "public_key": public_key
        }
        json_string_payload_bytes = json.dumps(json_payload).encode('utf-8')
        json_string_payload_bytes_size = len(json_string_payload_bytes)

        state = 0x01 # リクエスト
        header = self.protocol_header(room_name_bytes_size, operation, state, json_string_payload_bytes_size)
        body = room_name_bytes + json_string_payload_bytes
        self.sock.send(header+body)
    
    def receive_message(self):
        self.sock.settimeout(10)
        try:
            response_state = self.sock.recv(1)[0]
            if response_state == 0x00:
                data = self.sock.recv(4096)
                token_size = int.from_bytes(data[0:1], "big")
                ip_size = int.from_bytes(data[1:2], "big")
                port_size = int.from_bytes(data[2:3], "big")
                header_size = 3
                token = data[header_size : header_size + token_size]
                decoded_ip = socket.inet_ntoa(data[header_size + token_size : header_size + token_size + ip_size])
                decoded_port = struct.unpack('!H', data[header_size + token_size + ip_size : header_size + token_size + ip_size + port_size])[0]
                client_address = (decoded_ip, decoded_port)
                ex_server_public_key = data[header_size + token_size + ip_size + port_size :]
                server_public_key = RSA.import_key(ex_server_public_key)

                self.info["token"] = token
                self.info["address_port"] = client_address
                self.info["server_public_key"] = server_public_key

                if token:
                    print(self.info)
            
            elif response_state == 0x03:
                print(f"ルーム{self.info['room_name']}は既に存在します。")
            
            elif response_state == 0x04:
                print("パスワードが間違っています。")
            
            elif response_state == 0x05:
                print(f"ルーム{self.info['room_name']}が見つかりません。")
            
            else:
                print("エラーが発生しました")

        except TimeoutError:
            print('Socket timeout, ending listening for server messages')
        
        finally:
            print('closing socket')
            self.sock.close()
    
    def start(self):
        try:
            self.sock.connect((self.server_address, self.server_port))
        except socket.error as err:
            print(err)
            sys.exit(1)
        
        self.send_message()
        self.receive_message()

        return self.info


class UDPClient:
    def __init__(self, server_address,  udp_server_port, info, private_key):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = server_address
        self.udp_server_port = udp_server_port
        self.info = info
        self.private_key = private_key
        self.sock.bind(info["address_port"])
    
    def protocol_header(self, room_name_bytes_len, token_bytes_len):
        return room_name_bytes_len.to_bytes(1, "big") + token_bytes_len.to_bytes(1, "big")
    
    # メッセージ送信
    def send_message(self):
        while True:
            message = input(f"[{self.info['user_name']}] ").strip()
            while message == "":
                print("\033[1A", end="") 
                message = input(f"[{self.info['user_name']}] ").strip()
            print("\033[1A\033[K", end="") 
            print(f"[{self.info['user_name']}] {message}")
            message_bytes = message.encode('utf-8')
            room_name_bytes = self.info["room_name"].encode('utf-8')
            room_name_bytes_len = len(room_name_bytes)
            token_bytes = self.info["token"]
            token_bytes_len = len(token_bytes)
            header = self.protocol_header(room_name_bytes_len, token_bytes_len)
            body = room_name_bytes + token_bytes + message_bytes
            data = header + body
            cipher_rsa = PKCS1_OAEP.new(self.info["server_public_key"])
            cipherdata = cipher_rsa.encrypt(data)

            self.sock.sendto(cipherdata, (self.server_address, self.udp_server_port))
    
    # メッセージ受信
    def receive_message(self):
        while True:
            cipherdata, _ = self.sock.recvfrom(4096)
            decipher_rsa = PKCS1_OAEP.new(self.private_key)
            data = decipher_rsa.decrypt(cipherdata)

            # タイムアウト処理
            if data.decode('utf-8') == "timeout":
                print("タイムアウトしました")
                self.sock.close()
                os._exit(0)
                break
            elif data.decode('utf-8') == "nohost":
                print("ホストが退出しました")
                self.sock.close()
                os._exit(0)
                break
            
            user_name_bytes_len = int.from_bytes(data[0:1], "big")
            user_name = data[1 : 1 + user_name_bytes_len].decode('utf-8')
            message = data[1 + user_name_bytes_len:].decode('utf-8')
            print("\033[1A") 
            print(f'[{user_name}] {message}')
            print(f'[{self.info["user_name"]}] ', end='', flush=True)



    def start(self):
        send_thread = threading.Thread(target=self.send_message)
        receive_thread = threading.Thread(target=self.receive_message)
        send_thread.start()
        receive_thread.start()
        send_thread.join()
        receive_thread.join()



if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    udp_server_port = 9002

    # 秘密鍵と公開鍵作成
    private_key = RSA.generate(2048)
    public_key = private_key.publickey()
    
    tcp_client = TCPClient(server_address, tcp_server_port, public_key)
    info = tcp_client.start()

    if "token" in info.keys():
        udp_client = UDPClient(server_address, udp_server_port, info, private_key)
        udp_client.start()

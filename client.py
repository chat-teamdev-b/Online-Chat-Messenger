import socket
import sys
import threading

class TCPClient:
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.info = {}
    
    # ヘッダー作成
    def protocol_header(self, room_name_bytes_size, operation, state, user_name_bytes_size):
        return room_name_bytes_size.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1,"big") + user_name_bytes_size.to_bytes(29, "big")

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
                return user_name_bytes
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

    # リクエスト送信    
    def send_message(self):
        user_name_bytes = self.input_user_name()
        user_name_bytes_size = len(user_name_bytes)
        operation = self.input_operation()
        room_name_bytes = self.input_room_name(operation)
        room_name_bytes_size = len(room_name_bytes)
        state = 0x01 # リクエスト
        header = self.protocol_header(room_name_bytes_size, operation, state, user_name_bytes_size)
        body = room_name_bytes + user_name_bytes
        self.sock.send(header+body)
    
    def receive_message(self):
        self.sock.settimeout(10)
        try:
            response_state = self.sock.recv(1)[0]
            if response_state == 0x00:
                token = self.sock.recv(255)
                self.info["token"] = token
                print(self.info)
            elif response_state == 0x03:
                print(f"ルーム{self.info["room_name"]}は既に存在します。")
            elif response_state == 0x04:
                print(f"ルーム{self.info["room_name"]}が見つかりません。")
            else:
                print("エラーが発生しました.。")
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


# class UDPClient:



if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    # udp_server_port = 9002

    tcp_client = TCPClient(server_address, tcp_server_port)
    info = tcp_client.start()

    # if "token" in info.keys():
        # udp_client = UDPClient(server_address, udp_server_port, info)
        # udp_client.start()
import socket
import sys
import threading

class TCPClient:
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.info = {}
    
    def protocol_header(self, room_name_bytes_len, operation, state, user_name_bytes_len):
        return room_name_bytes_len.to_bytes(1, "big") + operation.to_bytes(1, "big") + state.to_bytes(1,"big") + user_name_bytes_len.to_bytes(29, "big")

    def input_user_name(self):
        user_name = input("ユーザー名を入力してください: ")
        self.info["user_name"] =  user_name
        user_name_bytes = user_name.encode('utf-8')
        if len(user_name_bytes) > 2**29:
            print("ルーム名は2**29バイト以下にしてください:")
            return self.input_room_name()
        elif len(user_name_bytes) == 0:
            return self.input_room_name()
        else:
            return user_name_bytes
        
    def input_operation(self):
        operation = int(input("1または2を入力してください (1 : チャットルームを作成, 2 : チャットルームに参加): "))
        if operation != 1 and operation != 2:
            return self.input_operation()
        return operation

    def input_room_name(self, operation):
        if operation == 1:
            room_name = input("作成したいルーム名を入力してください: ")
            self.info["room_name"] = room_name
            room_name_bytes = room_name.encode('utf-8')
            if len(room_name_bytes) > 2**8:
                print("ルーム名は2**8バイト以下にしてください")
                return self.input_room_name()
            elif len(room_name_bytes) == 0:
                return self.input_room_name()
            return room_name_bytes
        
        elif operation == 2:
            room_name = input("参加したいルーム名を入力してください: ")
            self.info["room_name"] = room_name
            room_name_bytes = room_name.encode('utf-8')
            if len(room_name_bytes) > 2**8:
                print("ルーム名は2**8バイト以下にしてください")
                return self.input_room_name()
            elif len(room_name_bytes) == 0:
                return self.input_room_name()
            return room_name_bytes
        
    def send_message(self):
        user_name_bytes = self.input_user_name()
        user_name_bytes_len = len(user_name_bytes)
        operation = self.input_operation()
        room_name_bytes = self.input_room_name(operation)
        room_name_bytes_len = len(room_name_bytes)
        header = self.protocol_header(room_name_bytes_len, operation, 1, user_name_bytes_len)
        body = room_name_bytes + user_name_bytes
        self.sock.send(header+body)
    
    def receive_message(self):
        self.sock.settimeout(10)
        try:
            while True:
                token = self.sock.recv(4096)
                self.info["token"] = token
                if token:
                    print(self.info)
                else:
                    break
        except(TimeoutError):
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

    # udp_client = UDPClient(server_address, udp_server_port, info)
    # udp_client.start()
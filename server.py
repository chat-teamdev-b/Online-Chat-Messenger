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


# class UDPServer:



if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    # udp_server_port = 9002
    chat_room = ChatRoom()
    tcp_server = TCPServer(server_address, tcp_server_port)
    # udp_server = UDPServer(server_address, udp_server_port, chat_room)
    thread_tcp_server = threading.Thread(target=tcp_server.handle_message)
    # thread_udp_server = threading.Thread(target=udp_server.handle_message)
    thread_tcp_server.start()
    # thread_udp_server.start()
    thread_tcp_server.join()
    # thread_udp_server.join()

import socket
import threading

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = input("Type in the server's address to connect to: ")
server_port = 9001

def receive_messages():
    while True:
        data, server = sock.recvfrom(4096)
        usernamelen = data[0]
        username = data[1:usernamelen+1].decode('utf-8')
        message = data[usernamelen+1:].decode('utf-8')
        print("\033[1A") 
        print(f'{username}: {message}')

threading.Thread(target=receive_messages, daemon=True).start()

# try:
username = input('Enter your username: ')
username_bytes = username.encode('utf-8')
usernamelen = len(username_bytes)
message = f'{username} has connected'
message_bytes = message.encode('utf-8')
full_message_bytes = bytes([usernamelen]) + username_bytes + message_bytes
sock.sendto(full_message_bytes, (server_address, server_port))

if usernamelen > 255:
    raise Exception('Your username must be below 255 bytes.')

while True:
    message = input('')
    print("\033[1A", end="") 
    print(f'{username}: {message}')
    message_bytes = message.encode('utf-8')
    full_message_bytes = bytes([usernamelen]) + username_bytes + message_bytes
    sent = sock.sendto(full_message_bytes, (server_address, server_port))

# finally:
#     print('closing socket')
#     sock.close()
const net = require('net');

class TCPClient {
    constructor(host, port) {
        this.host = host;
        this.port = port;
        this.client = new net.Socket();
    }

    connect() {
        this.client.connect(this.port, this.host, () => {
            this.appendMessage('サーバーに接続しました');
            const message = this.createMessage();
            this.sendMessage(message);
        });

        this.client.on('data', (data) => {
            console.log('datalen:', data.length);
            console.log('rawdata:', data);
            console.log('バイト列の内容（16進数）:', data.toString('hex'));
            const receivedString = data.toString('utf-8');
            console.log('data:', receivedString);
            this.appendMessage(`受信: ${data.toString()}`);
        });

        this.client.on('error', (err) => {
            this.appendMessage(`エラー: ${err.message}`);
        });

        this.client.on('close', () => {
            this.appendMessage('接続が閉じられました');
        });
    }

    createMessage() {
        const userName = document.getElementById('username').value;
        console.log(userName);
        const operation = document.getElementById('action').value === 'create' ? 1 : 2;
        console.log(userName);
        const roomNameBytes = Buffer.from(document.getElementById('roomname').value, 'utf-8');
        const roomNameBytesSize = roomNameBytes.length;

        const password = document.getElementById('password').value;
        const jsonPayload = {
            user_name: userName,
            password: password
        };
        const jsonStringPayloadBytes = Buffer.from(JSON.stringify(jsonPayload), 'utf-8');
        console.log(jsonStringPayloadBytes)
        const jsonStringPayloadBytesSize = jsonStringPayloadBytes.length;
        console.log("json_operation_payload_size")
        console.log(jsonStringPayloadBytesSize)

        const header = this.protocolHeader(roomNameBytesSize, operation, 1, jsonStringPayloadBytesSize);
        return Buffer.concat([header, roomNameBytes, jsonStringPayloadBytes]);
    }

    protocolHeader(roomNameBytesSize, operation, state, jsonStringPayloadBytesSize) {
      const roomNameSizeBytes = Buffer.alloc(1);
      roomNameSizeBytes.writeUInt8(roomNameBytesSize);
  
      const operationSizeBytes = Buffer.alloc(1);
      operationSizeBytes.writeUInt8(operation);
  
      const stateSizeBytes = Buffer.alloc(1);
      stateSizeBytes.writeUInt8(state);

      const jsonStringPayloadSizeBytes = Buffer.alloc(29);
      const bigIntBytes = jsonStringPayloadBytesSize.toString(16).padStart(29 * 2, '0');
      const byteArray = Buffer.from(bigIntBytes, 'hex');
  
      byteArray.copy(jsonStringPayloadSizeBytes, 29 - byteArray.length);
  
      return Buffer.concat([roomNameSizeBytes, operationSizeBytes, stateSizeBytes, jsonStringPayloadSizeBytes]);
  }
  
    sendMessage(message) {
        // console.log(jsonStringPayloadBytes)
        console.log("送信するメッセージ:", message);
        this.client.write(message);
    }

    appendMessage(message) {
        const chatDiv = document.getElementById('chat');
        const messageElement = document.createElement('div');
        messageElement.textContent = message;
        chatDiv.appendChild(messageElement);
    }

    close() {
        this.client.end();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const connectButton = document.getElementById('connect');
    const tcpClient = new TCPClient('0.0.0.0', 9001); // ローカルホストに接続

    connectButton.addEventListener('click', () => {
        tcpClient.connect();
    });
});
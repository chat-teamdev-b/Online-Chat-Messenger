const net = require('net');

class TCPClient {
    constructor(server_address, server_port) {
        this.server_address = server_address;
        this.server_port = server_port;
        this.client = new net.Socket();
        this.info = {};
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.client.connect(this.server_port, this.server_address, () => {
                this.appendMessage('サーバーに接続しました');
                const message = this.createMessage();
                this.sendMessage(message);
            });

            let success = false;

            this.client.on('data', (data) => {
                let offset = 0;

                // 0. statusを取得
                const status = data.readUInt8(offset);
                offset += 1;

                if (status === 0x00){
                    // 1. トークンの長さを取得
                    const tokenLen = data.readUInt8(offset);
                    offset += 1;
                
                    // 2. IPアドレスの長さを取得
                    const ipLen = data.readUInt8(offset);
                    offset += 1;
                
                    // 3. トークンを取得
                    const token = data.slice(offset, offset + tokenLen);
                    this.info['token'] = token;
                    offset += tokenLen;
                
                    // 4. IPアドレスを取得
                    const ipBytes = data.slice(offset, offset + ipLen);
                    const client_address = bytesToIp(ipBytes);
                    offset += ipLen;
                
                    // 5. ポート番号を取得
                    const client_port = data.readUInt16BE(offset);
                    offset += 2;
                    const client_address_port = (client_address, client_port);
                    this.info['client_address_port'] = client_address_port;
                
                    // 必要に応じて画面に表示
                    this.appendMessage(`受信:
                    status: ${status}
                    トークン長: ${tokenLen}
                    IP長: ${ipLen}
                    トークン: ${token.toString('hex')}
                    IP: ${client_address}
                    ポート: ${client_port}`);

                    success = true;
                }
                else if (status === 0x03){
                    this.appendMessage('ルームは既に存在します');
                    reject(new Error('ルームは既に存在します'));
                }
                else if (status === 0x04){
                    this.appendMessage('パスワードが間違っています');
                    reject(new Error('パスワードが間違っています'));
                }
                else if (status === 0x05){
                    this.appendMessage('ルームが見つかりません');
                    reject(new Error('ルームが見つかりません'));
                }
                else {
                    this.appendMessage('エラーが発生しました');
                    reject(new Error('エラーが発生しました'));
                }
            });
            

            this.client.on('error', (err) => {
                this.appendMessage(`エラー: ${err.message}`);
                reject(err);
                success = false;
            });

            this.client.on('close', () => {
                this.appendMessage('接続が閉じられました');
                if (success) resolve();
            });
        });
    }

    createMessage() {
        const userName = document.getElementById('username').value;
        this.info['user_name'] = userName;
        console.log(userName);

        const operation = document.getElementById('action').value === 'create' ? 1 : 2;
        console.log(operation);

        const roomname = document.getElementById('roomname').value;
        this.info['room_name'] = roomname;
        const roomNameBytes = Buffer.from(roomname, 'utf-8');
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
        console.log("送信するメッセージ:", message);
        this.client.write(message);
    }

    appendMessage(message) {
        const connectionMessagesDiv = document.getElementById('connectionMessages');
        const messageElement = document.createElement('div');
        messageElement.textContent = message;
        connectionMessagesDiv.appendChild(messageElement);
        connectionMessagesDiv.scrollTop = connectionMessagesDiv.scrollHeight;
    }

    close() {
        this.client.end();
    }
}

/**
 * バイトバッファをIPアドレス文字列に変換する関数
 * @param {Buffer} buffer - IPアドレスのバイトバッファ
 * @returns {string} ドット区切りのIPアドレス文字列
 */
function bytesToIp(buffer) {
    // IPv4の場合
    if (buffer.length === 4) {
        return Array.from(buffer).join('.');
    }
    // IPv6の場合（必要に応じて対応）
    else if (buffer.length === 16) {
        const segments = [];
        for (let i = 0; i < 16; i += 2) {
            segments.push(buffer.readUInt16BE(i).toString(16));
        }
        return segments.join(':');
    }
    // その他の場合
    else {
        return '不明なIP形式';
    }
}




const dgram = require('dgram');

class UDPClient {
    constructor(serverAddress, udpServerPort, info) {
        this.sock = dgram.createSocket('udp4');
        this.serverAddress = serverAddress;
        this.udpServerPort = udpServerPort;
        this.info = info;
        this.sock.bind(info.client_address_port);
    }

    protocolHeader(roomNameBytesLen, tokenBytesLen) {
        const buffer = Buffer.alloc(2);
        buffer.writeUInt8(roomNameBytesLen, 0);
        buffer.writeUInt8(tokenBytesLen, 1);
        return buffer;
    }

    sendMessage(message) {
        const messageBytes = Buffer.from(message, 'utf-8');
        const roomNameBytes = Buffer.from(this.info.room_name, 'utf-8');
        const roomNameBytesLen = roomNameBytes.length;
        const tokenBytes = Buffer.from(this.info.token);
        const tokenBytesLen = tokenBytes.length;
        const header = this.protocolHeader(roomNameBytesLen, tokenBytesLen);
        const body = Buffer.concat([roomNameBytes, tokenBytes, messageBytes]);
        this.sock.send(Buffer.concat([header, body]), this.udpServerPort, this.serverAddress, (err) => {
            if (err) {
                this.displayMessage(`メッセージ送信エラー: ${err.message}`);
            }
        });
    }

    receiveMessage() {
        this.sock.on('message', (data) => {
            console.log("sssss")
            const userNameBytesLen = data.readUInt8(0);
            const userName = data.slice(1, 1 + userNameBytesLen).toString('utf-8');
            const messageContent = data.slice(1 + userNameBytesLen).toString('utf-8');
            this.displayMessage(`[${userName}] ${messageContent}`);
        });
    }

    displayMessage(message, isSent = false) {
        const chatDiv = document.getElementById('chat');
        const messageElement = document.createElement('div');
        messageElement.textContent = message;

        // 送信されたメッセージを右寄せし、背景色を設定
        if (isSent) {
            messageElement.classList.add('sent-message');
        } else {
            // 受信メッセージの背景色を設定
            messageElement.classList.add('received-message');
        }

        chatDiv.appendChild(messageElement);
        chatDiv.scrollTop = chatDiv.scrollHeight; // 最新メッセージにスクロール
    }

    start() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendMessage');
    
        sendButton.addEventListener('click', () => {
            const message = messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                this.displayMessage(`[${this.info.user_name}] ${message}`, true);
                messageInput.value = '';
            }
        });
        
        this.receiveMessage();  
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const connectButton = document.getElementById('connect');
    const connectionScreen = document.getElementById('connectionScreen');
    const chatScreen = document.getElementById('chatScreen');
    const exitButton = document.getElementById('exitChat');
    const connectionMessagesDiv = document.getElementById('connectionMessages');
    const chatDiv = document.getElementById('chat');
    const usernameInput = document.getElementById('username');
    const roomnameInput = document.getElementById('roomname');
    const passwordInput = document.getElementById('password');
    const actionSelect = document.getElementById('action');



    const tcpClient = new TCPClient('0.0.0.0', 9001);

    connectButton.addEventListener('click', async () => {
        try {
            await tcpClient.connect(); 

            if ("token" in tcpClient.info) {
                const udpClient = new UDPClient('0.0.0.0', 9002, tcpClient.info);
                udpClient.displayMessage('UDP接続が開始されました。');
                udpClient.start();

                // 接続画面を非表示にし、チャット画面を表示
                connectionScreen.classList.add('d-none');
                chatScreen.classList.remove('d-none');
            }
        } catch (error) {
            console.error('接続に失敗しました:', error);
            tcpClient.appendMessage('接続に失敗しました。');
        }
    });

    exitButton.addEventListener('click', () => {
        // チャット画面を非表示にし、接続画面を表示
        chatScreen.classList.add('d-none');
        connectionScreen.classList.remove('d-none');
        
        connectionMessagesDiv.innerHTML = '';
        chatDiv.innerHTML = '';

        // 接続画面の入力フィールドをリセット
        usernameInput.value = '';
        roomnameInput.value = '';
        passwordInput.value = '';
        actionSelect.selectedIndex = 0;
    });
});
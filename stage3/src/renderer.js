const net = require('net');
const NodeRSA = require('node-rsa');
const crypto = require('crypto');

class TCPClient {
    constructor(server_address, server_port, client_publicKey) {
        this.last_message = '';
        this.server_address = server_address;
        this.server_port = server_port;
        this.client_publicKey = client_publicKey;
        this.client = new net.Socket();
        this.info = {};
    }

    connect() {
        return new Promise((resolve, reject) => {
            this.client.connect(this.server_port, this.server_address, () => {
                this.last_message = this.appendMessage('サーバーに接続しました', this.last_message);
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
                    // トークンの長さを取得
                    const tokenLen = data.readUInt8(offset);
                    offset += 1;
                
                    // IPアドレスの長さを取得
                    const ipLen = data.readUInt8(offset);
                    offset += 1;

                    // Port番号の長さを取得
                    const portLen = data.readUInt8(offset);
                    offset += 1;
                    console.log(portLen)

                    // トークンを取得
                    const token = data.slice(offset, offset + tokenLen);
                    this.info['token'] = token;
                    offset += tokenLen;

                    // IPアドレスを取得
                    const ipBytes = data.slice(offset, offset + ipLen);
                    const client_address = bytesToIp(ipBytes);
                    offset += ipLen;

                    // ポート番号を取得
                    const portBytes = data.slice(offset, offset + portLen); 
                    const client_port = portBytes.readUInt16BE(0);
                    offset += portLen;
                    const client_address_port = (client_address, client_port);
                    this.info['client_address_port'] = client_address_port;

                    // サーバの公開鍵を取得
                    const ex_server_public_key = data.slice(offset);
                    const server_publicKey = crypto.createPublicKey({
                        key: ex_server_public_key,
                        format: 'pem',
                        type: 'spki',
                    });
                    this.info['server_publicKey'] = server_publicKey;
                
                    // 必要に応じて画面に表示
                    this.last_message = this.appendMessage(`受信:
                    status: ${status}
                    トークン長: ${tokenLen}
                    IP長: ${ipLen}
                    トークン: ${token.toString('hex')}
                    IP: ${client_address}
                    ポート: ${client_port}`, this.last_message);

                    success = true;
                }
                else if (status === 0x03){
                    this.last_message = this.appendMessage('ルームは既に存在します', this.last_message);
                    reject(new Error('ルームは既に存在します'));
                }
                else if (status === 0x04){
                    this.last_message = this.appendMessage('パスワードが間違っています', this.last_message);
                    reject(new Error('パスワードが間違っています'));
                }
                else if (status === 0x05){
                    this.last_message = this.appendMessage('ルームが見つかりません', this.last_message);
                    reject(new Error('ルームが見つかりません'));
                }
                else {
                    this.last_message = this.appendMessage('エラーが発生しました', this.last_message);
                    reject(new Error('エラーが発生しました'));
                }
            });
            

            this.client.on('error', (err) => {
                this.last_message = this.appendMessage(`エラー: ${err.message}`, this.last_message);
                reject(err);
                success = false;
            });

            this.client.on('close', () => {
                this.last_message = this.appendMessage('接続が閉じられました', this.last_message);
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
            password: password,
            client_publicKey: this.client_publicKey
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

    appendMessage(message, last_message) {
        if(message !== last_message){
            const connectionMessagesDiv = document.getElementById('connectionMessages');
            const messageElement = document.createElement('div');
            messageElement.textContent = message;
            connectionMessagesDiv.appendChild(messageElement);
            connectionMessagesDiv.scrollTop = connectionMessagesDiv.scrollHeight;
        }
        return message
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
    constructor(serverAddress, udpServerPort, info, client_privateKey) {
        this.sock = dgram.createSocket('udp4');
        this.serverAddress = serverAddress;
        this.udpServerPort = udpServerPort;
        this.info = info;
        this.client_privateKey = client_privateKey;
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
        const data = Buffer.concat([header, body])
        const cipherdata = this.encryptWithPublicKey(this.info['server_publicKey'], data);
        this.sock.send(cipherdata, this.udpServerPort, this.serverAddress, (err) => {
            if (err) {
                this.displayMessage(`メッセージ送信エラー: ${err.message}`);
            }
        });
    }

    encryptWithPublicKey(server_publicKey, data) {
        const encryptedData = crypto.publicEncrypt(
            {
                key: server_publicKey,
                padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
                oaepHash: "sha1"
            },
            Buffer.from(data)
        );

        return encryptedData;
    }

    receiveMessage() {
        this.sock.on('message', (encryptedData) => {
            const data = this.decryptWithPrivateKey(encryptedData, this.client_privateKey);
    
            const dataStr = data.toString('utf-8');
            console.log(dataStr)
            if (dataStr === "timeout") {
                this.displayMessage("タイムアウトしました");
                this.sock.close();
                // ルーム作成・参加ページへ画面遷移処理
    
            } else if (dataStr === "nohost") {
                this.displayMessage("ホストが退出しました");
                this.sock.close();
                // ルーム作成・参加ページへ画面遷移処理
    
            }
    
            const userNameBytesLen = data.readUInt8(0);
            const userName = data.slice(1, 1 + userNameBytesLen).toString('utf-8');
            const messageContent = data.slice(1 + userNameBytesLen).toString('utf-8');
            this.displayMessage(messageContent, false, userName);
        });
    }
    

    // 復号関数
    decryptWithPrivateKey(encryptedData, privateKey) {
        const privateKeyObject = crypto.createPrivateKey(privateKey);

        const decryptedData = crypto.privateDecrypt(
            {
                key: privateKeyObject,
                padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
                oaepHash: "sha1"
            },
            encryptedData
        );

        return decryptedData;
    }

    displayMessage(message, isSent = false, userName = null) {
        const chatDiv = document.getElementById('chat');
        const messageWrapper = document.createElement('div');
        const userElement = document.createElement('div');
        const messageElement = document.createElement('div');
        
        userElement.textContent = isSent ? this.info.user_name : userName;  
        messageElement.textContent = message;
        
        messageWrapper.classList.add('message-wrapper');
        userElement.classList.add('message-user');
        messageElement.classList.add('message');
        
        if (isSent) {
            messageWrapper.classList.add('sent-message-wrapper');
            messageElement.classList.add('sent-message');
        } else {
            messageWrapper.classList.add('received-message-wrapper');
            messageElement.classList.add('received-message');
        }
        
        messageWrapper.appendChild(userElement);
        messageWrapper.appendChild(messageElement);
        chatDiv.appendChild(messageWrapper);
        chatDiv.scrollTop = chatDiv.scrollHeight; 
    }
    
    start() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendMessage');

    
        sendButton.addEventListener('click', () => {
            const message = messageInput.value.trim();
            if (message) {
                this.sendMessage(message);
                this.displayMessage(` ${message}`, true);
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
    const textCenter = document.getElementsByClassName('text-center'); // text-center要素の取得

    // 2048ビットのRSA鍵ペアを生成
    const key = new NodeRSA({ b: 2048 });
    
    // 秘密鍵と公開鍵を取得
    const client_privateKey = key.exportKey('private');  // 秘密鍵
    const client_publicKey = key.exportKey('public');    // 公開鍵

    const tcpClient = new TCPClient('0.0.0.0', 9001, client_publicKey);

    connectButton.addEventListener('click', async () => {
        try {
            await tcpClient.connect(); 

            if ("token" in tcpClient.info) {
                const udpClient = new UDPClient('0.0.0.0', 9002, tcpClient.info, client_privateKey);
                udpClient.displayMessage('UDP接続が開始されました。');
                udpClient.start();

                // text-centerの内容をroomnameに書き換える
                textCenter[0].innerHTML = roomnameInput.value;


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
        textCenter[0].innerHTML = "チャットルーム";
        usernameInput.value = '';
        roomnameInput.value = '';
        passwordInput.value = '';
        actionSelect.selectedIndex = 0;
    });
});

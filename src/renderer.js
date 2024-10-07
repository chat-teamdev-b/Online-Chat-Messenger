const { ipcRenderer } = require('electron');

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('run-python').addEventListener('click', async () => {
        const user_name = document.getElementById('user_name').value;
        const room_name = document.getElementById('room_name').value;
        const operation = document.querySelector('input[name="operation"]:checked').value;

        const data = {
            user_name: user_name,
            room_name: room_name,
            operation: operation
        };

        const result = await ipcRenderer.invoke('client', data);
        document.getElementById('output').innerText = JSON.stringify(result, null, 2);
    });
});

// Pythonスクリプトからのメッセージを受信
window.api.on('return_data', (data) => {
    const outputElement = document.getElementById('output');
    outputElement.innerText += `Received: ${JSON.stringify(data)}\n`;
});

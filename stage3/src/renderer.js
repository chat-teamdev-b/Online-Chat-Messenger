// renderer.js
const net = require('net');

function sendDataToServer(inputData) {
  const client = new net.Socket();

  client.connect(65432, 'localhost', () => {
    console.log('Connected to server');
    client.write(inputData);
  });

  client.on('data', (data) => {
    console.log('Received: ' + data);
    const responseElement = document.createElement('div');
    responseElement.innerText = data.toString();
    document.getElementById('responseHistory').appendChild(responseElement);
    client.destroy(); // Close the connection after receiving the response
  });

  client.on('close', () => {
    console.log('Connection closed');
  });

  client.on('error', (err) => {
    console.error('Error: ' + err.message);
  });
}
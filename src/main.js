const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { PythonShell } = require('python-shell');

let mainWindow;
const createWindow = () => {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            // preload: path.join(__dirname, 'preload.js'),  // 必要に応じてコメントアウトまたは削除
            nodeIntegration: true,  // 注意: nodeIntegration を有効にするとセキュリティリスクが増すため、必要に応じて適切な対策を講じる
            contextIsolation: false  // Electron 12以上の場合、これが必要になる場合があります
        },
    });
    mainWindow.loadFile('index.html');
    mainWindow.webContents.openDevTools();
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
};

app.whenReady().then(() => {
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// IPCハンドラを設定
ipcMain.handle('client', async (event, data) => {
    var options = {
        args: [data]  // 引数としてデータを渡す場合
    };

    let pyshell = new PythonShell('client.py', options);
    
    // メッセージを受信
    pyshell.on('message', function (message) {
        event.sender.send('return_data', message);
    });

    // エラー処理
    pyshell.on('error', function (err) {
        console.error(err);
        event.sender.send('return_data', { error: err.message });
    });

    // 終了処理
    pyshell.end(function (err, code, signal) {
        if (err) {
            console.error(err);
            event.sender.send('return_data', { error: err.message });
        }
    });
});

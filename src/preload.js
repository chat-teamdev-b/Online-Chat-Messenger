const{contextBridge, ipcRenderer} = require("electron")
contextBridge.exposeInMainWorld('api',{
    send: async(data) => await ipcRenderer.invoke('hoge',data),
    on:(channel, func) => {
        ipcRenderer.on(channel,(event, data) =>func(data))
    }
})
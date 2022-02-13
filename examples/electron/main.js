const {app, BrowserWindow, Menu, Tray} = require('electron')
const nativeImage = require('electron').nativeImage
const ipc = require('electron').ipcMain;
const path = require('path');
const pyhtmlgui = require('./pyhtmlgui.js');

let mainWindow = null;

function createWindow () {
  pyhtmlgui.start();
  mainWindow = new BrowserWindow({
    frame: true,
    webPreferences: {
      nodeIntegration: true
    },
  });
  //mainWindow.webContents.openDevTools()
  mainWindow.on('minimize',function(event){
    mainWindow.webContents.send('python_bridge', {'message': 'minimize'}); // Send message to python main view class on_electron_message() method
  });
  setTimeout(function() {
    mainWindow.loadURL(pyhtmlgui.get_start_url());
  }, 1000);
}

app.on('ready', () => {
  pyhtmlgui.init();
  createWindow();
})

app.on('window-all-closed', function () {
  // Quit when all windows are closed.
  // On macOS it is common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') app.quit()
  mainWindow = null
})

app.on('activate', function () {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (mainWindow === null){
    createWindow()
  }else{
    mainWindow.show()
  }
})


pyhtmlgui.add_public_functions({
  eval_script: function(script, args) {
    let f = undefined;
    eval('f = function(args){' + script + '}');
    return f(args);
  },
  exit: function (){
    app.quit();
    app.exit(0);
  },
  ping: function (){
    return "Pong from electron";
  }
  // ADD CUSTOM FUNCTIONS HERE
})


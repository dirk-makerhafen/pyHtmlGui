const {app, BrowserWindow, Menu, Tray} = require('electron')
const nativeImage = require('electron').nativeImage
const ipc = require('electron').ipcMain;
const path = require('path');
const pyhtmlgui = require('./pyhtmlgui.js');

let mainWindow = null;
pyhtmlgui.start(); // start early

function createWindow () {
  pyhtmlgui.start() // on osx window may be created multiple times, ensure python process is active
  mainWindow = new BrowserWindow({
    frame: true,
    webPreferences: {
      nodeIntegration: true
    },
    //icon: path.join(icon_path, "icon_256.png"),
  });
  mainWindow.webContents.openDevTools()
  mainWindow.loadURL(pyHtmlGui.get_start_url());
  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

app.on('ready', () => {
  pyhtmlgui.init_ipc();
  createWindow();
})

app.on('window-all-closed', function () {
  // Quit when all windows are closed.
  // On macOS it is common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', function () {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (mainWindow === null) createWindow()
})

pyhtmlgui.add_public_functions({
  eval_script: function(script, args) {
    const f = new Function("args", script);
    return f(args);
  },
  exit: function (){
    console.log("exit called ");
    app.quit();
    app.exit(0);
  },
  ping: function (){
    return "pong";
  }
  // ADD CUSTOM FUNCTIONS HERE
})


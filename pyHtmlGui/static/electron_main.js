// Modules to control application life and create native browser window
const {app, BrowserWindow, Menu, Tray} = require('electron')
const nativeImage = require('electron').nativeImage
const ipc = require('electron').ipcMain;
var path = require('path');
var fs = require('fs');

let start_url = undefined;
let resource_path = undefined;
let icon_path = undefined;

try { // if we are started with parameters in dev env
   start_url = process.argv[4];
   resource_path = process.argv[5];
   icon_path = path.join(resource_path, "img", "icons");
}catch (e) {}

if (resource_path === undefined){
  resource_path = app.getAppPath();
  icon_path = path.join(resource_path, "icons");
  let token_file = path.join(resource_path, "TOKEN");
  let token = fs.readFileSync(token_file);
  start_url = "127.0.0.1:8000/?token=" + token;
}

let mainWindow = null;
let tray = null;
let APPNAME = ""

// Disable menu
Menu.setApplicationMenu(false)

function createTray () { // not working
  tray = new Tray(nativeImage.createFromPath(path.join(icon_path, "icon_32.png")));
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Item1', type: 'radio' },
    { label: 'Item2', type: 'radio' },
    { label: 'Item3', type: 'radio', checked: true },
    { label: 'Item4', type: 'radio' }
  ])
  tray.setToolTip('This is my application.')
  tray.setContextMenu(contextMenu)

  tray.on('click', () => {
    console.log("does no work");
  });

}


function createWindow () {
  app.name = APPNAME;
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    frame: true,
    //skipTaskbar: true,
    //toolbar: false,
    //resizable: false,
    title: APPNAME,
    webPreferences: {
      nodeIntegration: true
    },
    icon: path.join(icon_path, "icon_256.png"),
  });

    mainWindow.webContents.openDevTools()

  mainWindow.setMenu(null);

  mainWindow.loadURL("http://" + start_url); // because ":" does not work in windows commandline

  mainWindow.on('closed', function () {
    mainWindow = null;
  })

  //mainWindow.setFullScreen(true)
  ipc.on('set_tray_icon', (event, filename) => {
    console.log("set_tray_icon " + filename);
    tray.setImage(nativeImage.createFromPath(path.join(icon_path, filename)));
    //mainWindow.webContents.send("message", "hallo23");
  })
}

app.on('ready', () => {
  createTray();
  createWindow();
})

// Quit when all windows are closed.
app.on('window-all-closed', function () {
  // On macOS it is common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', function () {
  // On macOS it's common to re-create a window in the app when the
  // dock icon is clicked and there are no other windows open.
  if (mainWindow === null) createWindow()
})

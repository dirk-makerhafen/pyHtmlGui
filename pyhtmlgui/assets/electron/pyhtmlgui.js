const ipc = require('electron').ipcMain;
const spawn = require('child_process').spawn;
let package_json = require('./package.json');

let childProcess = null;
let publicFunctions = {};

if (package_json.PYHTMLGUI_HOST     === undefined){package_json.PYHTMLGUI_HOST     = process.env.PYHTMLGUI_HOST}
if (package_json.PYHTMLGUI_PORT     === undefined){package_json.PYHTMLGUI_PORT     = process.env.PYHTMLGUI_PORT}
if (package_json.PYHTMLGUI_SECRET   === undefined){package_json.PYHTMLGUI_SECRET   = process.env.PYHTMLGUI_SECRET}
if (package_json.PYHTMLGUI_CMD      === undefined){package_json.PYHTMLGUI_CMD      = process.env.PYHTMLGUI_CMD}
if (package_json.PYHTMLGUI_CMD_ARGS === undefined){package_json.PYHTMLGUI_CMD_ARGS = process.env.PYHTMLGUI_CMD_ARGS}
if (package_json.PYHTMLGUI_CMD_ARGS === undefined){package_json.PYHTMLGUI_CMD_ARGS = ""}

function start(){
  if (package_json.PYHTMLGUI_CMD !== undefined && childProcess === null){  // we launch pyHtmlGui python process internally
    var args = package_json.PYHTMLGUI_CMD_ARGS.split(',')
    childProcess = spawn(package_json.PYHTMLGUI_CMD, args, {cwd : __dirname, } );
    childProcess.stdout.setEncoding('utf8');
    childProcess.stderr.setEncoding('utf8');
    childProcess.stdout.on('data', function(data) { console.log('pyHtmlGui: ' + data); });
    childProcess.stderr.on('data', function(data) { console.log('pyHtmlGui: ' + data); });
    childProcess.on('close', function(code) {
      console.log('pyHtmlGui: Python app exit with code: ' + code);
      childProcess = null;
    });
  }
}

function init_ipc(){
  ipc.handle('call', async (event, function_name_full, args) => {
      let name_parts = function_name_full.split(".");
      let function_name = name_parts.pop();
      let obj = publicFunctions;
      for(var i = 0; i < name_parts.length; i++) {
        obj = obj[name_parts[i]];
      }
      let return_data = null;
      if(obj[function_name] === undefined){
        return_data = { 'error': "No function called '" + function_name_full + "' in electron main.js publicFunctions" }
      }else{
        try {
          return_data = { 'value':  obj[function_name](...args)};
        }catch (e) {
          return_data = { 'error': "Failed to execute '" + function_name_full + "' in electron main.js \n" + e.stack }
        }
      }
      return return_data;
    })
}

function get_start_url(){
  start_url = "http://" + package_json.PYHTMLGUI_HOST + ":" +  package_json.PYHTMLGUI_PORT + "";
  if(package_json.PYHTMLGUI_SECRET !== null && package_json.PYHTMLGUI_SECRET !== undefined ){
    start_url += "/?token=" + package_json.PYHTMLGUI_SECRET;
  }
  return start_url;
}

function add_public_functions(functions){
    publicFunctions = { ...publicFunctions, ...functions };
}

module.exports = {
   init: init,
   start: start,
   get_start_url: get_start_url,
   add_public_functions: add_public_functions,
}



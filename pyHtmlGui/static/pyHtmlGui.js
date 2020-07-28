
var getUrlParameter = function getUrlParameter(sParam) {
    var sPageURL = window.location.search.substring(1),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        }
    }
};

pyHtmlGui = {
    _host: window.location.origin,

    set_host: function (hostname) {
        pyHtmlGui._host = hostname
    },

    expose: function(f, name) {
        if(name === undefined){
            name = f.toString();
            let i = 'function '.length, j = name.indexOf('(');
            name = name.substring(i, j).trim();
        }

        pyHtmlGui._exposed_functions[name] = f;
    },

    guid: function() {
        return pyHtmlGui._guid;
    },

    // These get dynamically added by library when file is served
    /** _py_functions **/
    /** _start_geometry **/

    _guid: ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        ),

    _exposed_functions: {},

    _mock_queue: [],

    _mock_py_functions: function() {
        for(let i = 0; i < pyHtmlGui._py_functions.length; i++) {
            let name = pyHtmlGui._py_functions[i];
            pyHtmlGui[name] = function() {
                let call_object = pyHtmlGui._call_object(name, arguments);
                pyHtmlGui._mock_queue.push(call_object);
                return pyHtmlGui._call_return(call_object);
            }
        }
    },

    _import_py_function: function(name) {
        let func_name = name;
        pyHtmlGui[name] = function() {
            let call_object = pyHtmlGui._call_object(func_name, arguments);
            pyHtmlGui._websocket.send(pyHtmlGui._toJSON(call_object));
            return pyHtmlGui._call_return(call_object);
        }
    },

    _call_number: 0,

    _call_return_callbacks: {},

    _call_object: function(name, args) {
        let arg_array = [];
        for(let i = 0; i < args.length; i++){
            arg_array.push(args[i]);
        }

        let call_id = (pyHtmlGui._call_number += 1) + Math.random();
        return {'call': call_id, 'name': name, 'args': arg_array};
    },

    _sleep: function(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    _toJSON: function(obj) {
        return JSON.stringify(obj, (k, v) => v === undefined ? null : v);
    },

    _call_return: function(call) {
        return function(callback = null) {
            if(callback != null) {
                pyHtmlGui._call_return_callbacks[call.call] = callback;
            } else {
                return new Promise(function(resolve) {
                    pyHtmlGui._call_return_callbacks[call.call] = resolve;
                });
            }
        }
    },

    _position_window: function(page) {
        let size = pyHtmlGui._start_geometry['default'].size;
        let position = pyHtmlGui._start_geometry['default'].position;

        if(page in pyHtmlGui._start_geometry.pages) {
            size = pyHtmlGui._start_geometry.pages[page].size;
            position = pyHtmlGui._start_geometry.pages[page].position;
        }

        if(size != null){
            window.resizeTo(size[0], size[1]);
        }

        if(position != null){
            window.moveTo(position[0], position[1]);
        }
    },

    _init: function() {
        pyHtmlGui._mock_py_functions();

        document.addEventListener("DOMContentLoaded", function(event) {
            let page = window.location.pathname.substring(1);
            pyHtmlGui._position_window(page);

            let websocket_addr = (pyHtmlGui._host + '/pyHtmlGui').replace('http', 'ws');
            websocket_addr += ('?token=' + csrf_token);
            pyHtmlGui._websocket = new WebSocket(websocket_addr);

            pyHtmlGui._websocket.onopen = function() {
                for(let i = 0; i < pyHtmlGui._py_functions.length; i++){
                    let py_function = pyHtmlGui._py_functions[i];
                    pyHtmlGui._import_py_function(py_function);
                }

                while(pyHtmlGui._mock_queue.length > 0) {
                    let call = pyHtmlGui._mock_queue.shift();
                    pyHtmlGui._websocket.send(pyHtmlGui._toJSON(call));
                }
            };

            pyHtmlGui._websocket.onmessage = function (e) {
                let message = JSON.parse(e.data);
                if(message.hasOwnProperty('call') ) {
                    // Python making a function call into us
                    if(message.name in pyHtmlGui._exposed_functions) {
                        let return_val = pyHtmlGui._exposed_functions[message.name](...message.args);
                        pyHtmlGui._websocket.send(pyHtmlGui._toJSON({'return': message.call, 'value': return_val}));
                    }else{
                        pyHtmlGui._websocket.send(pyHtmlGui._toJSON({'return': message.call, 'error': "No exposed javascript function called '"+message.name+"'"}));
                    }
                } else if(message.hasOwnProperty('return')) {
                    // Python returning a value to us
                    if(message['return'] in pyHtmlGui._call_return_callbacks) {
                        pyHtmlGui._call_return_callbacks[message['return']](message.value);
                    }
                } else {
                    throw 'Invalid message ' + message;
                }

            };

            pyHtmlGui.token = getUrlParameter('token');

            // return list of expored js functions on ready
            pyHtmlGui.frontend_ready(Object.keys(pyHtmlGui._exposed_functions));

        });
    },

    call: function (functionCallbackId, ...args){
        if( args.length === 0 ){
            return pyHtmlGui.call_python_function(functionCallbackId);
        }else{
            return pyHtmlGui.call_python_function_with_args(functionCallbackId, args);
        }
    },

}

pyHtmlGui._init();

if(typeof require !== 'undefined'){
    // Avoid name collisions when using Electron, so jQuery etc work normally
    window.nodeRequire = require;
    delete window.require;
    delete window.exports;
    delete window.module;
}




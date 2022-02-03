function create_random_string(prefix = ""){
    return prefix + " this part in JS, " + Math.random();
}

if (_id_cache === undefined){
    var _id_cache = "JS_" + Math.random();
};
function get_frontend_id(){
    return _id_cache;
}
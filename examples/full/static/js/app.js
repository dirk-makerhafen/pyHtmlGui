
function update_balls(uid, position_x, position_y){
     item_style = document.getElementById(uid).style;
     item_style.left = position_x + "%";
     item_style.top  = position_y + "%";
}
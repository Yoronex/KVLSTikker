var cartList = [];   //Orders all users in a cart

var prod_price;

function myCreateFunction() {
  var table = document.getElementById("myTable");
  var row = table.insertRow(0);
  var cell1 = row.insertCell(0);
  var cell2 = row.insertCell(1);
  cell1.innerHTML = "NEW CELL1";
  cell2.innerHTML = "NEW CELL2";
}

function myDeleteFunction() {
  document.getElementById("myTable").deleteRow(0);
}

/*
Table layout

| Decrease button | Name | Count | Price |
 */

var decrease_button_loc = 0;
var name_loc = 1;
var count_loc = 2;
var price_loc = 3;



function addToCart(u_id, user_name, p_price) {
    prod_price = p_price;
    var user_id = parseInt(u_id);
    if (user_id in cartList) {
        changeCartAmount(user_id, cartList[user_id], 1);
        return;
    }

    var table = document.getElementById("cart");
    var row = table.insertRow(-1);
    var cell0 = row.insertCell(decrease_button_loc);
    var cell1 = row.insertCell(name_loc);
    var cell2 = row.insertCell(count_loc);
    var cell3 = row.insertCell(price_loc);

    cell0.innerHTML = "<a onclick='removeFromCart(" + user_id + ")'>DEL</a>";
    cell1.innerHTML = user_name;
    cell2.innerHTML = 1;
    cell3.innerHTML = prod_price;

    //var temp = [];
    //temp["id"] = user_id;
    //temp["row"] = row;
    cartList[user_id] = row;
}

function changeCartAmount(user_id, row, amount) {
    //var row = document.getElementById("cart").rows[loc];
    var count_cell = row.cells[count_loc];
    var count = parseInt(count_cell.innerHTML) + amount;
    row.cells[count_loc].innerHTML = count;
    row.cells[price_loc].innerHTML = parseFloat(prod_price) * count;
}

function removeFromCart(u_id) {
    var user_id = parseInt(u_id);
    if (!(user_id in cartList)) {
        return;
    }
    var count = parseInt(cartList[user_id].cells[count_loc].innerHTML);
    if (count <= 1) {
        document.getElementById("cart").deleteRow(cartList[user_id].rowIndex);
        calendarList.pop(user_id);
    } else {
        changeCartAmount(user_id, cartList[user_id], -1)
    }
}
var cartList = [];   //Orders all users in a cart

var prod_price;

/*
Table layout

| Decrease button | Name | Count | Price |
 */

var decrease_button_loc = 0;
var name_loc = 1;
var count_loc = 2;
var price_loc = 3;


function makeSubmitInvisible() {
    document.getElementById("submitbutton").style.visibility = "hidden";
}

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

    var minusimg = $('body').data('minus-img');
    cell0.innerHTML = "<a onclick='removeFromCart(" + user_id + ")' onmouseover=\"\" style=\"cursor: pointer;\"><img src='" + minusimg + "' alt=\"DEL\" title=\"Verwijder één\"></a>";
    cell0.style.width = "15%";
    cell1.innerHTML = user_name;
    cell1.style.width = "50%";
    cell2.innerHTML = "1x";
    cell2.style.width = "15%";
    cell3.innerHTML = "€" + parseFloat(Math.round(prod_price * 100) / 100).toFixed(2).toString();
    cell3.style.width = "20%";

    //var temp = [];
    //temp["id"] = user_id;
    //temp["row"] = row;
    cartList[user_id] = row;
    document.getElementById("submitbutton").style.visibility = "visible";
}

function changeCartAmount(user_id, row, amount) {
    //var row = document.getElementById("cart").rows[loc];
    var count_cell = row.cells[count_loc];
    var count = parseInt(count_cell.innerHTML) + amount;
    row.cells[count_loc].innerHTML = count.toString() + "x";
    row.cells[price_loc].innerHTML = "€" + parseFloat(Math.round((parseFloat(prod_price) * count)* 100) / 100).toFixed(2).toString();
}

function removeFromCart(u_id) {
    var user_id = parseInt(u_id);
    if (!(user_id in cartList)) {
        return;
    }
    var count = parseInt(cartList[user_id].cells[count_loc].innerHTML);
    if (count <= 1) {
        document.getElementById("cart").deleteRow(cartList[user_id].rowIndex);
        delete cartList[user_id];
    } else {
        changeCartAmount(user_id, cartList[user_id], -1)
    }

    if (cartList.length === 0) {
        document.getElementById("submitbutton").style.visibility = "hidden";
    }
}

function submitCart() {
    if (cartList.length <= 0) {
        return;
    }

    var output = "/";
    for (var key in cartList) {
        output = output + key;
        output = output + "a";
        output = output + parseFloat(cartList[key].cells[count_loc].innerHTML);
        output = output + "&";
    }
    output = output.slice(0, -1);
    window.location.href = window.location.href + output;
}


window.onload = function() {
    makeSubmitInvisible()
}

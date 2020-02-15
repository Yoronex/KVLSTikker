var cartList = [];   //Orders all users in a cart
var prod_price = 0;
var dinner = false;
var biertjekwartiertje = false;

/*
Table layout

| Decrease button | Name | Count | Price |
 */

var decrease_button_loc = 0;
var name_loc = 1;
var count_loc = 2;
var price_loc = 3;
var total = 0;

function initCart(p_price, already_in_cart=[]) {
    console.log("price: " + p_price);
    prod_price = p_price;

    for (let i = 0; i < already_in_cart.length; i++) {
        addToCart(already_in_cart[i].id, already_in_cart[i].name, 'False')
    }
}

function makeSubmitInvisible() {
    document.getElementById("submitbutton").style.visibility = "hidden";
}

function addToCart(u_id, user_name, shared) {
    total = total + 1;
    shared = (shared === 'True');

    if(shared === false) {
        //prod_price = p_price;
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
        cell3.innerHTML = "€" + parseFloat(Math.ceil(prod_price * 100) / 100).toFixed(2).toString();
        cell3.style.width = "20%";

        //var temp = [];
        //temp["id"] = user_id;
        //temp["row"] = row;
        cartList[user_id] = row;
        document.getElementById("submitbutton").style.visibility = "visible";
    } else {
        //prod_price = p_price;
        var user_id = parseInt(u_id);
        if (user_id in cartList) {
            changeCartPart(user_id, cartList[user_id], 1);
            return;
        }

        var table = document.getElementById("cart");
        var row = table.insertRow(-1);
        var cell0 = row.insertCell(decrease_button_loc);
        var cell1 = row.insertCell(name_loc);
        var cell2 = row.insertCell(count_loc);
        var cell3 = row.insertCell(price_loc);

        var minusimg = $('body').data('minus-img');
        cell0.innerHTML = "<a onclick='removeFromPart(" + user_id + ")' onmouseover=\"\" style=\"cursor: pointer;\"><img src='" + minusimg + "' alt=\"DEL\" title=\"Verwijder één\"></a>";
        cell0.style.width = "15%";
        cell1.innerHTML = user_name;
        cell1.style.width = "50%";
        cell2.innerHTML = "1/" + total.toString();
        cell2.style.width = "15%";
        cell3.innerHTML = "€" + parseFloat(Math.ceil(prod_price / total * 100) / 100).toFixed(2).toString();
        cell3.style.width = "20%";

        updateCart();

        //var temp = [];
        //temp["id"] = user_id;
        //temp["row"] = row;
        cartList[user_id] = row;
        //document.getElementById("submitbutton").style.visibility = "visible";
    }
}

function changeCartAmount(user_id, row, amount) {
    //var row = document.getElementById("cart").rows[loc];
    var count_cell = row.cells[count_loc];
    var count = parseInt(count_cell.innerHTML) + amount;
    row.cells[count_loc].innerHTML = count.toString() + "x";
    row.cells[price_loc].innerHTML = "€" + parseFloat(Math.ceil((parseFloat(prod_price) * count)* 100) / 100).toFixed(2).toString();
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

    //if (cartList.length === 0) {
    //    document.getElementById("submitbutton").style.visibility = "hidden";
    //}
}

function changeCartPart(user_id, row, amount) {
    //var row = document.getElementById("cart").rows[loc];
    var count_cell = row.cells[count_loc];
    var count = parseInt(count_cell.innerHTML) + amount;
    row.cells[count_loc].innerHTML = count.toString() + "/" + total.toString();
    row.cells[price_loc].innerHTML = "€" + parseFloat(Math.ceil((parseFloat(prod_price) * count / total)* 100) / 100).toFixed(2).toString();

    updateCart();
}

function removeFromPart(u_id) {
    var user_id = parseInt(u_id);
    if (!(user_id in cartList)) {
        return;
    }

    total = total - 1;

    var count = parseInt(cartList[user_id].cells[count_loc].innerHTML);
    if (count <= 1) {
        document.getElementById("cart").deleteRow(cartList[user_id].rowIndex);
        changeCartPart(user_id, cartList[user_id], -1);
        delete cartList[user_id];
    } else {
        changeCartPart(user_id, cartList[user_id], -1)
    }

    //if (cartList.length === 0) {
    //    document.getElementById("submitbutton").style.visibility = "hidden";
    //}
}

function updateCart() {
    for(var key in cartList) {
        var row = cartList[key];
        var count = parseInt(row.cells[count_loc].innerHTML);
        row.cells[count_loc].innerHTML = count.toString() + "/" + total.toString();
        row.cells[price_loc].innerHTML = "€" + parseFloat(Math.ceil((parseFloat(prod_price) * count / total)* 100) / 100).toFixed(2).toString();
    }
}

function submitCart() {
    if (cartList.length <= 0) {
        return;
    }

    document.getElementById("loader").style.display = "block";

    var output = "/";
    output = output + document.getElementById('round_giver').value + "&";
    for (var key in cartList) {
        output = output + key;
        output = output + "a";
        output = output + parseFloat(cartList[key].cells[count_loc].innerHTML);
        output = output + "&";
    }
    output = output.slice(0, -1);

    if (dinner) {
        let price = document.getElementById('total-spent').value;
        price = parseFloat(price.replace(',', '.'));
        if (isNaN(price)) {
            hideLoadingBar();
            return;
        }
        const comments = document.getElementById('comments').value;
        output = output + encodeURI( `?price=${price}&comments=${comments}`)
    }

    if (biertjekwartiertje) {
        let drink = document.getElementById('drink').value;
        let time = document.getElementById('playtime').value;
        output = output + encodeURI(`?drink=${drink}&time=${time}`)
    }

    window.location.href = window.location.href + output;
}

function changePrice() {
    let field = document.getElementById("total-spent");
    let s = parseFloat(field.value.replace(',', '.'));
    prod_price = s;
    updateCart();
}
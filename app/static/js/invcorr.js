var products = [];
var index = -1;
var max;
var inventories = [];
var usergroup_ids = {};
var result = [];

function init(pr, inv, g_ids) {
    products = pr;
    inventories = inv;
    usergroup_ids = g_ids;
    max = products.length;

    updatePage();
}

var product_id;

function getInv(inventory) {
    if (inventory['id'] === product_id) {
        return inventory
    }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function updatePage() {
    if (index !== -1) {
        document.getElementById("loader").style.display = "block";
        await sleep(500);
        addToResult();
    }

    index++;
    if (index < products.length) {
        var p = products[index];
        if (index !== 0) {
            var prev_p = products[index - 1];
            var t_row = document.getElementById("product-list-" + prev_p['id'].toString());
            t_row.style.fontWeight = "normal";
            t_row.cells[1].style.textDecoration = "";
            t_row.cells[0].innerHTML = ""
        }
        var p_row = document.getElementById("product-list-" + p['id'].toString());
        p_row.style.fontWeight = "bold";
        p_row.cells[1].style.textDecoration = "underline";
        p_row.cells[0].innerHTML = "→";

        document.getElementById("curr_inv").innerHTML = p['stock'];
        document.getElementById("real_inv").value = p['stock'];

        var percentage = Math.round(index * 100 / max);
        var progress = document.getElementById("progress");
        progress.style.width = percentage.toString() + "%";

        product_id = p['id'];
        var invs = inventories.filter(getInv);
        var table = document.getElementById("inv-table");
        var rows = table.getElementsByTagName("tr").length;
        for (var i = 1; i < rows; i++) {
            table.deleteRow(1);
        }
        for (var i = 0; i < invs.length; i++) {
            var row = table.insertRow(i+1);
            var cell1 = row.insertCell(0);
            cell1.innerHTML = invs[i]['id'];
            var cell2 = row.insertCell(1);
            cell2.innerHTML = invs[i]['timestamp'][0];
            var cell3 = row.insertCell(2);
            cell3.innerHTML = parseInt(invs[i]['quantity']);
            var cell4 = row.insertCell(3);
            if (invs[i]['price_before_profit'] === null) {
                cell4.innerHTML = `<span style="color: red;font-weight:bold;">--</span>`
            } else {
                cell4.innerHTML = invs[i]['price_before_profit'].toFixed(2);
            }
            var cell5 = row.insertCell(4);
            cell5.innerHTML = invs[i]['note'];
        }

        if (index === products.length - 1) {
            document.getElementById("next-btn").innerHTML = "Voltooien";
        }
    }
    else {
        var http = new XMLHttpRequest();
        var url = window.location.href;
        var param = JSON.stringify(result);
        http.open('POST', url, true);
        http.setRequestHeader('Content-type', 'application/json;charset=UTF-8')

        http.onreadystatechange = function () {
            if (http.readyState === 4 && http.status === 200) {
                console.log(http.responseURL);
                window.location.replace(http.responseURL);
            }
        };
        http.send(param);
    }
    document.getElementById("loader").style.display = "none";
}

function addToResult() {
    var real_inv = parseInt(document.getElementById("real_inv").value);
    var old_inv = parseInt(document.getElementById("curr_inv").innerHTML);
    var diff = old_inv - real_inv;
    if (diff < 0) {
        document.getElementById("product-list-" + products[index]['id'].toString()).cells[2].innerHTML = diff.toString();
    } else {
        document.getElementById("product-list-" + products[index]['id'].toString()).cells[2].innerHTML = "+" + diff.toString();
    }
    var checkboxes = document.getElementsByName("groups");
    var paying_groups = [];
    var groupcell = document.getElementById("product-list-" + products[index]['id'].toString()).cells[3];
    for (var i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].checked) {
            paying_groups.push(parseInt(checkboxes[i].value));
            groupcell.innerHTML = groupcell.innerHTML + usergroup_ids[checkboxes[i].value] + ", "
        }
    }
    groupcell.innerHTML = groupcell.innerHTML.substring(0, groupcell.innerHTML.length - 2);
    result.push({'product_id': products[index]['id'], 'stock': real_inv, 'groups': paying_groups});
}

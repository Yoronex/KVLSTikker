function backgroundColors(length) {
    var result = [];
    for (var i = 0; i < length; i++) {
        if (i % 2 === 0) {
            result.push('rgba(11, 131, 55, 0.2)');
        } else {
            result.push('rgba(255, 200, 0, 0.2)');
        }
    }
    return result;
}

function borderColors(length) {
    var result = [];
    for (var i = 0; i < length; i++) {
        if (i % 2 === 0) {
            result.push('rgba(11, 131, 55, 1.0)');
        } else {
            result.push('rgba(255, 200, 0, 1.0)');
        }
    }
    return result;
}

function createBar(ids, data, labels, id, url_prefix) {

    var ctx = document.getElementById(id);
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors(data.length),
                borderColor: borderColors(data.length),
                borderWidth: 1
            }]
        },
        options: {
            legend: {
                display: false
            },
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }]
            }
        }
    });

    if (url_prefix !== "") {
        ctx.onclick = function (evt) {
            var activePoints = myChart.getElementsAtEvent(evt);
            if (activePoints[0]) {
                var idx = activePoints[0]['_index'];

                var domain = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '');

                var url_parts = url_prefix.split("/");
                url_parts.pop();
                var final_url = "";
                for (var part in url_parts) {
                    final_url = final_url + url_parts[part] + "/"
                }
                final_url = domain + final_url + ids[idx];
                window.location.href = final_url;
            }
        }
    }
}

function createPie(ids, data, labels, id, url_prefix) {
    var ctx = document.getElementById(id);
    var myChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors(data.length),
                borderColor: borderColors(data.length),
                borderWidth: 1
            }]
        },
        options: {
            legend: {
                display: false
            }
        }
    });


    if (url_prefix !== "") {
        ctx.onclick = function (evt) {
            var activePoints = myChart.getElementsAtEvent(evt);
            if (activePoints[0]) {
                var idx = activePoints[0]['_index'];

                var domain = location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '');

                var url_parts = url_prefix.split("/");
                url_parts.pop();
                var final_url = "";
                for (var part in url_parts) {
                    final_url = final_url + url_parts[part] + "/"
                }
                final_url = domain + final_url + ids[idx];
                window.location.href = final_url;
            }
        }
    }
}

function createLine(data, id) {
    var date_array = data.map(function(a) {
        return {
            "x": new Date(a["x"]),
            "y": a["y"]
        }
    });

    var labels = [];
    for (var i in data) {
        labels.push(new Date(date_array[i]["x"]).toLocaleString())
    }

    var ctx = document.getElementById("line-chart");
    var myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: date_array,
                //backgroundColor: [
                //'rgba(255, 99, 132, 0.2)',
                //'rgba(54, 162, 235, 0.2)',
                //'rgba(255, 206, 86, 0.2)',
                //'rgba(75, 192, 192, 0.2)',
                //'rgba(153, 102, 255, 0.2)',
                //'rgba(255, 159, 64, 0.2)'
                //],
                borderColor: 'rgba(11, 131, 55, 1.0)',
                //],
                borderWidth: 1,
                steppedLine: true,
            }]
        },
        options: {
            scales: {
                xAxes: [{
                    // This is the important part
                    type: "time",
                }]
            },
            legend: {
                display: false
            }
        }
    });

}

function testInput(input) {
    console.log(input.toString());
    console.log(type(input).toString());
}

function changeDate() {
    var begin = document.getElementById('begindate').value;
    var end = document.getElementById('enddate').value;
    var url_parts = window.location.href.split("/");
    var length = url_parts.length;
    url_parts[length - 2] = begin;
    url_parts[length - 1] = end;
    var final_url = "";
    for (var part in url_parts) {
        final_url = final_url + url_parts[part] + "/"
    }
    final_url = final_url.slice(0, -1);
    window.location.href = final_url
}

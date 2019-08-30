var ctx = document.getElementById('myChart');
var myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
        datasets: [{
            label: '# of Votes',
            data: [12, 19, 3, 5, 2, 3],
//            backgroundColor: [
//                'rgba(255, 99, 132, 0.2)',
//                'rgba(54, 162, 235, 0.2)',
//                'rgba(255, 206, 86, 0.2)',
//                'rgba(75, 192, 192, 0.2)',
//                'rgba(153, 102, 255, 0.2)',
//                'rgba(255, 159, 64, 0.2)'
//            ],
//            borderColor: [
//                'rgba(255, 99, 132, 1)',
//                'rgba(54, 162, 235, 1)',
//                'rgba(255, 206, 86, 1)',
//                'rgba(75, 192, 192, 1)',
//                'rgba(153, 102, 255, 1)',
//                'rgba(255, 159, 64, 1)'
//            ],
            borderWidth: 1
        }]
    },
    options: {
        scales: {
            yAxes: [{
                ticks: {
                    beginAtZero: true

                }
            }]
        }
    }
});

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

function createBar(data, labels) {

    var ctx1 = document.getElementById('bar');
    var myChart = new Chart(ctx1, {
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
}

function testInput(input) {
    console.log(input.toString());
    console.log(type(input).toString());
}
function startFunctions() {
    startTime();
    pingTikker();
    hideLoadingBar();
}

function startTime() {
    var today = new Date();
    var h = today.getHours();
    var m = today.getMinutes();
    var s = today.getSeconds();
    m = checkTime(m);
    if (s % 2 == 0) {
        document.getElementById('clock').innerHTML = h + ":" + m;
    } else {
        document.getElementById('clock').innerHTML = h + " " + m;
    }
    var t = setTimeout(startTime, 500);
}

function checkTime(i) {
    if (i < 10) { // add zero in front of numbers < 10
        i = "0" + i
    }
    return i;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function toggle_confetti() {
    var cookie = getCookie('confetti');
    if(cookie === "True") {
        setSessionCookie('confetti', 'False')
    } else {
        setSessionCookie('confetti', 'True')
    }
    location.reload()
}

function toggle_darkmode() {
    var cookie = getCookie('dark-mode');
    if(cookie === "True") {
        setCookie('dark-mode', 'False', 1000)
    } else {
        setCookie('dark-mode', 'True', 1000)
    }
    location.reload()
}

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
    }
    }
    return "";
}

function setSessionCookie(cname, cvalue) {
    document.cookie = cname + "=" + cvalue + ";path=/";
}

function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function showLoadingBar() {
    document.getElementById("loader").style.display = "block";
}

function hideLoadingBar() {
    document.getElementById("loader").style.display = "none";
}

var alreadyoffline = false;

function pingTikker() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ping', true);
    xhr.timeout = 2000;
    var circle = document.getElementById('status-dot');
    var status_text = document.getElementById('status-text');

    xhr.onload = function() {
        circle.style.backgroundColor = 'green';
        circle.classList.add("pulsation");
        status_text.style.color = 'green';
        status_text.innerHTML = "Tikker online";
        if (alreadyoffline) {
            $('#tikker-offline-modal').modal('hide');
            alreadyoffline = false;
            circle.style.backgroundColor = 'green';
            circle.classList.add("pulsation");
            status_text.style.color = 'green';
            status_text.innerHTML = "Tikker online";
        }
    };
    xhr.ontimeout = function(e) {
        if (!alreadyoffline) {
            $('#tikker-offline-modal').modal('show');
            alreadyoffline = true;
            circle.style.backgroundColor = 'red';
            circle.classList.remove("pulsation");
            status_text.style.color = 'red';
            status_text.innerHTML = "Tikker offline";
        }
    };

    xhr.send(null);
    var t = setTimeout(pingTikker, 15000);
}
loadXMLDoc()
setInterval(loadXMLDoc, 1000);

function loadXMLDoc() {
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            parseXML(this);
        }
    };
    xhttp.open("GET", "statistics.xml", false);
    xhttp.send();
}

function parseXML(xml) {
    var i;
    var parser = new DOMParser();
    var xmlDoc = parser.parseFromString(xml.responseText, "application/xml");
    
    document.getElementById("connection_number").innerHTML = "Connections: " + xmlDoc.getElementsByTagName("connection_number")[0].childNodes[0].nodeValue
    document.getElementById("demo").innerHTML = '';

    table = 
        '<thead>' +
            '<tr>' +
                '<th></th>' +
                '<th> Socket Type </th>' +
                '<th> Socket File Descriptor </th>' +
                '<th> Bytes </th>' +
                '<th> </th>' +
            '</tr>' +
        '</thead>' +
        '<tbody>'
    ;
    
    var x = xmlDoc.getElementsByTagName("connection");
    for (i = 0; i < x.length; i++) {
        table += 
            '<tr>' +
                '<td class="center" rowspan="2">' + (i+1) + '</td>' +
                '<td> server </td>' +
                '<td>' + x[i].getElementsByTagName("server")[0].childNodes[0].nodeValue + '</td>' +
                '<td>' + x[i].getElementsByTagName("in")[0].childNodes[0].nodeValue + '</td>' +
                '<td class="center" rowspan="2">' +
                    '<button type="button" onclick="location.href=\'/disconnect?connection=' + x[i].getElementsByTagName("num")[0].childNodes[0].nodeValue + '\';">' +
                    '    Disconnect' +
                    '</button>' +
                '</td>' +
            '</tr>' +
            '<tr>' +
                '<td> partner </td>' +
                '<td>' + x[i].getElementsByTagName("partner")[0].childNodes[0].nodeValue + '</td>' +
                '<td>' + x[i].getElementsByTagName("out")[0].childNodes[0].nodeValue + '</td>' +
            '</tr>'
        ;
    }
    table += '</tbody>'
    document.getElementById("demo").innerHTML += table;
}
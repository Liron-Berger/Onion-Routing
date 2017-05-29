loadXMLDoc()
setInterval(loadXMLDoc, 1000);

function loadXMLDoc() {
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            parseXML(this);
        }
    };
    xhttp.open("GET", "nodes.xml", false);
    xhttp.send();
}

function parseXML(xml) {
    var i;
    var parser = new DOMParser();
    var xmlDoc = parser.parseFromString(xml.responseText, "application/xml");
    
    document.getElementById("nodes_number").innerHTML = "Counter: " + xmlDoc.getElementsByTagName("nodes_number")[0].childNodes[0].nodeValue
    document.getElementById("demo").innerHTML = '';

    
    nodes = ''
    var x = xmlDoc.getElementsByTagName("node");
    for (i = 0; i < x.length; i++) {
        nodes += 
            '<a href="/unregister?' + x[i].getElementsByTagName("port")[0].childNodes[0].nodeValue + '" class="animated-button unregister">' +
                x[i].getElementsByTagName("address")[0].childNodes[0].nodeValue + ' : ' + x[i].getElementsByTagName("port")[0].childNodes[0].nodeValue + 
            '</a>'
        ;
    }
    document.getElementById("demo").innerHTML += nodes;
}
const flask_doc_request = 'http://localhost:3000/get-doc-by-id/'
const first_request = "http://localhost:3000/search"
const polling_request = "http://localhost:3000/get-doc-id"

//request to update the nav bar with all the graphs processed 
setInterval(function () {
    $.ajax({
        type: "get",
        url: polling_request,
        dataType: 'json',
        success: function (data) {
            var list_len = Object.keys(data.ids).length
            document.getElementById("generated-graphs").innerHTML = "current graphs: " + list_len;
            for (i = 0; i < list_len; i++) {
                var iDiv = document.createElement('div');
                iDiv.id = 'block' + i;
                iDiv.className = 'block';
                if (document.getElementById("block" + i) === null) {
                    document.getElementById("select-item").appendChild(iDiv);
                    document.getElementById("block" + i).innerHTML = data.ids[i]
                    document.getElementById("block" + i).onclick = function () {
                        //onclick to get the graph
                        document.getElementById("current_label").innerHTML = String("ID: " + this.innerHTML);

                        $.getJSON(flask_doc_request + String(this.innerHTML), function (data) {
                            document.getElementById("current_timestamp").innerHTML = "Timestamp: " + String(data.timestamp);

                            var nodes = data.nodes
                            var edges = data.edges

                            var node_size = Object.keys(nodes).length
                            var edge_size = Object.keys(edges).length

                            var nodes_list = new vis.DataSet();
                            var edges_list = new vis.DataSet();

                            for (var i = 0; i < edge_size; i++) {
                                edges_list.add({ from: edges[i].source, to: edges[i].target, weight: edges[i].value, title: edges[i].value });
                            }

                            for (var i = 0; i < node_size; i++) {
                                nodes_list.add({ id: nodes[i].name, label: nodes[i].text, title: (nodes[i].categories !== null ? nodes[i].categories[0] : "None"), group: (nodes[i].categories !== null ? nodes[i].categories[0] : "None") });
                            }

                            var container = document.getElementById("mynetwork");

                            var datas = {
                                nodes: nodes_list,
                                edges: edges_list,
                            };

                            var options = {
                                nodes: {
                                    shape: "dot",
                                },
                                edges: {
                                    arrows: 'to',
                                    scaling: {
                                        label: true,
                                    }
                                }
                            };

                            var network = new vis.Network(container, datas, options, directed = true, show_buttons = false);

                            network.on("stabilizationProgress", function (params) {
                                document.getElementById('loadingBar').removeAttribute("style");
                                var maxWidth = 496;
                                var minWidth = 20;
                                var widthFactor = params.iterations / params.total;
                                var width = Math.max(minWidth, maxWidth * widthFactor);

                                document.getElementById('bar').style.width = width + 'px';
                                document.getElementById('text').innerHTML = Math.round(widthFactor * 100) + '%';
                            });

                            network.once("stabilizationIterationsDone", function () {
                                document.getElementById('text').innerHTML = '100%';
                                document.getElementById('bar').style.width = '496px';
                                document.getElementById('loadingBar').style.opacity = 0;
                                // really clean the dom element
                                setTimeout(function () { document.getElementById('loadingBar').style.display = 'none'; }, 500);
                            });

                        });

                    }
                }
            }
        }
    });
}, 10000); //10000 milliseconds = 10 seconds

//at the beginning loads the last graph written on es
$.getJSON(first_request, function (data) {


    console.log(data.id)
      

      

    document.getElementById("current_label").innerHTML = "ID: " + String(data.id);
    document.getElementById("current_timestamp").innerHTML = "Timestamp: " + String(data.id);
    
    var nodes = data.nodes
    var edges = data.edges

    var node_size = Object.keys(nodes).length
    var edge_size = Object.keys(edges).length

    var nodes_list = new vis.DataSet();
    var edges_list = new vis.DataSet();

    for (var i = 0; i < edge_size; i++) {
        edges_list.add({ from: edges[i].source, to: edges[i].target, weight: edges[i].value, title: edges[i].value });
    }

    for (var i = 0; i < node_size; i++) {
        nodes_list.add({ id: nodes[i].name, label: nodes[i].text, title: (nodes[i].categories !== null ? nodes[i].categories[0] : "None"), group: (nodes[i].categories !== null ? nodes[i].categories[0] : "None") });
    }

    var container = document.getElementById("mynetwork");

    var datas = {
        nodes: nodes_list,
        edges: edges_list,
    };

    var options = {
        nodes: {
            shape: "dot",
        },
        edges: {
            arrows: 'to',
            scaling: {
                label: true,
            }
        },
        layout: {
            improvedLayout: false
        }
    };

    var network = new vis.Network(container, datas, options, directed = true, show_buttons = false);

    network.on("stabilizationProgress", function (params) {
        document.getElementById('loadingBar').removeAttribute("style");
        var maxWidth = 496;
        var minWidth = 20;
        var widthFactor = params.iterations / params.total;
        var width = Math.max(minWidth, maxWidth * widthFactor);

        document.getElementById('bar').style.width = width + 'px';
        document.getElementById('text').innerHTML = Math.round(widthFactor * 100) + '%';
    });

    network.once("stabilizationIterationsDone", function () {
        document.getElementById('text').innerHTML = '100%';
        document.getElementById('bar').style.width = '496px';
        document.getElementById('loadingBar').style.opacity = 0;
        // really clean the dom element
        setTimeout(function () { document.getElementById('loadingBar').style.display = 'none'; }, 500);
    });

});

var hide_button = document.getElementById("reduce");
hide_button.addEventListener('click', function () {
    if (document.getElementById("select-item").style.display == "none") {
        document.getElementById("select-item").style.display = "flex";
        hide_button.style.left = "19%";
        document.getElementById("image-button").src = "img/forward.png";
        return;
    }

    document.getElementById("select-item").style.display = "none";
    hide_button.style.left = "0%";
    document.getElementById("image-button").src = "img/back.png";
});
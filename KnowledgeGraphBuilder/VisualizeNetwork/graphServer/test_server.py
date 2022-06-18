from cgitb import reset
from flask import Flask, json, after_this_request, jsonify, make_response
from elasticsearch import Elasticsearch
from flask_cors import CORS, cross_origin

es_server = Flask(__name__)
cors = CORS(es_server)
ES_ADDRESS = "http://elasticsearch:9200"
ES_INDEX = "graph_gui"

es = Elasticsearch(
        ES_ADDRESS,
        verify_certs=False
    )

#return the last written document
@es_server.route("/search")
@cross_origin()
def getData():
    search_param = {
        "size": 1,
        "sort": { "timestamp": "desc"},
        "query": {
            "match_all": {}
        }
    }
    res = es.search(index=ES_INDEX, body=search_param)
    #res = str(res)
    #res =  jsonify(res)
    nodes = []
    edges = []

    
    id = res["hits"]["hits"][0]["_id"]
    print(id)
    for x in res["hits"]["hits"]:
        nodes = x["_source"]["nodes"]
        edges = x["_source"]["links"]

    return make_response(jsonify({"id":id,"nodes":nodes, "edges":edges}), 200) #test jsonify


#return a list of all document's ids
@es_server.route("/get-doc-id")
@cross_origin()
def get_documents_id():
    query = {
         "size": 100,
        "query" : { 
            "match_all" : {} 
        },
       "stored_fields": ["_id"]
       
    }
    
    res = es.search(index=ES_INDEX, body=query)
    ids = []
    for x in res["hits"]["hits"]:
        if x["_id"] not in ids:
            ids.append(x["_id"])

    return es_server.response_class( json.dumps({"ids":ids}) )
    

#return the schema of a given id document
@es_server.route("/get-doc-by-id/<id>") 
@cross_origin()
def get_document_by_id(id):
    query = {
        "size": 1,
        "query": { 
            "bool": {
            "filter": {
                    "term": {
                    "_id": str(id)
                    }
                }
            }
        }
    }

    res = es.search(index=ES_INDEX, body=query)

    nodes = []
    edges = []

    
    id = res["hits"]["hits"][0]["_id"]
    timestamp = res["hits"]["hits"][0]["_source"]["timestamp"]
    print(timestamp)
    for x in res["hits"]["hits"]:
        nodes = x["_source"]["nodes"]
        edges = x["_source"]["links"]
    return make_response(jsonify({"timestamp": timestamp, "id":id,"nodes":nodes, "edges":edges}), 200) #test jsonify


if __name__ == "__main__":
    es_server.run(debug=True,
            host='0.0.0.0',
            port=3000)
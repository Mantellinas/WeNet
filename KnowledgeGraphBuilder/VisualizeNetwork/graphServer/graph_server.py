from os import times
from time import time
from flask import Flask, json, after_this_request
from elasticsearch import Elasticsearch

es_server = Flask(__name__)

ES_ADDRESS = "http://localhost:9200"
ES_INDEX = "graph_gui"

es = Elasticsearch(
        ES_ADDRESS,
        verify_certs=False
    )

#return the last written document
@es_server.route("/search")
def getData():
    @after_this_request
    def add_header(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response 

    search_param = {
        "size": 1,
        "sort": { "timestamp": "desc"},
        "query": {
            "match_all": {}
        }
    }
    res = es.search(index=ES_INDEX, body=search_param)
    return es_server.response_class( json.dumps(res) )


#return a list of all document's ids
@es_server.route("/get-doc-id")
def get_documents_id():
    @after_this_request
    def add_header(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

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
def get_document_by_id(id):
    @after_this_request
    def add_header(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

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
    return es_server.response_class( json.dumps(res) )


if __name__ == "__main__":
    es_server.run(debug=True,
            host='0.0.0.0',
            port=3000)
from __future__ import print_function
import pandas as pd
import requests
import json
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.types import *
from pyspark.sql.types import StructType,StructField, StringType
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.evaluation import ClusteringEvaluator
from elasticsearch import Elasticsearch
from datetime import datetime
from time import sleep

ES_ADDRESS = "http://elasticsearch:9200"
SPACY_ADDRESS = "http://spacy:8088/entities"

GRAPH_ES_INDEX = "graph_gui"
GLOBAL_NODES_ES_INDEX = "global_nodes_index"
GLOBAL_EDGES_ES_INDEX = "global_edges_index"
CLUSTERING_GROUPBY_ES_INDEX = "clusteringgroupby"
JSON_NODES_ES_INDEX="nodes"
JSON_EDGES_ES_INDEX="edges"

#graph_gui graph mapping
mapping = {
  "mappings":{
  "properties": {
    "@timestamp": {
      "type": "date"
    },
    "nodes": {
      "type": "nested",
      "properties": {
        "name": {
          "type": "long"
        },
        "group": {
          "type": "keyword"
        },
        "index": {
          "type": "long"
        }
      }
    },
    "links": {
      "type": "nested",
      "properties": {
        "source": {
          "type": "long"
        },
        "target": {
          "type": "long"
        },
        "value": {
          "type": "keyword"
        }
      }
    }
  }
}
}



# Streaming Query trasformation
def elaborate(batch_df: DataFrame, batch_id: int):
  dff = batch_df.toPandas()
  dff = dff.to_dict('dict')

  try:
    partial_df = dff['value'][0]
    query_df = json.loads(partial_df)
  except:
    return
  
  while True:
    #try:
      query = { "pmcid": "string" , "text" : query_df['text']}
      resp = requests.post(url=SPACY_ADDRESS, json=query)
      data = resp.json()

      #create json for graph visualization 
      nodesDict = []
      source = []

      for item in data['nodes']:
        nodesDict.append({"name" : item, "text": data['nodes'][item]['text'], "categories": data['nodes'][item]['categories'], "wid":data['nodes'][item]['wid'], "rho":data['nodes'][item]['rho']}) 
      
      for item in data['sentences']:
        for edge in item['edges']:
          source.append({"source": edge['src_pos'], "target": edge['dst_pos'], "value": edge['edge_name']})
      
      temp_dict = {"timestamp": datetime.now().isoformat(),"nodes": nodesDict, "links": source}
      graph_dict = json.dumps(temp_dict)

    
      #graph elaboration
      nodes = []
      node_id = []
      start_pos = []
      end_pos = []
      wid = []
      rho = []
      categories = []

      for item in data['nodes']:
        node_id.append(item)
        nodes.append(data['nodes'][item]['text'])
        start_pos.append(data['nodes'][item]['start_pos'])
        end_pos.append(data['nodes'][item]['end_pos'])
        wid.append(data['nodes'][item]['wid'])
        rho.append(data['nodes'][item]['rho'])
        categories.append(data['nodes'][item]['categories'])

      d_nodes = {'node_id': node_id, 'text' : nodes , 'start_pos' : start_pos , 'end_pos' : end_pos, 'wid' : wid , 'rho' : rho , 'categories' : categories}
      pandas_nodes_df = pd.DataFrame(d_nodes)
      spark_nodes_df=spark.createDataFrame(pandas_nodes_df) 
      

      edges = []
      src_pos = []
      dst_pos = []

      for item in data['sentences']:
        for edge in item['edges']:
            src_pos.append(edge['src_pos'])
            dst_pos.append(edge['dst_pos'])
            edges.append(edge['edge_name'])
      
      d_edges = {'text' : edges , 'src_pos' : src_pos , 'dst_pos' : dst_pos}
      pandas_edges_df = pd.DataFrame(d_edges)
      spark_edges_df=spark.createDataFrame(pandas_edges_df) 

      spark_nodes_df.show()
      spark_edges_df.show()

      #vertex clustering (per document)
      vecAssembler = VectorAssembler(inputCols=["start_pos", "end_pos", "wid", "rho"], outputCol="features")
      new_df = vecAssembler.transform(spark_nodes_df)
      new_df = new_df.drop("start_pos", "end_pos", "wid", "rho")
      new_df = new_df.dropna()
      kmeans = KMeans(k=4, seed=1)  
      model = kmeans.fit(new_df.select('features'))
      predictions = model.transform(new_df)

      predictions.show()

      # Evaluate clustering by computing Silhouette score
      evaluator = ClusteringEvaluator()
      silhouette = evaluator.evaluate(predictions)
      print("Silhouette with squared euclidean distance = " + str(silhouette))
      # Shows the result.
      centers = model.clusterCenters()
      print("Cluster Centers: ")
      for center in centers:
          print(center)


      prediction_groupby = predictions \
            .groupBy("prediction", "text", "categories") \
            .count()\
            .withColumnRenamed("count", "cluster_entities") \
            .orderBy("count", ascending=False) 

      #aggregating the single graph entities
      partial_nodes = spark_nodes_df.groupBy("text", "categories").count()
      partial_edges = spark_edges_df.groupBy("text").count()
      
      #aggregating all the graph entities
      global global_nodes 
      global global_edges

      global_nodes = global_nodes.union(partial_nodes) \
                        .dropna() \
                        .groupBy("text", "categories") \
                        .sum("count") \
                        .withColumnRenamed("sum(count)", "count") \
                        .orderBy("count", ascending=False)  

      global_edges = global_edges.union(partial_edges) \
                        .groupBy("text") \
                        .sum("count") \
                        .withColumnRenamed("sum(count)", "count") \
                        .orderBy("count", ascending=False)  

    
      #writing on es
      resp = es.index(index=GRAPH_ES_INDEX, document=graph_dict)
      print(resp['result'])
      es.indices.refresh(index=GRAPH_ES_INDEX)
      temp_dict.clear()
      graph_dict = None


      fist_nodes = global_nodes.first()
      most_common_node_text = json.dumps({'@timestamp': datetime.now().isoformat(), 'text': str(fist_nodes["text"]), "categories": str(fist_nodes["categories"])})
      resp = es.index(index=GLOBAL_NODES_ES_INDEX, document=most_common_node_text)
      print(resp['result'])
      es.indices.refresh(index=GLOBAL_NODES_ES_INDEX)


      first_edges = global_edges.first()
      most_common_edges_text = json.dumps({'@timestamp': datetime.now().isoformat(), 'text': str(first_edges["text"])})
      resp = es.index(index=GLOBAL_EDGES_ES_INDEX, document=most_common_edges_text)
      print(resp['result'])
      es.indices.refresh(index=GLOBAL_EDGES_ES_INDEX)


      first_cluster = prediction_groupby.first() 
      most_common_cluster = json.dumps({'@timestamp': datetime.now().isoformat(), 'prediction': int(first_cluster["prediction"])})
      resp = es.index(index=CLUSTERING_GROUPBY_ES_INDEX, document=most_common_cluster)
      print(resp['result'])
      es.indices.refresh(index=CLUSTERING_GROUPBY_ES_INDEX)


      nodes_json = {'@timestamp': datetime.now().isoformat(),'node_id': node_id, 'text' : nodes , 'start_pos' : start_pos , 'end_pos' : end_pos, 'wid' : wid , 'rho' : rho , 'categories' : categories}
      nodes_json = json.dumps(nodes_json)
      resp = es.index(index=JSON_NODES_ES_INDEX, document=nodes_json)
      print(resp['result'])
      es.indices.refresh(index=JSON_NODES_ES_INDEX)


      edges_json = {'@timestamp': datetime.now().isoformat(), 'text' : edges , 'src_pos' : src_pos , 'dst_pos' : dst_pos}
      edges_json = json.dumps(edges_json)
      resp = es.index(index=JSON_EDGES_ES_INDEX, document=edges_json)
      print(resp['result'])
      es.indices.refresh(index=JSON_EDGES_ES_INDEX)

    #   break
    # except:
    #   print(500,{})
    #   sleep(10)

#main function
if __name__ == '__main__':

  kafkaServer="kafkaserver:9092"
  topic = "pubMed"
  
  #es configuration 
  es = Elasticsearch(
      ES_ADDRESS,
      verify_certs=False
      )

  try:
    es.options(ignore_status=[400,404]).indices.delete(index=GLOBAL_NODES_ES_INDEX)
    es.options(ignore_status=[400,404]).indices.delete(index=GLOBAL_EDGES_ES_INDEX)
    es.options(ignore_status=[400,404]).indices.delete(index=CLUSTERING_GROUPBY_ES_INDEX)
    es.options(ignore_status=[400,404]).indices.delete(index=JSON_NODES_ES_INDEX)
    es.options(ignore_status=[400,404]).indices.delete(index=JSON_EDGES_ES_INDEX)
    es.options(ignore_status=[400,404]).indices.delete(index=GRAPH_ES_INDEX)
  except:
    print("index must exists")

  es.indices.create(index=GLOBAL_NODES_ES_INDEX, ignore=400)
  es.indices.put_settings(index=GLOBAL_NODES_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  es.indices.create(index=GLOBAL_EDGES_ES_INDEX, ignore=400)
  es.indices.put_settings(index=GLOBAL_EDGES_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  es.indices.create(index=CLUSTERING_GROUPBY_ES_INDEX, ignore=400)
  es.indices.put_settings(index=CLUSTERING_GROUPBY_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  es.indices.create(index=JSON_NODES_ES_INDEX, ignore=400)
  es.indices.put_settings(index=JSON_NODES_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  es.indices.create(index=JSON_EDGES_ES_INDEX, ignore=400)
  es.indices.put_settings(index=JSON_EDGES_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  es.indices.create(index=GRAPH_ES_INDEX, body= mapping, ignore=400)
  es.indices.put_settings(index=GRAPH_ES_INDEX, body={
    "index.mapping.total_fields.limit": 100000
  })

  
  #spark configuration
  schema_nodes = StructType([
    StructField('text', StringType(), True),
    StructField('categories', ArrayType(StringType()), True),
    StructField('count', IntegerType(), True),
    ])

  schema_edges = StructType([
    StructField('text', StringType(), True),
    StructField('count', IntegerType(), True),
    ])

  #spark context creation
  sc = SparkContext(appName="PythonStructuredStreamsKafka")
  spark = SparkSession(sc)
  sc.setLogLevel("WARN")


  #global statistics dataframe 
  global_nodes = spark.createDataFrame([], schema_nodes) #stats dataframe
  global_edges = spark.createDataFrame([], schema_edges) #stats dataframe


  #Streaming reading from kafka
  df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafkaServer) \
    .option("subscribe", topic) \
    .load()

  df.selectExpr("CAST(timestamp AS STRING)","CAST(value AS STRING)") \
    .writeStream \
    .foreachBatch(elaborate) \
    .start() \
    .awaitTermination()

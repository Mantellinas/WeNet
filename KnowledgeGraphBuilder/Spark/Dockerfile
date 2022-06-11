FROM jupyter/pyspark-notebook:spark-3.1.1

RUN pip3 install pyspark numpy elasticsearch pandas requests datetime 

WORKDIR /app

COPY ./code .

ENTRYPOINT ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.1,org.elasticsearch:elasticsearch-spark-30_2.12:8.2.2", "--master", "local[*]", "streaming.py"]   
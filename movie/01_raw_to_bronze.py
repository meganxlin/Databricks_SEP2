# Databricks notebook source
#%run ./includes/configuration

# COMMAND ----------

#%run ./includes/utilities

# COMMAND ----------

import json

movies = {"movie": []}
for i in range(8):
    with open(myPath + f"movie_{i}.json") as f:
        data = json.load(f)
        movies["movie"].append(data["movie"])

dbutils.fs.put(rawPath, json.dumps(movies, indent=2), True)

# COMMAND ----------

#Display the files in the raw path
display(dbutils.fs.ls(f"FileStore/tables/movie_0.json"))

# COMMAND ----------

#Make Notebook Idempotent
dbutils.fs.rm(bronzePath, recurse=True)

# COMMAND ----------

from pyspark.sql.types import StringType
from pyspark.sql.functions import *

raw_movie_DF = rawDF.select(explode("movie").alias("movie"))
display(raw_movie_DF)

# COMMAND ----------

# Ingestion Metadata
from pyspark.sql.functions import current_timestamp, lit
raw_movie_data_df = (raw_movie_DF
                     .select("movie",
                             lit("files.training.databricks.com").alias("datasource"),
                             current_timestamp().alias("ingesttime"),
                             lit("new").alias("status"),
                             current_timestamp().cast("date").alias("ingestdate")
                            )
                    )

# COMMAND ----------

#Partitioning
from pyspark.sql.functions import col
(raw_movie_data_df.select("datasource",
                          "ingesttime",
                          "value",
                          "status",
                          col("ingestdate").alias("p_ingestdate"))
 .write.format("delta")
 .mode("append")
 .partitionBy("p_ingestdate")
 .save(bronzePath)
)

# COMMAND ----------

display(dbutils.fs.ls(bronzePath))

# COMMAND ----------

spark.sql("""
drop table if exists movie_bronze
""")

spark.sql(f"""
create table movie_bronze
using delta
location "{bronzePath}"
""")

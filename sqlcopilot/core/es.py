from elasticsearch import Elasticsearch, ConnectionTimeout
from restful.app.settings import config

ES_HOST = config.elasticsearch.url
ELASTICSEARCH_USER = config.elasticsearch.username
ELASTICSEARCH_PASSWORD = config.elasticsearch.password

# Initialize Elasticsearch client
elastic_search_client = Elasticsearch(
    [ES_HOST],
    http_auth=(ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD),
    max_retries=10,
    retry_on_timeout=True,
)

env = config.elasticsearch.env

# Define index mappings for each model
index_mappings = {
    "business": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "create_time": {"type": "date"},
            },
        }
    },
    "knowledge": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "knowledge_id": {"type": "keyword"},
                "table_id": {"type": "keyword"},
                "key_alpha": {"type": "text"},
                "key_alpha_embedding": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "key_beta": {"type": "text"},
                "value": {"type": "text"},
            },
        },
    },
    "sqlcases": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "table_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "querys": {"type": "text"},
                "sql": {"type": "text"},
            },
        }
    },
    "prompt": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "time_convert_agent": {"type": "text"},
                "nl2sql_agent": {"type": "text"},
                "element_extract_agent": {"type": "text"},
            },
        }
    },
    "tableinfo": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "table_id": {"type": "keyword"},
                "table_name": {"type": "text"},
                "table_comment": {"type": "text"},
                "update_time": {"type": "date"},
                "semantic_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "name_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "comment_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "fields_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "fields": {
                    "type": "nested",
                    "properties": {
                        "field_id": {"type": "keyword"},
                        "filed_name": {"type": "text"},
                        "field_datatype": {"type": "text"},
                        "field_comment": {"type": "text"},
                    },
                },
            },
        },
    },
    "settings": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "table_retrieve_threshold": {"type": "float"},
                "enable_table_auth": {"type": "boolean"},
            },
        }
    },
    "synonym": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "primary": {"type": "keyword"},
                "secondary": {"type": "keyword"},
            },
        }
    },
    "dim_values": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "table_id": {"type": "keyword"},
                "field_id": {"type": "keyword"},
                "value": {"type": "text"},
            },
        }
    },
    "field_inverted": {
        "mappings": {
            "dynamic": "false",
            "properties": {
                "bizid": {"type": "keyword"},
                "field_id": {"type": "keyword"},
                "field_name": {"type": "keyword"},
                "field_comment": {"type": "keyword"},
                "update_time": {"type": "date"},
                "field_name_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "field_comment_vector": {
                    "type": "dense_vector",
                    "dims": 1024,
                    "index": True,
                    "similarity": "cosine",
                },
                "table_id_list": {"type": "text"},
            },
        }
    },
    # Add more mappings for other models as needed
}

# Create indices with mappings
import time

for index_name, mapping in index_mappings.items():
    # Add environment variable to index name
    full_index_name = f"{env}_{index_name}"
    if not elastic_search_client.indices.exists(index=full_index_name):
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                elastic_search_client.indices.create(
                    index=full_index_name, body=mapping
                )
                print(f"Successfully created index {full_index_name}")
                break
            except ConnectionTimeout:
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"Connection timeout while creating index {full_index_name}. Retrying ({retry_count}/{max_retries})..."
                    )
                    time.sleep(2**retry_count)  # Exponential backoff
                else:
                    print(
                        f"Failed to create index {full_index_name} after {max_retries} attempts"
                    )
                    raise

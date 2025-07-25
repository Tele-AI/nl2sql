import datetime
import traceback
from typing import List, Dict, Any, Optional

from elasticsearch.helpers import bulk

# Initialize Elasticsearch client
from core.es import elastic_search_client
from loguru import logger

# Import default templates from agents.nl2sql
from agents.nl2sql import (
    default_time_convert_prompt,
    default_nl2sql_prompt,
    default_key_element_prompt,
    default_sql_explain_prompt,
    default_sql_comment_prompt,
    default_sql_correct_prompt,
    default_query_parse_prompt,
)


class BusinessManager:
    """
    BusinessManager handles all operations related to business domains.
    It manages CRUD operations for business domains and persists data to Elasticsearch.
    """

    def __init__(self):
        self.es = elastic_search_client
        # Initialize embedding service
        from core.embedding import EmbeddingService
        from restful.app.settings import config

        self.embedding_service = EmbeddingService(config=config)
        
        # Get environment variable and create index names with env prefix
        env = config.elasticsearch.env
        self.business_index = f"{env}_business"
        self.prompt_index = f"{env}_prompt"
        self.settings_index = f"{env}_settings"
        self.synonym_index = f"{env}_synonym"
        self.tableinfo_index = f"{env}_tableinfo"
        self.sqlcases_index = f"{env}_sqlcases"
        self.knowledge_index = f"{env}_knowledge"
        self.dim_values_index = f"{env}_dim_values"
        self.field_inverted_index = f"{env}_field_inverted"

    # ==================== Business Domain Operations ====================

    def create_business(self, bizid: str) -> Dict[str, Any]:
        """
        Create a new business domain with the given bizid.

        Args:
            bizid: The business domain ID

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain already exists
            if self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} already exists",
                }

            # Create business domain
            doc = {"bizid": bizid, "create_time": datetime.datetime.now().isoformat()}

            result = self.es.index(index=self.business_index, body=doc, refresh=True)

            if result["result"] == "created":
                # Initialize default prompts for this business domain
                self.initialize_default_prompts(bizid)
                # Initialize default settings for this business domain
                self.initialize_default_settings(bizid)
                return {"status": "success"}
            else:
                return {
                    "status": "error",
                    "message": "Failed to create business domain",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_business(self, bizid: str) -> Dict[str, Any]:
        """
        Delete a business domain with the given bizid.

        Args:
            bizid: The business domain ID

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Delete business domain
            result = self.es.delete_by_query(
                index=self.business_index, body={"query": {"term": {"bizid": bizid}}}
            )

            if result["deleted"] > 0:
                # Also delete related prompts, settings, and synonyms
                self.delete_related_resources(bizid)
                return {"status": "success"}
            else:
                return {
                    "status": "error",
                    "message": "Failed to delete business domain",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_businesses(self) -> Dict[str, Any]:
        """
        List all business domains.

        Returns:
            Dict with status, data, and optional error message
        """
        try:
            # Query all business domains
            result = self.es.search(
                index=self.business_index,
                body={"query": {"match_all": {}}, "size": 1000},
            )

            businesses = []
            for hit in result["hits"]["hits"]:
                businesses.append(
                    {
                        "bizid": hit["_source"]["bizid"],
                        "create_time": hit["_source"]["create_time"],
                    }
                )

            return {"status": "success", "data": businesses}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def business_exists(self, bizid: str) -> bool:
        """
        Check if a business domain exists.

        Args:
            bizid: The business domain ID

        Returns:
            True if the business domain exists, False otherwise
        """
        try:
            result = self.es.search(
                index=self.business_index, body={"query": {"term": {"bizid": bizid}}}
            )
            return result["hits"]["total"]["value"] > 0
        except Exception:
            return False

    # ==================== Prompt Operations ====================

    def initialize_default_prompts(self, bizid: str) -> None:
        """
        Initialize default prompts for a new business domain.

        Args:
            bizid: The business domain ID
        """

        # Convert template objects to strings for storage in Elasticsearch
        default_prompts = {
            "bizid": bizid,
            "time_convert_agent": str(default_time_convert_prompt.template),
            "nl2sql_agent": str(default_nl2sql_prompt.template),
            "element_extract_agent": str(default_key_element_prompt.template),
            "sql_explain_agent": str(default_sql_explain_prompt.template),
            "sql_comment_agent": str(default_sql_comment_prompt.template),
            "sql_correct_agent": str(default_sql_correct_prompt.template),
            "query_parse_agent": str(default_query_parse_prompt.template),
        }

        self.es.index(index=self.prompt_index, body=default_prompts)

    def update_prompts(self, bizid: str, prompts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update prompts for a business domain.

        Args:
            bizid: The business domain ID
            prompts: Dict containing prompt configurations

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Delete existing prompts first
            self.es.delete_by_query(
                index=self.prompt_index,
                body={"query": {"term": {"bizid": bizid}}},
                refresh=True,
            )

            # Create new prompts
            doc = {
                "bizid": bizid,
                "time_convert_agent": prompts["time_convert_agent"],
                "nl2sql_agent": prompts["nl2sql_agent"],
                "element_extract_agent": prompts["element_extract_agent"],
                "sql_explain_agent": prompts["sql_explain_agent"],
                "sql_comment_agent": prompts["sql_comment_agent"],
                "sql_correct_agent": prompts["sql_correct_agent"],
                "query_parse_agent": prompts["query_parse_agent"],
            }

            result = self.es.index(index=self.prompt_index, body=doc, refresh=True)

            if result["result"] in ["created", "updated"]:
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Failed to update prompts"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_prompts(self, bizid: str) -> Dict[str, Any]:
        """
        List prompts for a business domain.

        Args:
            bizid: The business domain ID

        Returns:
            Dict with status, prompts, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "prompts": {},
                }

            # Get prompts
            try:
                result = self.es.search(
                    index=self.prompt_index, body={"query": {"term": {"bizid": bizid}}}
                )

                if result["hits"]["total"]["value"] > 0:
                    source = result["hits"]["hits"][0]["_source"]
                    prompts = {
                        "time_convert_agent": source.get("time_convert_agent"),
                        "nl2sql_agent": source.get("nl2sql_agent"),
                        "element_extract_agent": source.get("element_extract_agent"),
                        "sql_explain_agent": source.get("sql_explain_agent"),
                        "sql_comment_agent": source.get("sql_comment_agent"),
                        "sql_correct_agent": source.get("sql_correct_agent"),
                        "query_parse_agent": source.get("query_parse_agent"),
                    }
                    return {"status": "success", "prompts": prompts}
                else:
                    # If prompts don't exist, return default ones
                    prompts = {
                        "time_convert_agent": "Default time convert agent prompt",
                        "nl2sql_agent": "Default NL2SQL prompt",
                        "element_extract_agent": "Default element extract prompt",
                        "sql_explain_agent": "Default SQL explain prompt",
                        "sql_comment_agent": "Default SQL comment prompt",
                        "sql_correct_agent": "Default SQL correct prompt",
                        "query_parse_agent": "Default query parse prompt",
                    }
                    return {"status": "success", "prompts": prompts}
            except Exception as e:
                return {"status": "error", "message": str(e), "prompts": {}}
        except Exception as e:
            return {"status": "error", "message": str(e), "prompts": {}}


    def get_prompt(self, bizid: str, prompt_type: str) -> Dict[str, Any]:
        """
        Get a specific prompt for a business domain.

        Args:
            bizid: The business domain ID
            prompt_type: The type of prompt to retrieve (e.g., 'time_convert_agent', 'nl2sql_agent', etc.)

        Returns:
            Dict with status, prompt content, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "prompt": None
                }

            # Convert template objects to strings for storage in Elasticsearch
            default_prompts = {
                "time_convert_agent": str(default_time_convert_prompt.template),
                "nl2sql_agent": str(default_nl2sql_prompt.template),
                "element_extract_agent": str(default_key_element_prompt.template),
                "sql_explain_agent": str(default_sql_explain_prompt.template),
                "sql_comment_agent": str(default_sql_comment_prompt.template),
                "sql_correct_agent": str(default_sql_correct_prompt.template),
                "query_parse_agent": str(default_query_parse_prompt.template),
            }

            # Get prompts from ES
            result = self.es.search(
                index=self.prompt_index,
                body={"query": {"term": {"bizid": bizid}}}
            )

            if result["hits"]["total"]["value"] > 0:
                source = result["hits"]["hits"][0]["_source"]
                # If prompt exists in ES, return it, otherwise return default
                prompt = source.get(prompt_type, default_prompts.get(prompt_type))
                if prompt is not None:
                    return {
                        "status": "success",
                        "prompt": prompt
                    }
            
            return {
                "status": "error",
                "message": f"Prompt type '{prompt_type}' not found",
                "prompt": None
            }

        except Exception as e:
            # If ES query fails, return default prompt
            if prompt_type in default_prompts:
                return {
                    "status": "success",
                    "prompt": default_prompts[prompt_type]
                }
            return {
                "status": "error",
                "message": str(e),
                "prompt": None
            }
 

    # ==================== Settings Operations ====================

    def initialize_default_settings(self, bizid: str) -> None:
        """
        Initialize default settings for a new business domain.

        Args:
            bizid: The business domain ID
        """
        default_settings = {
            "bizid": bizid,
            "table_retrieve_threshold": "0.7",
            "enable_table_auth": False,
        }

        self.es.index(index=self.settings_index, body=default_settings)

    def update_settings(self, bizid: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a business domain.

        Args:
            bizid: The business domain ID
            settings: Dict containing settings

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Delete existing settings first
            self.es.delete_by_query(
                index=self.settings_index,
                body={"query": {"term": {"bizid": bizid}}},
                refresh=True,
            )

            # Create new settings
            doc = {
                "bizid": bizid,
                "table_retrieve_threshold": settings["table_retrieve_threshold"],
                "enable_table_auth": settings["enable_table_auth"],
            }

            result = self.es.index(index=self.settings_index, body=doc, refresh=True)

            if result["result"] in ["created", "updated"]:
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Failed to update settings"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_settings(self, bizid: str) -> Dict[str, Any]:
        """
        List settings for a business domain.

        Args:
            bizid: The business domain ID

        Returns:
            Dict with status, data, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "data": {},
                }

            # Get settings
            try:
                result = self.es.search(
                    index=self.settings_index,
                    body={"query": {"term": {"bizid": bizid}}},
                )

                if result["hits"]["total"]["value"] > 0:
                    source = result["hits"]["hits"][0]["_source"]
                    data = {
                        "table_retrieve_threshold": source.get(
                            "table_retrieve_threshold", "0.7"
                        ),
                        "enable_table_auth": source.get("enable_table_auth", False),
                    }
                    return {"status": "success", "data": data}
                else:
                    # If settings don't exist, return default ones
                    data = {
                        "table_retrieve_threshold": "0.7",
                        "enable_table_auth": False,
                    }
                    return {"status": "success", "data": data}
            except Exception as e:
                return {"status": "error", "message": str(e), "data": {}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": {}}

    # ==================== Synonym Operations ====================

    def create_or_update_synonyms(
        self, bizid: str, synonyms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create or update synonyms for a business domain.

        Args:
            bizid: The business domain ID
            synonyms: List of synonym objects

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Process each synonym
            actions = []
            for synonym in synonyms:
                primary = synonym.get("primary")
                if not primary:
                    continue

                # Delete existing synonym first
                self.es.delete_by_query(
                    index=self.synonym_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"primary": primary}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                    wait_for_completion=True,
                )

                doc = {
                    "bizid": bizid,
                    "primary": primary,
                    "secondary": synonym["secondary"],
                }

                actions.append(
                    {
                        "_op_type": "index",
                        "_index": self.synonym_index,
                        "_source": doc,
                    }
                )

            if actions:
                bulk(self.es, actions, refresh=True)
                return {"status": "success"}
            else:
                return {"status": "error", "message": "No valid synonyms provided"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_synonym(self, bizid: str, primary: str) -> Dict[str, Any]:
        """
        Delete a synonym for a business domain.

        Args:
            bizid: The business domain ID
            primary: The primary word of the synonym

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Delete the synonym
            try:
                result = self.es.delete_by_query(
                    index=self.synonym_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"primary": primary}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                )

                if result["deleted"] > 0:
                    return {"status": "success"}
                else:
                    return {
                        "status": "error",
                        "message": f"Synonym with primary word '{primary}' not found",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error deleting synonym: {str(e)}",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_synonyms(
        self, bizid: str, primary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List synonyms for a business domain.

        Args:
            bizid: The business domain ID
            primary: Optional primary word to filter by

        Returns:
            Dict with status, synonyms, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "synonyms": [],
                }

            # Build query
            query = {"bool": {"must": [{"term": {"bizid": bizid}}]}}

            if primary:
                query["bool"]["must"].append({"term": {"primary": primary}})

            # Execute query
            result = self.es.search(
                index=self.synonym_index, body={"query": query, "size": 1000}
            )

            # Process results
            synonyms = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                synonyms.append(
                    {"primary": source["primary"], "secondary": source["secondary"]}
                )

            return {"status": "success", "synonyms": synonyms}
        except Exception as e:
            return {"status": "error", "message": str(e), "synonyms": []}

    # ==================== Helper Methods ====================

    def delete_related_resources(self, bizid: str) -> None:
        """
        Delete all resources related to a business domain.

        Args:
            bizid: The business domain ID
        """
        # Delete prompts
        try:
            self.es.delete_by_query(
                index=self.prompt_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete settings
        try:
            self.es.delete_by_query(
                index=self.settings_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete synonyms
        try:
            self.es.delete_by_query(
                index=self.synonym_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete tableinfo
        try:
            self.es.delete_by_query(
                index=self.tableinfo_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete sqlcases
        try:
            self.es.delete_by_query(
                index=self.sqlcases_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete knowledge
        try:
            self.es.delete_by_query(
                index=self.knowledge_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

        # Delete dimension values
        try:
            self.es.delete_by_query(
                index=self.dim_values_index, body={"query": {"term": {"bizid": bizid}}}
            )
        except Exception:
            pass

    # ==================== TableInfo Operations ====================

    def create_or_update_tableinfo(
        self, bizid: str, table: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create or update table information for a business domain.

        Args:
            bizid: The business domain ID
            table: Table information dictionary

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Create document
            doc = {
                "bizid": bizid,
                "table_id": table["table_id"],
                "table_name": table["table_name"],
                "table_comment": table["table_comment"],
                "fields": table["fields"],
                "update_time": datetime.datetime.now().isoformat()
            }

            # Generate semantic vector for the table information
            semantic_text, fields_text = self._generate_table_semantic_text(table)
            try:
                semantic_vector = self.embedding_service.get_embedding(semantic_text)
                doc["semantic_vector"] = semantic_vector
                doc["name_vector"] = self.embedding_service.get_embedding(table["table_name"])
                doc["comment_vector"] = self.embedding_service.get_embedding(table["table_comment"])
                doc["fields_vector"] = self.embedding_service.get_embedding(fields_text)
            except Exception as e:
                logger.error(
                    f"Error generating semantic vector for table: {str(e)}, {traceback.format_exc()}"
                )
                # Continue even if embedding generation fails
            
            # check generated vector is none
            if doc["semantic_vector"] is None or doc["name_vector"] is None or doc["comment_vector"] is None or doc["fields_vector"] is None:
                logger.error(f"Error generating semantic vector for table: {table['table_name']}")
                return {
                    "status": "error",
                    "message": "Failed to generate semantic vector for table"
                }

            # Check if index exists before performing update
            if not self.es.indices.exists(index=self.tableinfo_index):
                return {
                    "status": "error",
                    "message": f"Index '{self.tableinfo_index}' does not exist"
                }

            # Use the update API with doc_as_upsert to atomically upsert the document
            # This avoids race conditions in concurrent environments
            result = self.es.update(
                index=self.tableinfo_index,
                id=f"{bizid}_{table['table_id']}",  # Use a deterministic ID
                body={"doc": doc, "doc_as_upsert": True},
                refresh=True,
            )

            if result["result"] in ["created", "updated", "noop"]:
                return {"status": "success", "tables": [table]}
            else:
                return {
                    "status": "error",
                    "message": "Failed to create/update table info",
                }
        except Exception as e:
            logger.error(
                f"Error creating/updating table info: {str(e)}, {traceback.format_exc()}"
            )
            return {"status": "error", "message": str(e)}
        
    
    def create_or_update_field_inverted(
            self, bizid: str, tables: List[Dict[str, Any]]
        ) -> Dict[str, Any]:
        """
        Create or update field inverted information for a business domain.

        Args:
            bizid: The business domain ID
            tables: List of table information dictionaries

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }
            
            # 收集所有字段名称
            all_field_names = []
            # 用于记录字段名和表ID的映射关系
            field_table_mapping = {} 
            for table in tables:
                for field in table["fields"]:
                    field_name = field["name"].lower()
                    all_field_names.append(field_name)
                    if field_name not in field_table_mapping:
                        field_table_mapping[field_name] = {
                            "table_ids": set(),
                            "field_comment": field["comment"]
                        }
                    field_table_mapping[field_name]["table_ids"].add(table["table_id"])

            # 批量查询已存在的字段
            if all_field_names:
                existing_fields_query = {
                    "query": {
                        "terms": {
                            "field_name": all_field_names
                        }
                    }
                }
                existing_fields_result = self.es.search(
                    index=self.field_inverted_index,
                    body=existing_fields_query,
                    size=len(all_field_names)
                )

                # 准备批量操作
                bulk_actions = []
                existing_field_names = set()

                # 处理已存在的字段
                for hit in existing_fields_result["hits"]["hits"]:
                    source = hit["_source"]
                    field_name = source["field_name"]
                    existing_field_names.add(field_name)
                    
                    # 更新table_id_list
                    current_table_ids = set(source["table_id_list"])
                    new_table_ids = field_table_mapping[field_name]["table_ids"]
                    updated_table_ids = list(current_table_ids.union(new_table_ids))
                    
                    bulk_actions.append({
                        "_op_type": "update",
                        "_index": self.field_inverted_index,
                        "_id": hit["_id"],
                        "doc": {"table_id_list": updated_table_ids}
                    })

                # 处理新字段
                for field_name in all_field_names:
                    if field_name not in existing_field_names:
                        field_info = field_table_mapping[field_name]
                        # 生成embeddings
                        field_name_vector = self.embedding_service.get_embedding(field_name)
                        field_comment_vector = self.embedding_service.get_embedding(field_info["field_comment"])
                        
                        doc = {
                            "bizid": bizid,
                            "field_name": field_name,
                            "field_comment": field_info["field_comment"],
                            "table_id_list": list(field_info["table_ids"]),
                            "field_name_vector": field_name_vector,
                            "field_comment_vector": field_comment_vector,
                            "update_time": datetime.datetime.now().isoformat()
                        }
                        
                        bulk_actions.append({
                            "_op_type": "index",
                            "_index": self.field_inverted_index,
                            "_source": doc
                        })

                # 执行批量操作
                if bulk_actions:
                    success, failed = bulk(self.es, bulk_actions, refresh=True)
                    if failed:
                        return {
                            "status": "error",
                            "message": f"Failed to process {len(failed)} operations"
                        }
                    return {"status": "success"}
                else:
                    return {"status": "success", "message": "No operations needed"}

            return {"status": "success", "message": "No fields to process"}

        except Exception as e:
            logger.error(f"Error in create_or_update_field_inverted: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _generate_table_semantic_text(self, table: Dict[str, Any]) -> str:
        """
        Generate a text representation of the table for semantic embedding.

        Args:
            table: Table information dictionary

        Returns:
            str: Textual representation of the table for embedding
        """
        table_text = f"Table {table['table_name']}: {table['table_comment']}. "

        fields_text = []
        for field in table["fields"]:
            field_name = field.get("field_name", "")
            field_comment = field.get("field_comment", "")
            field_text = f"Field {field_name}: {field_comment}"
            fields_text.append(field_text)

        return table_text + " ".join(fields_text), " ".join(fields_text)


    def delete_tableinfo(self, bizid: str, table_id: str) -> Dict[str, Any]:
        """
        Delete table information.

        Args:
            bizid: The business domain ID
            table_id: The table ID to delete

        Returns:
            Dict with status and optional error message
        """
        return self.delete_tableinfo_batch(bizid, [table_id])

    def delete_tableinfo_batch(
        self, bizid: str, table_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Delete multiple tables' information and their related resources.

        Args:
            bizid: The business domain ID
            table_ids: List of table IDs to delete

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            if not table_ids:
                return {
                    "status": "error",
                    "message": "No table IDs provided for deletion",
                }

            results = {
                "deleted_tables": 0,
                "deleted_knowledge": 0,
                "deleted_dim_values": 0,
                "errors": [],
            }

            # Delete the tables
            try:
                table_result = self.es.delete_by_query(
                    index=self.tableinfo_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"terms": {"table_id": table_ids}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                    wait_for_completion=True,
                )
                results["deleted_tables"] = table_result.get("deleted", 0)

                # Force a refresh after deletion
                self.es.indices.refresh(index=self.tableinfo_index)

                # Delete related knowledge for these tables
                knowledge_result = self.es.delete_by_query(
                    index=self.knowledge_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"terms": {"table_id": table_ids}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                )
                results["deleted_knowledge"] = knowledge_result.get("deleted", 0)

                # Delete dimension values for these tables
                dim_values_result = self.es.delete_by_query(
                    index=self.dim_values_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"terms": {"table_id": table_ids}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                )
                results["deleted_dim_values"] = dim_values_result.get("deleted", 0)

                if results["deleted_tables"] > 0:
                    return {
                        "status": "success",
                        "message": f"Successfully deleted {results['deleted_tables']} tables, {results['deleted_knowledge']} knowledge entries, and {results['deleted_dim_values']} dimension values.",
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"No tables found with the provided IDs in business domain {bizid}",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error deleting table info: {str(e)}",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_tableinfo(
        self, bizid: str, table_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List table information for a business domain.

        Args:
            bizid: The business domain ID
            table_id: Optional table ID to filter by

        Returns:
            Dict with status, tables, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                logger.warning(f"Business domain with ID {bizid} does not exist")
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "tables": [],
                }

            # Build query
            query = {"bool": {"must": [{"term": {"bizid": bizid}}]}}

            if table_id:
                query["bool"]["must"].append({"term": {"table_id": table_id}})

            # Force index refresh before query
            self.es.indices.refresh(index=self.tableinfo_index)

            # Log query for debugging
            logger.debug(f"Searching tableinfo with query: {query}")

            # Execute query
            result = self.es.search(
                index=self.tableinfo_index, body={"query": query, "size": 1000}
            )

            # Log result count for debugging
            logger.debug(
                f"Found {result['hits']['total']['value']} tables in search result"
            )

            # Process results
            tables = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                tables.append(
                    {
                        "table_id": source["table_id"],
                        "table_name": source["table_name"],
                        "table_comment": source["table_comment"],
                        "fields": source["fields"],
                    }
                )

            return {"status": "success", "tables": tables}
        except Exception as e:
            logger.error(f"Error listing table info: {str(e)}")
            return {"status": "error", "message": str(e), "tables": []}

    def create_or_update_field_value(
        self, bizid: str, table_id: str, field_id: str, values: str
    ) -> Dict[str, Any]:
        """
        Create or update field value information.

        Args:
            bizid: The business domain ID
            table_id: The table ID
            field_id: The field ID
            values: The field values

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Get existing table info
            try:
                result = self.es.search(
                    index=self.tableinfo_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"table_id": table_id}},
                                ]
                            }
                        }
                    },
                )

                if result["hits"]["total"]["value"] == 0:
                    return {
                        "status": "error",
                        "message": f"Table with ID '{table_id}' not found",
                    }

                table_info = result["hits"]["hits"][0]["_source"]
                doc_id = result["hits"]["hits"][0]["_id"]
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error retrieving table info: {str(e)}",
                }

            # Update field values
            for field in table_info["fields"]:
                if field["field_id"] == field_id:
                    field["field_values"] = values
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Field with ID '{field_id}' not found",
                }

            # Save updated table info
            result = self.es.index(
                index=self.tableinfo_index, body=table_info, id=doc_id
            )

            if result["result"] in ["created", "updated"]:
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Failed to update field values"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ==================== SQLCases Operations ====================

    def create_or_update_sqlcases(
        self, bizid: str, sqlcases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create or update SQL cases for a business domain.

        Args:
            bizid: The business domain ID
            sqlcases: List of SQL case objects

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Process each SQL case
            actions = []
            for sqlcase in sqlcases:
                case_id = sqlcase.get("case_id")
                if not case_id:
                    continue

                # Delete existing SQL case first
                self.es.delete_by_query(
                    index=self.sqlcases_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"case_id": case_id}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                    wait_for_completion=True,
                )

                doc = {
                    "bizid": bizid,
                    "case_id": case_id,
                    "querys": sqlcase["querys"],
                    "sql": sqlcase["sql"],
                }

                actions.append(
                    {
                        "_op_type": "index",
                        "_index": self.sqlcases_index,
                        "_source": doc,
                    }
                )

            if actions:
                bulk(self.es, actions, refresh=True)
                return {"status": "success", "sqlcases": sqlcases}
            else:
                return {"status": "error", "message": "No valid SQL cases provided"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_sqlcase(self, bizid: str, case_id: str) -> Dict[str, Any]:
        """
        Delete a SQL case.

        Args:
            bizid: The business domain ID
            case_id: The case ID to delete

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Delete the SQL case
            try:
                result = self.es.delete_by_query(
                    index=self.sqlcases_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"case_id": case_id}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                )

                if result["deleted"] > 0:
                    return {"status": "success"}
                else:
                    return {
                        "status": "error",
                        "message": f"SQL case with ID '{case_id}' not found",
                    }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error deleting SQL case: {str(e)}",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_sqlcases(self, bizid: str) -> Dict[str, Any]:
        """
        List SQL cases for a business domain.

        Args:
            bizid: The business domain ID

        Returns:
            Dict with status, sqlcases, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "sqlcases": [],
                }

            # Build query
            query = {"bool": {"must": [{"term": {"bizid": bizid}}]}}

            # Execute query
            result = self.es.search(
                index=self.sqlcases_index, body={"query": query, "size": 1000}
            )

            # Process results
            sqlcases = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                sqlcases.append(
                    {
                        "case_id": source["case_id"],
                        "querys": source["querys"],
                        "sql": source["sql"],
                    }
                )

            return {"status": "success", "sqlcases": sqlcases}
        except Exception as e:
            return {"status": "error", "message": str(e), "sqlcases": []}

    # ==================== Knowledge Operations ====================

    def create_or_update_knowledge(
        self, bizid: str, knowledges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create or update knowledge entries for a business domain.

        Args:
            bizid: The business domain ID
            knowledges: List of knowledge objects

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Process each knowledge entry
            actions = []
            results = []
            for knowledge in knowledges:
                knowledge_id = knowledge.get("knowledge_id")
                if not knowledge_id:
                    continue

                # Delete existing knowledge first
                self.es.delete_by_query(
                    index=self.knowledge_index,
                    body={
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"bizid": bizid}},
                                    {"term": {"knowledge_id": knowledge_id}},
                                ]
                            }
                        }
                    },
                    refresh=True,
                    wait_for_completion=True,
                )

                doc = {
                    "bizid": bizid,
                    "knowledge_id": knowledge_id,
                    "table_id": knowledge["table_id"],
                    "key_alpha": knowledge["key_alpha"],
                    "key_beta": knowledge["key_beta"],
                    "value": knowledge["value"],
                }

                # 如果提供了embedding，则添加到文档中
                if "key_alpha_embedding" in knowledge:
                    doc["key_alpha_embedding"] = knowledge["key_alpha_embedding"]
                elif knowledge["key_alpha"]:
                    # 请求语义模型服务，获得embedding
                    doc["key_alpha_embedding"] = self.embedding_service.get_embedding(
                        text=knowledge["key_alpha"]
                    )
                    emb = doc["key_alpha_embedding"]

                actions.append(
                    {
                        "_op_type": "index",
                        "_index": self.knowledge_index,
                        "_source": doc,
                    }
                )
                results.append(
                    {
                        "knowledge_id": knowledge_id,
                        "status": "success",
                        "message": "Successfully created/updated",
                    }
                )

            if actions:
                bulk(self.es, actions, refresh=True)
                return {"status": "success", "data": results}
            else:
                return {
                    "status": "error",
                    "message": "No valid knowledge entries provided",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_knowledge(self, bizid: str, knowledge_ids: List[str]) -> Dict[str, Any]:
        """
        Delete knowledge entries for a business domain.

        Args:
            bizid: The business domain ID
            knowledge_ids: List of knowledge IDs to delete

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            if not knowledge_ids:
                return {
                    "status": "error",
                    "message": "No knowledge IDs provided for deletion",
                }

            # Delete knowledge entries
            result = self.es.delete_by_query(
                index=self.knowledge_index,
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"bizid": bizid}},
                                {"terms": {"knowledge_id": knowledge_ids}},
                            ]
                        }
                    }
                },
                refresh=True,
            )

            if result["deleted"] > 0:
                return {
                    "status": "success",
                    "message": f"Successfully deleted {result['deleted']} knowledge entries",
                }
            else:
                return {
                    "status": "error",
                    "message": f"No knowledge entries found for the provided IDs in business domain {bizid}",
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting knowledge entries: {str(e)}",
            }

    def list_knowledge(
        self, bizid: str, table_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List knowledge entries for a business domain.

        Args:
            bizid: The business domain ID
            table_id: Optional table ID to filter by

        Returns:
            Dict with status, data, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "data": [],
                }

            # Build query
            query = {"bool": {"must": [{"term": {"bizid": bizid}}]}}

            if table_id:
                query["bool"]["must"].append({"term": {"table_id": table_id}})

            # Execute query
            result = self.es.search(
                index=self.knowledge_index, body={"query": query, "size": 1000}
            )

            # Process results
            knowledge_entries = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                knowledge_entries.append(
                    {
                        "knowledge_id": source["knowledge_id"],
                        "table_id": source["table_id"],
                        "key_alpha": source["key_alpha"],
                        "key_beta": source["key_beta"],
                        "value": source["value"],
                    }
                )

            return {"status": "success", "data": knowledge_entries}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    # ==================== Dimension Values Operations ====================

    def create_or_update_dim_value(
        self, bizid: str, table_id: str, field_id: str, values: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Create or update dimension values for a field.

        Args:
            bizid: The business domain ID
            table_id: The table ID
            field_id: The field ID
            values: List of value objects with 'value' field

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            # Process each dimension value
            actions = []
            for val in values:
                value = val.get("value", "")
                if not value:
                    continue

                doc = {
                    "bizid": bizid,
                    "table_id": table_id,
                    "field_id": field_id,
                    "value": value,
                }

                actions.append(
                    {
                        "_op_type": "index",
                        "_index": self.dim_values_index,
                        "_source": doc,
                    }
                )

            if actions:
                bulk(self.es, actions)
                return {"status": "success"}
            else:
                return {
                    "status": "error",
                    "message": "No valid dimension values provided",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_dim_value(
        self, bizid: str, table_id: str, field_id: str, value: str = None
    ) -> Dict[str, Any]:
        """
        Delete dimension values for a field. If value is provided, only that value is deleted.
        Otherwise, all values for the field are deleted.

        Args:
            bizid: The business domain ID
            table_id: The table ID
            field_id: The field ID
            value: Optional specific value to delete

        Returns:
            Dict with status and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                }

            if value:
                # Delete specific value
                try:
                    result = self.es.delete_by_query(
                        index=self.dim_values_index,
                        body={
                            "query": {
                                "bool": {
                                    "must": [
                                        {"term": {"bizid": bizid}},
                                        {"term": {"table_id": table_id}},
                                        {"term": {"field_id": field_id}},
                                        {"term": {"value": value}},
                                    ]
                                }
                            }
                        },
                    )

                    if result["deleted"] > 0:
                        return {"status": "success"}
                    else:
                        return {
                            "status": "error",
                            "message": f"Dimension value '{value}' not found for field '{field_id}'",
                        }
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Error deleting dimension value: {str(e)}",
                    }
            else:
                # Delete all values for the field
                query = {
                    "bool": {
                        "must": [
                            {"term": {"bizid": bizid}},
                            {"term": {"table_id": table_id}},
                            {"term": {"field_id": field_id}},
                        ]
                    }
                }

                self.es.delete_by_query(
                    index=self.dim_values_index, body={"query": query}
                )
                return {"status": "success"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_dim_values(
        self, bizid: str, table_id: Optional[str] = None, field_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List dimension values for a business domain, optionally filtered by table and field.

        Args:
            bizid: The business domain ID
            table_id: Optional table ID to filter by
            field_id: Optional field ID to filter by

        Returns:
            Dict with status, values, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "values": [],
                }

            # Build query
            query = {"bool": {"must": [{"term": {"bizid": bizid}}]}}

            if table_id:
                query["bool"]["must"].append({"term": {"table_id": table_id}})

            if field_id:
                query["bool"]["must"].append({"term": {"field_id": field_id}})

            # Execute query
            result = self.es.search(
                index=self.dim_values_index, body={"query": query, "size": 1000}
            )

            # Process results
            values = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                values.append(
                    {
                        "table_id": source["table_id"],
                        "field_id": source["field_id"],
                        "value": source["value"],
                    }
                )

            return {"status": "success", "values": values}
        except Exception as e:
            return {"status": "error", "message": str(e), "values": []}

    def search_dim_values(
        self,
        bizid: str,
        query: str,
        table_id: Optional[str] = None,
        field_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search dimension values using fuzzy matching on value field.

        Args:
            bizid: The business domain ID
            query: The search query text (can be a string or list of strings)
            table_id: Optional table ID to filter by
            field_id: Optional field ID to filter by

        Returns:
            Dict with status, values, and optional error message
        """
        try:
            # Check if business domain exists
            if not self.business_exists(bizid):
                return {
                    "status": "error",
                    "message": f"Business domain with ID {bizid} does not exist",
                    "values": [],
                }

            # Build query
            must_clauses = [{"term": {"bizid": bizid}}]

            if table_id:
                must_clauses.append({"term": {"table_id": table_id}})

            if field_id:
                must_clauses.append({"term": {"field_id": field_id}})

            # Handle array input by creating separate match queries for each value
            if isinstance(query, list):
                should_clauses = [
                    {"match": {"value": {"query": q, "fuzziness": "AUTO"}}}
                    for q in query
                ]
            else:
                should_clauses = [
                    {"match": {"value": {"query": query, "fuzziness": "AUTO"}}}
                ]

            search_query = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "should": should_clauses,
                        "minimum_should_match": 1,
                    }
                },
                "size": 100,
            }

            # Execute query
            logger.debug(f"dim search query {search_query}")
            result = self.es.search(index=self.dim_values_index, body=search_query)
            logger.debug(f"dim search result {result}")

            # Process results
            values = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                values.append(
                    {
                        "table_id": source["table_id"],
                        "field_id": source["field_id"],
                        "value": source["value"],
                        "score": hit["_score"],
                    }
                )

            # Sort by score descending
            values.sort(key=lambda x: x["score"], reverse=True)

            return {"status": "success", "values": values}
        except Exception as e:
            logger.error(f"Error searching dimension values: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return {"status": "error", "message": str(e), "values": []}

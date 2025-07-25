import traceback

from loguru import logger

from core.business import BusinessManager


class MetaService(object):
    """
    库表信息元数据服务
    """

    def __init__(self):
        self.biz_manager = BusinessManager()
        self.es = self.biz_manager.es
        self.tableinfo_index = self.biz_manager.tableinfo_index
        self.knowledge_index = self.biz_manager.knowledge_index
        self.field_inverted_index = self.biz_manager.field_inverted_index
        self.embedding_service = self.biz_manager.embedding_service
    def match_table_values(self, bizid: str, query: str) -> list:
        """
        根据查询文本匹配表字段值

        Args:
            bizid: 业务域ID
            query: 查询文本

        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "table_id": "表ID",
                "table_name": "表名",
                "field_id": "字段ID",
                "field_name": "字段名",
                "field_values": "匹配的字段值"
            }
        """
        try:
            # 构建ES查询
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"bizid": bizid}},
                            {
                                "nested": {
                                    "path": "fields",
                                    "query": {
                                        "bool": {
                                            "must": [
                                                {
                                                    "exists": {
                                                        "field": "fields.field_values"
                                                    }
                                                },
                                                {
                                                    "match": {
                                                        "fields.field_values": query
                                                    }
                                                },
                                            ]
                                        }
                                    },
                                    "inner_hits": {},
                                }
                            },
                        ]
                    }
                }
            }

            # 执行ES查询
            result = self.es.search(index=self.tableinfo_index, body=search_query)

            matched_results = []
            for hit in result["hits"]["hits"]:
                table_id = hit["_source"]["table_id"]
                table_name = hit["_source"]["table_name"]

                # 处理嵌套的字段匹配结果
                for inner_hit in hit["inner_hits"]["fields"]["hits"]["hits"]:
                    field = inner_hit["_source"]
                    matched_results.append(
                        {
                            "table_id": table_id,
                            "table_name": table_name,
                            "field_id": field["field_id"],
                            "field_name": field["name"],
                            "field_values": field["field_values"],
                        }
                    )

            return matched_results

        except Exception as e:
            logger.error(
                f"Error in match_table_values: {str(e)}\n{traceback.format_exc()}"
            )
            return []

    def match_knowledge_by_embedding(
        self, bizid: str, query_embedding: list, top_k: int = 5, min_score: float = 0.7
    ) -> list:
        """
        根据语义向量匹配最相似的知识条目, 根据只是的alpha标签

        Args:
            bizid: 业务域ID
            query_embedding: 查询文本的向量表示，维度应与索引中的向量维度一致
            top_k: 返回的最大结果数量
            min_score: 最小相似度阈值，低于此值的结果将被过滤

        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "knowledge_id": "知识ID",
                "table_id": "表ID",
                "key_alpha": "知识的A标签",
                "key_beta": "知识的B标签",
                "value": "知识的值",
                "score": "相似度得分"
            }
        """
        try:
            # 构建ES查询，使用KNN查询
            search_query = {
                "query": {
                    "bool": {
                        "filter":[
                            {
                                "term": {
                                    "bizid": bizid
                                }
                            },
                            {
                                "exists": {
                                    "field": "key_alpha_embedding"
                                }
                            }
                        ],
                        "must": [
                            {
                                "bool": {  
                                    "should": [
                                        {
                                            "script_score": {
                                                "query": {
                                                    "match_all": {}
                                                },
                                                "script": {
                                                    "source": """
                                                        if (doc['key_alpha_embedding'].size() == 0) {
                                                            return 0.0;
                                                        }
                                                        return cosineSimilarity(params.vector, 'key_alpha_embedding');
                                                    """,
                                                    "params": {
                                                        "vector": query_embedding
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            }       
                        ]
                    }
                },
                "size": top_k,
                "sort": {
                    "_score": "desc"
                }
            }

            # 执行ES查询
            result = self.es.search(index=self.knowledge_index, body=search_query)

            matched_results = []
            for hit in result["hits"]["hits"]:
                score = hit["_score"]

                # 过滤低于阈值的结果
                if score < min_score:
                    continue

                source = hit["_source"]
                matched_results.append(
                    {
                        "knowledge_id": source["knowledge_id"],
                        "table_id": source["table_id"],
                        "key_alpha": source["key_alpha"],
                        "key_beta": source["key_beta"],
                        "value": source["value"],
                        "score": score,
                    }
                )

            # 根据score从高到低排序

            return matched_results

        except Exception as e:
            logger.error(
                f"Error in match_knowledge_by_embedding: {str(e)}\n{traceback.format_exc()}"
            )
            return []

    def match_tables_by_embedding(
        self, bizid: str, query_embedding: list, top_k: int = 5, min_score: float = 0.7
    ) -> list:
        """
        根据语义向量匹配最相似的表

        Args:
            bizid: 业务域ID
            query_embedding: 查询文本的向量表示，维度应与索引中的向量维度一致
            top_k: 返回的最大结果数量
            min_score: 最小相似度阈值，低于此值的结果将被过滤

        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "table_id": "表ID",
                "table_name": "表名",
                "table_comment": "表注释",
                "fields": "表字段列表",
                "score": "相似度得分"
            }
        """
        try:
            # 构建ES查询 - 使用原生KNN查询
            search_query = {
                "query": {
                    "bool": {
                        "filter":[
                            {
                                "term": {
                                    "bizid": bizid
                                }
                            }
                        ],
                        "must": [
                            {
                                "bool": {  
                                    "should": [
                                        {
                                            "script_score": {
                                                "query": {
                                                    "match_all": {}
                                                },
                                                "script": {
                                                    "source": "cosineSimilarity(params.vector, 'semantic_vector')",
                                                    "params": {
                                                        "vector": query_embedding
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            }       
                        ]
                    }
                },
                "size": top_k,
                "sort": {
                    "_score": "desc"
                }
            }

            # 执行ES查询
            result = self.es.search(index=self.tableinfo_index, body=search_query)

            matched_results = []
            for hit in result["hits"]["hits"]:
                # Debug information for table retrieval
                source = hit["_source"]
                score = hit["_score"]
                normalized_score = score

                # 过滤低于阈值的结果
                if normalized_score < min_score:
                    continue

                matched_results.append(
                    {
                        "table_id": source["table_id"],
                        "table_name": source["table_name"],
                        "table_comment": source["table_comment"],
                        "fields": source["fields"],
                        "score": normalized_score,
                    }
                )

            # 根据score从高到低排序
            matched_results.sort(key=lambda x: x["score"], reverse=True)

            return matched_results

        except Exception as e:
            logger.error(
                f"Error in match_tables_by_embedding: {str(e)}\n{traceback.format_exc()}"
            )
            return []

    def match_tables_by_deep_semantic(
        self, bizid: str, query_embedding: list, top_k: int = 5, min_score: float = 0.7, recommended_tables: list = []
    ) -> list:
        """
        根据语义向量分别针对名字、描述和字段进行深度匹配，返回最相似的表
        相关性分数计算公式：a * max(tablename, tableDesc) + b * field
        使用归一化处理确保分数计算的公平性

        Args:
            bizid: 业务域ID
            query_embedding: 查询文本的向量表示，维度应与索引中的向量维度一致
            top_k: 返回的最大结果数量
            min_score: 最小相似度阈值，低于此值的结果将被过滤
            recommended_tables: 预先推荐的一些表（暂不使用）
        
        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "table_id": "表ID",
                "table_name": "表名",
                "table_comment": "表注释",
                "fields": "表字段列表",
                "score": "相似度得分"
            }
        """
        try:
            # 分别查询表名、表描述和字段的相似度
            name_query = {
                "query": {
                    "bool": {
                        "filter":[
                            {
                                "term": {
                                    "bizid": bizid
                                }
                            },
                            {
                                "exists": {
                                    "field": "name_vector"
                                }
                            }
                        ],
                        "must": [
                            {
                                "bool": {  
                                    "should": [
                                        {
                                            "script_score": {
                                                "query": {
                                                    "match_all": {}
                                                },
                                                "script": {
                                                    "source": """
                                                        if (doc['name_vector'].size() == 0) {
                                                            return 0.0;
                                                        }
                                                        return cosineSimilarity(params.vector, 'name_vector');
                                                    """,
                                                    "params": {
                                                        "vector": query_embedding
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            }       
                        ]
                    }
                },
                "size": top_k,
                "sort": {
                    "_score": "desc"
                }
            }

            comment_query = {
                "query": {
                    "bool": {
                        "filter":[
                            {
                                "term": {
                                    "bizid": bizid
                                }
                            },
                            {
                                "exists": {
                                    "field": "comment_vector"
                                }
                            }
                        ],
                        "must": [
                            {
                                "bool": {  
                                    "should": [
                                        {
                                            "script_score": {
                                                "query": {
                                                    "match_all": {}
                                                },
                                                "script": {
                                                    "source": """
                                                        if (doc['comment_vector'].size() == 0) {
                                                            return 0.0;
                                                        }
                                                        return cosineSimilarity(params.vector, 'comment_vector');
                                                    """,
                                                    "params": {
                                                        "vector": query_embedding
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                }
                            }       
                        ]
                    }
                },
                "size": top_k,
                "sort": {
                    "_score": "desc"
                }
            }

            # 执行查询时添加错误处理
            try:
                name_results = self.es.search(index=self.tableinfo_index, body=name_query)
            except Exception as name_error:
                logger.warning(f"Name vector search failed: {name_error}, 回退到空结果")
                name_results = {"hits": {"hits": []}}
            
            try:
                comment_results = self.es.search(index=self.tableinfo_index, body=comment_query)
            except Exception as comment_error:
                logger.warning(f"Comment vector search failed: {comment_error}, 回退到空结果")
                comment_results = {"hits": {"hits": []}}

            # 创建表ID到分数的映射
            table_scores = {}
            
            # 处理表名和表描述的分数
            for hit in name_results["hits"]["hits"]:
                table_id = hit["_source"]["table_id"]
                name_score = hit["_score"]
                table_scores[table_id] = {
                    "name_score": name_score,
                    "comment_score": 0.0,
                    "fields_score": 0.0,
                    "has_name": True,
                    "has_comment": False,
                    "has_fields": False,
                    "source": hit["_source"]
                }

            for hit in comment_results["hits"]["hits"]:
                table_id = hit["_source"]["table_id"]
                comment_score = hit["_score"]
                if table_id in table_scores:
                    table_scores[table_id]["comment_score"] = comment_score
                    table_scores[table_id]["has_comment"] = True
                else:
                    table_scores[table_id] = {
                        "name_score": 0.0,
                        "comment_score": comment_score,
                        "fields_score": 0.0,
                        "has_name": False,
                        "has_comment": True,
                        "has_fields": False,
                        "source": hit["_source"]
                    }

            # 计算最终分数
            matched_results = []
            for table_id, scores in table_scores.items():
                # ===================== 按照表名称和描述计算相关性 =====================
                name_comment_scores = []
                
                # 处理表名相似度
                if scores["has_name"]:
                    name_comment_scores.append(scores["name_score"])
                
                # 处理表描述相似度
                if scores["has_comment"]:
                    name_comment_scores.append(scores["comment_score"])
                
                # 如果表名和表描述都有分数，取最大值作为最终分数
                final_score = max(name_comment_scores) if name_comment_scores else 0.0

                # 过滤低于阈值的结果
                if final_score < min_score:
                    continue

                matched_results.append({
                    "table_id": table_id,
                    "table_name": scores["source"]["table_name"],
                    "table_comment": scores["source"]["table_comment"],
                    "fields": scores["source"]["fields"],
                    "score": final_score
                })

            logger.debug(f"deep semantic search results: {matched_results}")

            # 将获得的matched_results和recommended_tables合并
            merged_results = {}

            # 首先添加语义匹配的结果
            for result in matched_results:
                table_id = result["table_id"]
                merged_results[table_id] = result
                
            # 合并推荐表的结果
            for table in recommended_tables:
                table_id = table["table_id"]
                if table_id in merged_results:
                    # 如果表已存在，取分数最大值
                    merged_results[table_id]["score"] = max(
                        merged_results[table_id]["score"],
                        table.get("score", 0.0)
                    )
                else:
                    # 如果表不存在，直接添加
                    merged_results[table_id] = table

            # 将合并后的结果转换为列表
            final_results = list(merged_results.values())

            # 根据score从高到低排序
            final_results.sort(key=lambda x: x["score"], reverse=True)

            # 只返回top_k个结果
            return final_results[:top_k]

        except Exception as e:
            logger.error(
                f"Error in match_tables_by_deep_semantic: {str(e)}\n{traceback.format_exc()}"
            )
            return []

    def match_knowledge_by_key_beta(self, bizid: str, query: str) -> list:
        """
        根据查询文本匹配包含在key_beta标签中的知识条目
        要求query完全包含key_beta列表中的至少一个元素才算匹配
        实现为两步过滤：
        1. 先用ES的match查询做粗筛选
        2. 再在内存中精确判断query是否包含key_beta元素

        Args:
            bizid: 业务域ID
            query: 查询文本

        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "knowledge_id": "知识ID",
                "table_id": "表ID",
                "key_alpha": "知识的A标签",
                "key_beta": "知识的B标签",
                "value": "知识的值"
            }
        """
        try:
            # 对查询进行规范化处理
            query = query.strip()

            # 步骤1: 使用ES的match查询做粗筛选
            search_query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"bizid": bizid}},
                            {"match": {"key_beta": query}},  # 粗筛选，没有精确要求
                        ]
                    }
                },
                "size": 1000,  # 限制获取的最大数量
            }

            # 执行ES查询
            result = self.es.search(index=self.knowledge_index, body=search_query)

            # 步骤2: 在内存中精确匹配
            matched_results = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                key_beta_list = source.get("key_beta", [])

                # 检查query是否包含key_beta中的任何一个元素
                matched = False
                for beta in key_beta_list:
                    if beta is None or str(beta).strip() == "":
                        continue

                    str_beta = str(beta).strip()
                    if query.find(str_beta) != -1:
                        matched = True
                        break

                if matched:
                    matched_results.append(
                        {
                            "knowledge_id": source["knowledge_id"],
                            "table_id": source["table_id"],
                            "key_alpha": source["key_alpha"],
                            "key_beta": source["key_beta"],
                            "value": source["value"],
                        }
                    )

            return matched_results

        except Exception as e:
            logger.error(
                f"Error in match_knowledge_by_key_beta: {str(e)}\n{traceback.format_exc()}"
            )
            return []


    def match_fields_by_entity(self, bizid: str, entity_list: list, top_k: int = 10) -> list:
        """
        根据实体名称匹配字段
        Args:
            bizid: 业务域ID
            entity_list: 实体名称列表

        Returns:
            list: 匹配结果列表，每个元素包含：
            {
                "entity": "实体名称",
                "matches": [
                    {
                        "field_name": "字段名",
                        "field_comment": "字段注释",
                        "table_id_list": "表ID列表",
                        "score": "相似度得分"
                    }
                ]
            }
        """
        try:
            # 存储每个实体的匹配结果
            entity_matches = []
            
            for entity in entity_list:
                # 查询倒排索引，向量匹配field_name和field_comment，取最高分
                entity_embedding = self.embedding_service.get_embedding(entity)
                name_query = {
                    "query": {
                        "bool": {
                            "filter":[
                                {
                                    "term": {
                                        "bizid": bizid
                                    }
                                }
                            ],
                            "must": [
                                {
                                    "bool": {  
                                        "should": [
                                            {
                                                "script_score": {
                                                    "query": {
                                                        "match_all": {}
                                                    },
                                                    "script": {
                                                        "source": "cosineSimilarity(params.vector, 'field_name_vector')",
                                                        "params": {
                                                            "vector": entity_embedding
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }       
                            ]
                        }
                    },
                    "size": top_k,
                    "sort": {
                        "_score": "desc"
                    }
                }

                comment_query = {
                    "query": {
                        "bool": {
                            "filter":[
                                {
                                    "term": {
                                        "bizid": bizid
                                    }
                                }
                            ],
                            "must": [
                                {
                                    "bool": {  
                                        "should": [
                                            {
                                                "script_score": {
                                                    "query": {
                                                        "match_all": {}
                                                    },
                                                    "script": {
                                                        "source": "cosineSimilarity(params.vector, 'field_comment_vector')",
                                                        "params": {
                                                            "vector": entity_embedding
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }       
                            ]
                        }
                    },
                    "size": top_k,
                    "sort": {
                        "_score": "desc"
                    }
                }

                # 执行ES查询
                name_result = self.es.search(index=self.field_inverted_index, body=name_query)
                comment_result = self.es.search(index=self.field_inverted_index, body=comment_query)

                # 存储当前实体的匹配结果
                entity_field_matches = {}

                # 处理name_result的结果
                for hit in name_result["hits"]["hits"]:
                    field_name = hit["_source"]["field_name"]
                    field_comment = hit["_source"]["field_comment"]
                    table_id_list = hit["_source"]["table_id_list"]
                    score = hit["_score"]

                    # 如果结果已存在，取最高分
                    if field_name in entity_field_matches:
                        entity_field_matches[field_name]["score"] = max(
                            entity_field_matches[field_name]["score"],
                            score
                        )
                    else:
                        entity_field_matches[field_name] = {
                            "field_name": field_name,
                            "field_comment": field_comment,
                            "table_id_list": table_id_list,
                            "score": score
                        }

                # 处理comment_result的结果
                for hit in comment_result["hits"]["hits"]:
                    field_name = hit["_source"]["field_name"]
                    field_comment = hit["_source"]["field_comment"]
                    table_id_list = hit["_source"]["table_id_list"]
                    score = hit["_score"]

                    # 如果结果已存在，取最高分
                    if field_name in entity_field_matches:
                        entity_field_matches[field_name]["score"] = max(
                            entity_field_matches[field_name]["score"],
                            score
                        )
                    else:
                        entity_field_matches[field_name] = {
                            "field_name": field_name,
                            "field_comment": field_comment,
                            "table_id_list": table_id_list,
                            "score": score
                        }

                # 将当前实体的匹配结果转换为列表并排序
                matches = list(entity_field_matches.values())
                matches.sort(key=lambda x: x["score"], reverse=True)
                
                # 添加到实体匹配结果列表
                entity_matches.append({
                    "entity": entity,
                    "matches": matches[:top_k]  # 只保留top_k个结果
                })

            return entity_matches

        except Exception as e:
            logger.error(
                f"Error in match_fields_by_entity: {str(e)}\n{traceback.format_exc()}"
            )
            return []

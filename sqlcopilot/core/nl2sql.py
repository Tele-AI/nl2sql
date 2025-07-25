# from ..agents import *
import sys
from pathlib import Path
from string import Template

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, Optional, List, Any

import json
from loguru import logger
from more_itertools import collapse

from agents.nl2sql import KeyElementExtractAgent, TimeConvertAgent, Text2SQLAgent, QueryParseAgent
from core.business import BusinessManager
from core.embedding import EmbeddingService
from core.meta import MetaService


class NL2SQLService:
    def __init__(self) -> None:
        self.biz_manager = BusinessManager()
        self.meta = MetaService()

    def _table_recommend(self, query: str) -> str:
        pass

    def _find_synonym(self, query: Optional[str], bizid: str) -> Dict:
        synonym = self.biz_manager.list_synonyms(bizid)["synonyms"]
        ss = {}

        for s in synonym:
            secondary = s["secondary"]
            for sec in secondary:
                if sec in query:
                    ss.update({s["primary"]: sec})

        return ss

    def _key_element_info_concat(
        self, query: Optional[str], element_text: Optional[str]
    ) -> str:
        # element should be a json object
        try:
            element = json.loads(element_text)
        except Exception as e:
            return ""

        return element

    def _render_fewshot(self, fewshot: List[Dict]) -> str:
        if not fewshot:
            return ""

        p = "以下是sql案例库中与问题相似的案例: \n"
        for case in fewshot:
            p += f"问题： {case['querys']}\nSQL: {case['sql']}\n"

        return p

    def _render_synonym(self, synonym: Dict) -> str:
        if not synonym:
            return ""

        p = "\n在用户的问题中, \n"
        for prim, sec in synonym.items():
            p += f"{sec} 是指 {prim}\n"

        return p

    def _render_field_value(
        self, field_value_info: List[Dict], table_info_list: List[Dict]
    ) -> str:
        # 将这些DimsInfo按照以下方式拼接
        # 例如:
        #
        # 表order_detail_shenzhen中，
        # 1. order_region的值例如：'南山区'表示南山区，'福田区'表示福田区，'罗湖区'表示罗湖区；
        # 2. is_overdue的值例如： '1' 表示超期;
        # 3. street的值例如：'1001'表示罗湖街道;

        if not field_value_info:
            return ""

        # Group field values by table
        table_values = {}
        for fv in field_value_info:
            table_id = fv["table_id"]
            if table_id not in table_values:
                table_values[table_id] = []
            table_values[table_id].append(fv)

        # Build output string
        output = []
        for table_id, values in table_values.items():
            # Find matching table info
            table_info = next(
                (t for t in table_info_list if t["table_id"] == table_id), None
            )
            if not table_info:
                continue

            table_str = f"\n表{table_info['table_name']}中，"
            field_strs = []

            # Group values by field
            field_values = {}
            for v in values:
                field_id = v["field_id"]
                if field_id not in field_values:
                    field_values[field_id] = []
                field_values[field_id].append(v["value"])

            # Build field value strings
            for i, (field_id, vals) in enumerate(field_values.items(), 1):
                # Get field info
                field = next(
                    (f for f in table_info["fields"] if f["field_id"] == field_id), None
                )
                if not field:
                    continue

                # Format values list
                value_str = ", ".join(f"'{v}'" for v in vals[:3])
                field_str = f"{i}. {field['name']}的值例如：{value_str}；"
                field_strs.append(field_str)

            if field_strs:
                output.append(table_str + "\n" + "\n".join(field_strs))

        return "\n".join(output)

    def _render_schema_ddl(self, table_info_list: List[Dict]) -> str:
        """
        根据表信息列表渲染数据库schema的DDL格式

        Args:
            table_info_list: 表信息列表

        Returns:
            str: DDL格式的schema定义
        """
        ddl = []
        for table_info in table_info_list:
            try:
                # 构建CREATE TABLE语句
                create_stmt = f"CREATE TABLE {table_info['table_name']} (\n"

                # 添加字段定义
                field_defs = []
                for field in table_info["fields"]:
                    field_def = f"    {field['name']} {field['datatype']}"
                    if field.get("comment"):
                        field_def += f" COMMENT '{field['comment']}'"
                    field_defs.append(field_def)

                create_stmt += ",\n".join(field_defs)
                create_stmt += "\n)"

                # 添加表注释
                if table_info.get("table_comment"):
                    create_stmt += f" COMMENT '{table_info['table_comment']}'"
                create_stmt += ";"

                ddl.append(create_stmt)

            except Exception as e:
                import traceback

                error_traceback = traceback.format_exc()
                logger.error(f"Error traceback: {error_traceback}")
                logger.error(
                    f"Error rendering DDL for table {table_info.get('table_id', 'unknown')}: {str(e)}"
                )
                continue

        return "\n\n".join(ddl)

    def _prepare_for_generation(self, query: str, context: Dict) -> Dict:
        """
        Prepare for SQL generation by extracting key elements and performing table matching.

        Args:
            query: The natural language query
            context: The context dictionary containing bizid and other configuration

        Returns:
            Dict: A dictionary containing the prepared data for SQL generation
        """
        bizid = context["bizid"]
        config = context["nl2sql_config"]
        biz_prompt = self.biz_manager.list_prompts(bizid).get("prompts")
        logger.info(
            f"Preparing for SQL generation for query: {query} in business domain: {bizid}"
        )
        embedding_service = EmbeddingService(config=config)

        # 保留原query
        ori_query = query

        # 时间转换
        time_convert_prompt = Template(biz_prompt.get("time_convert_agent"))
        time_convert = TimeConvertAgent(time_convert_prompt)
        query_t = time_convert.generate(current_time=datetime.now(), user_input=query)

        logger.info(f"Time converted query: {query_t}")

        # 同义词拼接
        s = self._find_synonym(query=query_t, bizid=bizid)
        query_s = query + " ".join(s.keys())  # "xxxxx" -> "xxxxx p1 p2 p3"

        logger.info(f"Synonym mapping applied: {s}")

        ## 1. 要素抽取
        key_element_extract_prompt = Template(biz_prompt.get("element_extract_agent"))
        key_element_extract = KeyElementExtractAgent(key_element_extract_prompt)
        element = key_element_extract.generate(user_input=query_s)

        logger.info(f"Extracted key elements: {element}")

        # Check if a specific table_id is provided in the context
        alpha_knowledges = []
        recommended_tables = []
        if "table_id" in context and context["table_id"]:
            # Skip table recommendation and use the specified table
            final_table_ids = [context["table_id"]]
            logger.info(f"Using specified table_id: {context['table_id']}")
        else:
            # Continue with normal table recommendation process
            # embedding for knowledge A-label recall
            redundants = collapse(element.values())
            query_s_trim = query_s
            for r in redundants:
                if r in query_s_trim:
                    query_s_trim = query_s_trim.replace(r, "")

            logger.debug(f"Synonym query: {query_s_trim}")
            query_knowledge_embedding = embedding_service.get_embedding(query_s_trim)

            # embedding for table recommend
            all_relevant_dims = []
            # filter clause
            if "where" in element:
                # Extract dimension values from where conditions
                dim_values = self.biz_manager.search_dim_values(
                    bizid=bizid, query=element["where"]
                )
                if dim_values["status"] == "success":
                    for dim_value in dim_values["values"]:
                        all_relevant_dims.append(dim_value["field_id"])
                        # Assuming there's a method to map dimension values to tables
                        mapped_table = self.biz_manager.list_tableinfo(
                            bizid=bizid, table_id=dim_value["table_id"]
                        )
                        if mapped_table:
                            recommended_tables.append(mapped_table)

            # TODO: Add group and order
            query_s_concat = (
                query_s + "," + ",".join(all_relevant_dims)
                if all_relevant_dims
                else query_s
            )
            query_s_concat_embedding = embedding_service.get_embedding(query_s_concat)

            # 进行真正的表推荐
            min_score = float(context.get("table_retrieve_threshold", 0.7))
            recommended_tables = self.meta.match_tables_by_embedding(
                bizid=bizid,
                query_embedding=query_s_concat_embedding,
                top_k=5,
                min_score=min_score,
            )

            deep_semantic_search = context.get("deep_semantic_search", False)
            if deep_semantic_search:
                recommended_tables = self._deep_semantic_table_search(
                    ori_query=ori_query,
                    query_s_concat_embedding=query_s_concat_embedding,
                    context=context,
                    recommended_tables=recommended_tables,
                    embedding_service=embedding_service
                )

            logger.debug(f"recommended table: {recommended_tables}")
            
            recommended_table_ids = [t["table_id"] for t in recommended_tables]

            # 搜索业务知识alpha标签
            alpha_knowledges = self.meta.match_knowledge_by_embedding(
                bizid=bizid,
                query_embedding=query_knowledge_embedding,
                top_k=5,
                min_score=min_score,
            )

            logger.debug(f"alpha_knowledges: {alpha_knowledges}")

            # 剔除分值差距过大的表
            if alpha_knowledges:
                residual = 0.1
                alpha_knowledges.sort(key=lambda x: x["score"], reverse=True)
                most_similiar_score = alpha_knowledges[0].get("score")
                filter(
                    lambda x: most_similiar_score - x["score"] < residual,
                    alpha_knowledges,
                )

            # 根据表推荐的结果，对上述结果进行筛选
            final_table_ids = []
            if alpha_knowledges:
                # 1. alpha_knowledges有匹配到
                if len(set([k["table_id"] for k in alpha_knowledges])) == 1:
                    # 1.1 同表
                    final_table_ids.append(alpha_knowledges[0]["table_id"])
                else:
                    # 1.2 不同表
                    for k in alpha_knowledges:
                        if k["table_id"] in recommended_table_ids:
                            # 与表推荐的相吻合，那就采用此知识
                            final_table_ids.append(k["table_id"])
                            break
                    else:
                        final_table_ids.append(alpha_knowledges[0]["table_id"])
            elif not recommended_table_ids:
                # 表推荐也是空的，说明没有任何匹配
                # 直接中断返回
                return {"query": query, "sql": None}
            else:
                # alpha_knowledges没有匹配到, 则使用表推荐的表
                final_table_ids.extend(recommended_table_ids)

        # TODO: 对表进行权限校验
        if context.get("table_auth_enable") == 1:
            pass

        # 将问题进行维值匹配
        matched_dim_values = []
        if element.get("where"):
            result = self.biz_manager.search_dim_values(
                bizid=bizid, query=element["where"]
            )
            if result["status"] == "success":
                matched_dim_values = result["values"]

        # 匹配业务知识的B标签
        beta_knowledge = self.meta.match_knowledge_by_key_beta(
            bizid=bizid, query=query_s
        )

        # 使用最终选出来的表，对搜出来的维值和知识进行过滤
        filter(lambda x: x["table_id"] in final_table_ids, matched_dim_values)
        filter(lambda x: x["table_id"] in final_table_ids, beta_knowledge)

        logger.debug(f"final_table: {final_table_ids}")

        # 获取表信息
        table_info_list = []
        for table_id in final_table_ids:
            table_info = self.biz_manager.list_tableinfo(bizid=bizid, table_id=table_id)
            logger.debug(f"table_info: {table_info}")
            if table_info:
                table_info_list.extend(table_info["tables"])

        logger.debug(f"table_info_list: {table_info_list}")

        # Log all the information for debugging and analysis
        # logger.info(f"Query: {query}")
        # logger.info(f"Translated Query: {query_t}")
        # logger.info(f"Business ID: {bizid}")
        # logger.info(f"Final Table IDs: {final_table_ids}")
        # logger.info(f"Recommended Table IDs: {recommended_table_ids}")
        # logger.info(f"All Recommended Tables: {recommended_tables}")
        # logger.info(f"Alpha Knowledges: {alpha_knowledges}")
        # logger.info(f"Beta Knowledge: {beta_knowledge}")
        # logger.info(f"Matched Dimension Values: {matched_dim_values}")
        # logger.info(f"Table Info List: {table_info_list}")
        # logger.info(f"Synonyms: {s}")
        # logger.info(f"Context: {context}")
        # logger.info(f"Business Prompt: {biz_prompt}")

        return {
            "query": query,
            "query_t": query_t,
            "s": s,
            "bizid": bizid,
            "biz_prompt": biz_prompt,
            "alpha_knowledges": alpha_knowledges,
            "beta_knowledge": beta_knowledge,
            "table_info_list": table_info_list,
            "all_recommended_tables": recommended_tables,
            "matched_dim_values": matched_dim_values,
            "context": context,
        }
    
    
    def _field_recommend(self, qp_result_dict: Dict, context: Dict) -> Dict:
        """
        Perform field recommendation based on the query and context.

        Args:
            query: The natural language query
            context: The context dictionary containing bizid and other configuration

        Returns:
            List: A list of field recommendation
        """
        bizid = context["bizid"]

        # 遍历qp_result_dict，如果entity_type为field,则去filed倒排索引中查找匹配的字段；如果其它type，则用entity_name去表中查找匹配的表
        entity_list = []
        for entity in qp_result_dict["entity"]:
            if entity["entity_type"] == "field":
                # 去filed倒排索引中查找匹配的字段
                entity_list.append(entity["entity_text"])
            else:
                # 用entity_name去表中查找匹配的表
                entity_list.append(entity["entity_name"])

        match_fields_by_entity = self.meta.match_fields_by_entity(
            bizid=bizid,
            entity_list=entity_list
        )
        logger.debug(f"Match Fields By Entity: {match_fields_by_entity}")

        # TABLE RECOMMEND
        # 1. 首先获取每个实体匹配度合格的字段
        entity_best_fields = {}
        for entity_match in match_fields_by_entity:
            entity = entity_match["entity"]
            # 筛选出score > 0.7的字段
            high_score_matches = [match for match in entity_match["matches"] if match["score"] > 0.70]
            entity_best_fields[entity] = high_score_matches
        
        # 2. 分析表包含的实体数量
        table_entity_count = {}
        total_entities = len(entity_best_fields)  # 总实体数
        
        for entity, field_match in entity_best_fields.items():
            # 对每个实体，按表ID分组，只保留每个表中得分最高的匹配
            table_best_matches = {}
            for match in field_match:
                for table_id in match["table_id_list"]:
                    if table_id not in table_best_matches or match["score"] > table_best_matches[table_id]["score"]:
                        table_best_matches[table_id] = match
            
            # 使用每个表的最佳匹配来更新计数
            for table_id, best_match in table_best_matches.items():
                if table_id not in table_entity_count:
                    table_entity_count[table_id] = {
                        "count": 0,
                        "entities": set(),
                        "total_score": 0,
                        "is_complete_match": False
                    }
                table_entity_count[table_id]["count"] += 1
                table_entity_count[table_id]["entities"].add(entity)
                table_entity_count[table_id]["total_score"] += best_match["score"]
                # 判断是否完全匹配
                if table_entity_count[table_id]["count"] == total_entities:
                    table_entity_count[table_id]["is_complete_match"] = True

        # 3. 按包含的实体数量和总分排序
        table_score = []
        for table_id, stats in table_entity_count.items():
            table_score.append({
                "table_id": table_id,
                "entity_count": stats["count"],
                "entities": list(stats["entities"]),
                "total_score": stats["total_score"],
                "is_complete_match": stats["is_complete_match"],
                "match_ratio": stats["count"] / total_entities  # 添加匹配比例
            })
        
        # 按完全匹配、实体数量和总分排序
        table_score.sort(key=lambda x: (
            x["is_complete_match"],  # 首先按是否完全匹配排序
            x["match_ratio"],        # 然后按匹配比例排序
            x["total_score"]         # 最后按总分排序
        ), reverse=True)
        
        # 取前3个表
        table_score = table_score[:3]

        # 获取推荐表的schema信息
        recommended_tables = []
        for table_info in table_score:
            # 获取表信息
            table_detail = self.biz_manager.list_tableinfo(
                bizid=bizid, 
                table_id=table_info["table_id"]
            )
            if table_detail and table_detail["tables"]:
                table = table_detail["tables"][0]
                # 添加表名
                table_info["table_name"] = table["table_name"]
                # 添加comment
                table_info["table_comment"] = table["table_comment"]
                # 添加fields
                table_info["fields"] = table["fields"]
                recommended_tables.append(table_info)

        logger.debug(f"Recommended Tables with field: {recommended_tables}")
        
        return recommended_tables

    def _deep_semantic_table_search(self, ori_query: str, query_s_concat_embedding: List[float], context: Dict, recommended_tables: List[Dict], embedding_service: Any) -> List[Dict]:
        """
        Perform deep semantic table search using both original and transformed queries.

        Args:
            ori_query: The original natural language query
            query_s_concat_embedding: The embedding of the concatenated query
            context: The context dictionary containing configuration
            recommended_tables: The initial recommended tables
            embedding_service: The embedding service instance

        Returns:
            List[Dict]: The final recommended tables after deep semantic search
        """
        bizid = context["bizid"]
        min_score = float(context.get("table_retrieve_threshold", 0.7))

        # QUERY PARSE
        prompt = self.biz_manager.get_prompt(bizid, "query_parse_agent")
        query_parse_prompt = Template(prompt.get("prompt"))
 
        query_parse = QueryParseAgent(query_parse_prompt)
        qp_result = query_parse.generate(
            query=ori_query
        )
        logger.debug(f"Query Parse Result: {qp_result}")

        try:
            qp_result_dict = json.loads(qp_result)
        except Exception as e:
            logger.error(f"Query Parse Result Error: {str(e)} ")
            return []
        
        # If the query contains table name, use it to search tables
        table_name = qp_result_dict.get("table", "")
        if table_name:
            # Get embedding for table name
            table_name_embedding = embedding_service.get_embedding(table_name)
            recommended_tables = self.meta.match_tables_by_deep_semantic(
                bizid=bizid,
                query_embedding=table_name_embedding,
                top_k=5,
                min_score=min_score,
            )
            return recommended_tables

        # First deep semantic search on transformed query
        recommended_tables = self.meta.match_tables_by_deep_semantic(
            bizid=bizid,
            query_embedding=query_s_concat_embedding,
            top_k=5,
            min_score=min_score,
            recommended_tables=recommended_tables
        )

        # Get embedding for original query
        ori_query_embedding = embedding_service.get_embedding(ori_query)
        
        # Get initial recommendations for original query
        ori_recommended_tables = self.meta.match_tables_by_embedding(
            bizid=bizid,
            query_embedding=ori_query_embedding,
            top_k=5,
            min_score=min_score,
        )

        # Perform deep semantic search on original query
        ori_recommended_tables = self.meta.match_tables_by_deep_semantic(
            bizid=bizid,
            query_embedding=ori_query_embedding,
            top_k=5,
            min_score=min_score,
            recommended_tables=ori_recommended_tables
        )

        # Merge and sort tables, keeping highest score for each table
        table_scores = {}
        cur_max_score = 0.0
        # Process recommended_tables
        for table in recommended_tables:
            table_id = table["table_id"]
            if table_id not in table_scores or table["score"] > table_scores[table_id]["score"]:
                table_scores[table_id] = table
                if table["score"] > cur_max_score:
                    cur_max_score = table["score"]
        
        # Process ori_recommended_tables
        for table in ori_recommended_tables:
            table_id = table["table_id"]
            if table_id not in table_scores or table["score"] > table_scores[table_id]["score"]:
                table_scores[table_id] = table
                if table["score"] > cur_max_score:
                    cur_max_score = table["score"]
        
        # Convert back to list and sort by score
        recommended_tables = list(table_scores.values())
        recommended_tables.sort(key=lambda x: x["score"], reverse=True)

        logger.debug(f"Semantic Recommended Tables: {recommended_tables}")
        logger.debug(f"Semantic Recommended Tables Max Score: {cur_max_score}")

        # now we always use field recommendation
        field_recommended_tables = self._field_recommend(qp_result_dict=qp_result_dict, context=context)
        
        # Create score mapping for table name recall
        table_scores = {table["table_id"]: table["score"] for table in recommended_tables}
        
        # Create mapping for field recall tables
        field_tables_map = {table["table_id"]: table for table in field_recommended_tables}
        
        # Weight tables based on field recommendations
        for field_table in field_recommended_tables:
            table_id = field_table["table_id"]
            if table_id in table_scores:
                # If table exists in table name recall
                if field_table["is_complete_match"]:
                    # Complete match case, boost existing score
                    table_stat = field_tables_map[table_id]
                    field_recall_score = table_stat["total_score"] / table_stat["entity_count"]
                    table_scores[table_id] = (table_scores[table_id] * 0.4 + field_recall_score * 0.6) * 1.25
                    table_scores[table_id] = min(table_scores[table_id], 1.0)  # Cap score at 1.0
                else:
                    # Partial match case, weight based on match ratio
                    table_stat = field_tables_map[table_id]
                    field_recall_score = table_stat["total_score"] / table_stat["entity_count"]
                    table_scores[table_id] = (table_scores[table_id] * 0.5 + field_recall_score * 0.5)
            else:
                # If table not in table name recall, assign base score
                if field_table["is_complete_match"]:
                    table_scores[table_id] = 0.75
                else:
                    table_scores[table_id] = field_table["total_score"] / field_table["entity_count"] * field_table["match_ratio"]
                
                # Add field matched tables to recommended_tables
                if table_scores[table_id] < min_score:
                    continue

                recommended_tables.append({
                    "table_id": table_id,
                    "table_name": field_table["table_name"],
                    "table_comment": field_table["table_comment"],
                    "fields": field_table["fields"],
                    "score": table_scores[table_id],
                    "is_complete_match": field_table["is_complete_match"],
                    "match_ratio": field_table["match_ratio"],
                    "entities": field_table["entities"]
                })
        
        # Update scores and field recall info in recommended_tables
        for table in recommended_tables:
            table_id = table["table_id"]
            if table_id in table_scores:
                table["score"] = table_scores[table_id]
            
            # Add field recall info
            if table_id in field_tables_map:
                field_table = field_tables_map[table_id]
                table["match_ratio"] = field_table["match_ratio"]
                table["entities"] = field_table["entities"]
                table["is_complete_match"] = field_table["is_complete_match"]
            else:
                # For tables without intersection, set these fields to empty
                table["match_ratio"] = None
                table["entities"] = []
                table["is_complete_match"] = False
        
        # Sort by normalized scores
        recommended_tables.sort(key=lambda x: x["score"], reverse=True)
        
        return recommended_tables

    def _prepare_generation_params(self, prepared_data: Dict) -> Dict:
        """
        Extract and prepare parameters needed for SQL generation from prepared data.

        Args:
            prepared_data: The dictionary containing prepared data from _prepare_for_generation

        Returns:
            Dict: Parameters for SQL generation
        """
        query_t = prepared_data["query_t"]
        s = prepared_data["s"]
        biz_prompt = prepared_data["biz_prompt"]
        alpha_knowledges = prepared_data["alpha_knowledges"]
        beta_knowledge = prepared_data["beta_knowledge"]
        table_info_list = prepared_data["table_info_list"]
        matched_dim_values = prepared_data["matched_dim_values"]
        context = prepared_data["context"]

        # Render relevant variables
        # TODO:Support multi metric
        logger.info(f"beta: {beta_knowledge}")
        logger.info(f"alpha: {alpha_knowledges}")

        metric = alpha_knowledges[0]["value"] if alpha_knowledges else ""
        business_knowledge = beta_knowledge[0]["value"] if beta_knowledge else ""

        # Only send the first matched table to LLM
        if table_info_list:
            schema = self._render_schema_ddl(table_info_list[:1])
        else:
            schema = ""
            logger.warning("No table info found, using empty schema")

        fewshot = self._render_fewshot(context.get("fewshot"))
        synonym = self._render_synonym(s)
        field_value_info = self._render_field_value(matched_dim_values, table_info_list)

        return {
            "metric": metric,
            "business_knowledge": business_knowledge,
            "schema": schema,
            "fewshot": fewshot,
            "query": query_t,
            "field_value_info": field_value_info,
            "synonym": synonym,
            "biz_prompt": biz_prompt,
        }

    def generate(self, query: str, context: Dict) -> str:
        """
        Generate SQL from natural language query.

        Args:
            query: The natural language query
            context: The context dictionary containing bizid and other configuration

        Returns:
            str: The generated SQL query
        """
        prepared_data = self._prepare_for_generation(query, context)

        # Check if we have tables
        if not prepared_data.get("table_info_list"):
            return None, None

        # Get generation parameters using the shared method
        gen_params = self._prepare_generation_params(prepared_data)

        # NL2SQl生成
        from agents.nl2sql import Text2SQLAgent

        text2sql = Text2SQLAgent(Template(gen_params["biz_prompt"]["nl2sql_agent"]))

        # render required variable
        sql = text2sql.generate(
            metric=gen_params["metric"],
            business_knowledge=gen_params["business_knowledge"],
            schema=gen_params["schema"],
            fewshot=gen_params["fewshot"],
            query=gen_params["query"],
            field_value_info=gen_params["field_value_info"],
            synonym=gen_params["synonym"],
        )

        logger.info(f"{query}, {sql}")

        return query, sql

    async def stream_generate(self, query: str, context: Dict):
        """
        Stream SQL generation from natural language query.

        Args:
            query: The natural language query
            context: The context dictionary containing bizid and other configuration

        Returns:
            An async generator that streams the generated SQL
        """
        prepared_data = self._prepare_for_generation(query, context)

        # logger.debug(f"table_info_list: {prepared_data["table_info_list"]}")

        # Check if we have tables
        if not prepared_data.get("table_info_list"):
            yield None
            return

        # Get generation parameters using the shared method
        gen_params = self._prepare_generation_params(prepared_data)

        # Stream SQL generation
        from agents.nl2sql import Text2SQLAgent

        text2sql = Text2SQLAgent(Template(gen_params["biz_prompt"]["nl2sql_agent"]))

        # Use the streaming version to get clean SQL without code block markers
        async for sql_chunk in text2sql.generate_stream(
            metric=gen_params["metric"],
            business_knowledge=gen_params["business_knowledge"],
            schema=gen_params["schema"],
            fewshot=gen_params["fewshot"],
            query=gen_params["query"],
            field_value_info=gen_params["field_value_info"],
            synonym=gen_params["synonym"],
        ):
            # logger.info(f"Streaming SQL chunk: {sql_chunk}")
            yield sql_chunk

    def get_query_metadata(self, query: str, context: Dict) -> Dict:
        """
        Get metadata related to a query including matched tables and alpha knowledge keys.

        Args:
            query: The natural language query
            context: The context dictionary containing bizid and other configuration

        Returns:
            Dict: A dictionary containing matched tables and alpha knowledge keys
        """
        prepared_data = self._prepare_for_generation(query, context)

        # Extract table_info_list
        table_info_list = prepared_data.get("table_info_list", [])

        # Extract alpha keys from alpha_knowledges
        alpha_knowledges = prepared_data.get("alpha_knowledges", [])
        alpha_keys = [
            knowledge.get("key_alpha")
            for knowledge in alpha_knowledges
            if knowledge.get("key_alpha")
        ]

        return {
            "query": query,
            "table_info_list": table_info_list,
            "alpha_keys": alpha_keys,
        }

    def sql_explain(self, bizid: str, sql: str, table_info=[]) -> Dict:
        """
        Explain the SQL query.

        Args:
            bizid: The business id
            sql: The SQL query to explain
            table_info: The table information

        Returns:
            Dict: A dictionary containing the explanation of the SQL query
        """
        biz_prompt = self.biz_manager.list_prompts(bizid).get("prompts")

        from agents.nl2sql import SqlExplainAgent

        sql_explain = SqlExplainAgent(Template(biz_prompt.get("sql_explain_agent")))

        # render required variable
        explain = sql_explain.generate(sql=sql, table_info=table_info)

        return {
            "status": "success",
            "result": explain,
            "message": "SQL explained successfully",
        }

    def sql_comment(self, bizid: str, sql: str) -> Dict:
        """
        Add comments to the SQL query.

        Args:
            bizid: The business id
            sql: The SQL query to comment

        Returns:
            Dict: A dictionary containing the commented SQL query
        """
        biz_prompt = self.biz_manager.list_prompts(bizid).get("prompts")

        from agents.nl2sql import SqlCommentAgent

        sql_comment = SqlCommentAgent(Template(biz_prompt.get("sql_comment_agent")))

        # render required variable
        commented_sql = sql_comment.generate(sql=sql)

        return {
            "status": "success",
            "result": commented_sql,
            "message": "SQL commented successfully",
        }

    def sql_correct(self, bizid: str, sql: str) -> Dict:
        """
        Correct the SQL query.

        Args:
            bizid: The business id
            sql: The SQL query to correct

        Returns:
            Dict: A dictionary containing the corrected SQL query
        """
        biz_prompt = self.biz_manager.list_prompts(bizid).get("prompts")

        from agents.nl2sql import SqlCorrectAgent

        sql_correct = SqlCorrectAgent(Template(biz_prompt.get("sql_correct_agent")))

        # render required variable
        corrected_sql = sql_correct.generate(
            sql=sql,
        )

        return {
            "status": "success",
            "result": corrected_sql,
            "message": "SQL corrected successfully",
        }


if __name__ == "__main__":
    service = NL2SQLService()
    ret = service.generate("user input")
    print(ret)

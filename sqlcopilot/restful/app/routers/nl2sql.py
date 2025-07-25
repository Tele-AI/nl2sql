import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse

from loguru import logger

from .models import (
    BusinessCreateRequest,
    BusinessDeleteRequest,
    BusinessListRequest,
    BusinessResponse,
    BusinessListResponse,
    KnowledgeCreateOrUpdateRequest,
    KnowledgeDeleteRequest,
    KnowledgeListRequest,
    KnowledgeResponse,
    SQLCaseCreateOrUpdateRequest,
    SQLCaseDeleteRequest,
    SQLCaseListRequest,
    SQLCaseResponse,
    PromptUpdateRequest,
    PromptListRequest,
    PromptResponse,
    TableCreateOrUpdateRequest,
    TableDeleteRequest,
    TableListRequest,
    TableInfo,
    TableResponse,
    SettingsUpdateRequest,
    SettingsListRequest,
    SettingsResponse,
    SynonymCreateOrUpdateRequest,
    SynonymDeleteRequest,
    SynonymListRequest,
    SynonymResponse,
    GenerateRequest,
    GenerateResponse,
    FieldValueCreateOrUpdateRequest,
    FieldValueResponse,
    StatusEnum,
    Settings,
    Prompt,
    SQL,
    Synonym,
    DimValueCreateOrUpdateRequest,
    DimValueDeleteRequest,
    DimValueListRequest,
    DimValueResponse,
    DimValueSearchRequest,
    KnowledgeEmbeddingSearchRequest,
    KnowledgeEmbeddingSearchResponse,
    TableEmbeddingSearchRequest,
    TableEmbeddingSearchResponse,
    QueryMetadataRequest,
    QueryMetadataResponse,
    SQLExplainRequset,
    SQLExplainResponse,
    SQLCommentRequest,
    SQLCommentResponse,
    SQLCorrectRequset,
    SQLCorrectResponse,
)
from core.business import BusinessManager
from core.meta import MetaService
from core.nl2sql import NL2SQLService
from app.settings import config

router = APIRouter()
business_manager = BusinessManager()
meta_service = MetaService()
nl2sql = NL2SQLService()


# Business domain related endpoints
@router.post(
    "/nl2sql/business/create",
    response_model=BusinessResponse,
    summary="业务域提供基本租户隔离，所有调用方需要新建业务域才可进行调用",
)
async def create_business(request: BusinessCreateRequest):
    """Create a new business domain for tenant isolation."""
    result = business_manager.create_business(request.bizid)
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/business/delete",
    response_model=BusinessResponse,
    summary="删除业务域。",
)
async def delete_business(request: BusinessDeleteRequest):
    """Delete an existing business domain."""
    result = business_manager.delete_business(request.bizid)
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/business/list",
    response_model=BusinessListResponse,
    summary="列出所有业务域。",
)
async def list_businesses(_: BusinessListRequest = None):
    """List all business domains."""
    result = business_manager.list_businesses()
    return BusinessListResponse(
        status=StatusEnum.success,
        data=result.get("data", []),
        message=result.get("message"),
    )


# Knowledge related endpoints
@router.post(
    "/nl2sql/knowledge/create_or_update",
    response_model=KnowledgeResponse,
    summary="该接口可批量增加/修改业务知识。在创建业务知识之前，需要保证业务域和业务知识所关联的表已经创建。"
    "每个知识条目的A标签和B标签至少有一个包含值。"
    "由于创建/更新业务知识过程耗时较长，建议设置稍微大一点的超时时间。建议15s以上。",
)
async def create_or_update_knowledge(request: KnowledgeCreateOrUpdateRequest):
    """Batch create or update business knowledge."""

    # 验证每个知识条目中的alpha和beta标签至少有一个包含值
    for knowledge in request.knowledges:
        if not knowledge.key_alpha and not knowledge.key_beta:
            return KnowledgeResponse(
                status=StatusEnum.failed,
                message="每个知识条目必须在key_alpha或key_beta中至少包含一个值",
            )

    result = business_manager.create_or_update_knowledge(
        request.bizid, [knowledge.model_dump() for knowledge in request.knowledges]
    )

    return KnowledgeResponse(
        status=StatusEnum(result["status"]),
        data=result.get("data", []),
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/knowledge/delete",
    response_model=BusinessResponse,
    summary="批量删除业务知识。",
)
async def delete_knowledge(request: KnowledgeDeleteRequest):
    """Delete multiple business knowledge entries within a business domain."""
    result = business_manager.delete_knowledge(request.bizid, request.knowledge_ids)
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/knowledge/list",
    response_model=KnowledgeResponse,
    summary="查询某业务域，某表下的所有的业务知识",
)
async def list_knowledge(request: KnowledgeListRequest):
    """List all business knowledge under a specific domain and table."""
    result = business_manager.list_knowledge(request.bizid, request.table_id)
    return KnowledgeResponse(
        status=StatusEnum(result["status"]),
        data=result.get("data", []),
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/knowledge/search_by_embedding",
    response_model=KnowledgeEmbeddingSearchResponse,
    summary="根据语义向量匹配最相似的知识条目",
)
async def search_knowledge_by_embedding(request: KnowledgeEmbeddingSearchRequest):
    """
    根据语义向量匹配最相似的知识条目

    - **bizid**: 业务域ID
    - **query_embedding**: 查询文本的向量表示，维度应与索引中的向量维度一致
    - **top_k**: 返回的最大结果数量，默认为5
    - **min_score**: 最小相似度阈值，低于此值的结果将被过滤，默认为0.7
    """
    # 检查业务域是否存在
    if not business_manager.business_exists(request.bizid):
        return KnowledgeEmbeddingSearchResponse(
            status=StatusEnum.error,
            message=f"Business domain with ID {request.bizid} does not exist",
            data=[],
        )

    # 调用MetaService的方法进行向量搜索
    results = meta_service.match_knowledge_by_embedding(
        bizid=request.bizid,
        query_embedding=request.query_embedding,
        top_k=request.top_k,
        min_score=request.min_score,
    )

    return KnowledgeEmbeddingSearchResponse(status=StatusEnum.success, data=results)


# SQL Cases related endpoints
@router.post(
    "/nl2sql/sqlcases/create_or_update",
    response_model=SQLCaseResponse,
    summary="新增/更新SQL语句案例库。支持批量更新。",
)
async def create_or_update_sqlcases(request: SQLCaseCreateOrUpdateRequest):
    """Batch create or update SQL cases."""
    result = business_manager.create_or_update_sqlcases(
        request.bizid, [sqlcase.model_dump() for sqlcase in request.sqlcases]
    )
    return SQLCaseResponse(
        status=StatusEnum(result["status"]),
        sqlcases=result.get("sqlcases", []),
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/sqlcases/delete",
    response_model=BusinessResponse,
    summary="删除某条SQL案例",
)
async def delete_sqlcase(request: SQLCaseDeleteRequest):
    """Delete a specific SQL case."""
    result = business_manager.delete_sqlcase(request.bizid, request.case_id)
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/sqlcases/list",
    response_model=SQLCaseResponse,
    summary="查询该业务下的所有案例库。",
)
async def list_sqlcases(request: SQLCaseListRequest):
    """List all SQL cases under a specific business domain."""
    result = business_manager.list_sqlcases(request.bizid)
    return SQLCaseResponse(
        status=StatusEnum(result["status"]),
        sqlcases=result.get("sqlcases", []),
        message=result.get("message"),
    )


# Prompt related endpoints
@router.post(
    "/nl2sql/prompt/update",
    response_model=PromptResponse,
    summary="NL2SQL相关所有的Prompt设置。业务域新创之后，会使用默认prompt模版配置。",
)
async def update_prompt(request: PromptUpdateRequest):
    """Update prompts for a business domain."""
    result = business_manager.update_prompts(
        request.bizid, request.prompts.model_dump(exclude_unset=True)
    )
    return PromptResponse(
        status=StatusEnum(result["status"]),
        prompts=request.prompts,
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/prompt/list",
    response_model=PromptResponse,
    summary="查询某业务域的所有prompt配置。",
)
async def list_prompts(request: PromptListRequest):
    """List prompts for a business domain."""
    result = business_manager.list_prompts(request.bizid)
    return PromptResponse(
        status=StatusEnum(result["status"]),
        prompts=Prompt(**result.get("prompts", {})),
        message=result.get("message"),
    )


# Table Info related endpoints
@router.post(
    "/nl2sql/tableinfo/create_or_update",
    response_model=TableResponse,
    summary="在某业务域下批量新建/更新数据表信息，每次最多10个表。",
)
async def create_or_update_tableinfo(request: TableCreateOrUpdateRequest):
    """Create or update multiple table information under a business domain.

    Supports batch operations with a maximum of 10 tables per request.
    """
    tables_result = []
    overall_status = StatusEnum.success
    error_messages = []

    logger.debug(f"create_update_table: {request}")

    # Process each table in the batch
    for table in request.tables:
        result = business_manager.create_or_update_tableinfo(
            request.bizid, table.model_dump()
        )

        if result["status"] == "error":
            # 直接返回错误，不继续执行后面的逻辑
            return TableResponse(
                status=StatusEnum.error,
                tables=[],
                message=f"Table {table.table_id}: {result.get('message', 'Unknown error')}"
            )

        if "tables" in result:
            tables_result.extend(result.get("tables", []))

    # 更新field_inverted
    result = business_manager.create_or_update_field_inverted(
        request.bizid, [table.model_dump() for table in request.tables]
    )
    if result["status"] == "error":
        # 直接返回错误，不继续执行后面的逻辑
        return TableResponse(
            status=StatusEnum.error,
            tables=[],
            message=f"Field inverted: {result.get('message', 'Unknown error')}"
        )

    # 如果所有操作都成功，返回成功响应
    return TableResponse(
        status=StatusEnum.success,
        tables=tables_result,
        message=None,
    )


@router.post(
    "/nl2sql/tableinfo/delete",
    response_model=BusinessResponse,
    summary="删除某张表或多张表的所有信息，同时删除相关的业务知识和维度值。",
)
async def delete_tableinfo(request: TableDeleteRequest):
    """Delete one or more tables along with related knowledge and dimension values.

    Accepts a list of table IDs to delete (can be a single item for deleting just one table).
    All related knowledge entries and dimension values will be automatically deleted.
    """
    result = business_manager.delete_tableinfo_batch(request.bizid, request.table_ids)
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/tableinfo/list",
    response_model=TableResponse,
    summary="查询某业务域下的所有表信息。",
)
async def list_tableinfo(request: TableListRequest):
    """List all table information under a specific business domain."""
    logger.info(
        f"Listing table info for bizid: {request.bizid}, table_id: {request.table_id}"
    )
    result = business_manager.list_tableinfo(request.bizid, request.table_id)
    return TableResponse(
        status=StatusEnum(result["status"]),
        tables=result.get("tables", []),
        message=result.get("message"),
    )


# @router.post(
#     "/nl2sql/tableinfo/create_or_update_field_value",
#     response_model=FieldValueResponse,
#     summary="为某表的某个字段增加维值信息。",
# )
# async def create_or_update_field_value(request: FieldValueCreateOrUpdateRequest):
#     """Create or update field value information under a specific table."""
#     # Convert the list of values to a comma-separated string
#     values_str = ",".join(request.values) if request.values else ""

#     result = business_manager.create_or_update_field_value(
#         request.bizid, request.table_id, request.field_id, values_str
#     )
#     return FieldValueResponse(
#         status=StatusEnum(result["status"]), message=result.get("message")
#     )


@router.post(
    "/nl2sql/tableinfo/search_by_embedding",
    response_model=TableEmbeddingSearchResponse,
    summary="根据语义向量匹配最相似的表",
)
async def search_tableinfo_by_embedding(request: TableEmbeddingSearchRequest):
    """
    根据语义向量匹配最相似的表

    基于提供的向量，在ES中搜索语义相似的表信息

    - **bizid**: 业务域ID
    - **query_embedding**: 查询文本的向量表示，维度应与索引中的向量维度一致
    - **top_k**: 返回的最大结果数量（默认为5）
    - **min_score**: 最小相似度阈值（默认为0.7）
    """
    try:
        results = meta_service.match_tables_by_embedding(
            bizid=request.bizid,
            query_embedding=request.query_embedding,
            top_k=request.top_k,
            min_score=request.min_score,
        )

        return TableEmbeddingSearchResponse(
            status=StatusEnum.success,
            tables=results,
        )
    except Exception as e:
        return TableEmbeddingSearchResponse(
            status=StatusEnum.error,
            message=str(e),
            tables=[],
        )


# Settings related endpoints
@router.post(
    "/nl2sql/settings/update",
    response_model=SettingsResponse,
    summary="nl2sql流程相关参数设置。",
)
async def update_settings(request: SettingsUpdateRequest):
    """Update settings for a business domain."""
    result = business_manager.update_settings(
        request.bizid, request.settings.model_dump(exclude_unset=True)
    )
    return SettingsResponse(
        status=StatusEnum(result["status"]),
        data=request.settings,
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/settings/list",
    response_model=SettingsResponse,
    summary="查询某业务域的所有设置。",
)
async def list_settings(request: SettingsListRequest):
    """List settings for a business domain."""
    result = business_manager.list_settings(request.bizid)
    return SettingsResponse(
        status=StatusEnum(result["status"]),
        data=Settings(**result.get("data", {})),
        message=result.get("message"),
    )


# Synonym related endpoints
@router.post(
    "/nl2sql/synonym/create_or_update",
    response_model=SynonymResponse,
    summary="新增一个同义词信息。当输入中有匹配到副义词，会自动把主义词拼接到问题之中。",
)
async def create_or_update_synonym(request: SynonymCreateOrUpdateRequest):
    """Create or update synonyms for a business domain."""
    result = business_manager.create_or_update_synonyms(
        request.bizid, [synonym.model_dump() for synonym in request.synonyms]
    )
    return SynonymResponse(
        status=StatusEnum(result["status"]),
        synonyms=request.synonyms,
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/synonym/delete",
    response_model=BusinessResponse,
    summary="删除一个同义词信息",
)
async def delete_synonym(request: SynonymDeleteRequest):
    """Delete a synonym for a business domain."""
    logger.debug(f"delete synonym request: {request}")
    result = business_manager.delete_synonym(request.bizid, request.primary)
    logger.debug(f"delete synonym result: {result}")
    return BusinessResponse(
        status=StatusEnum(result["status"]), message=result.get("message")
    )


@router.post(
    "/nl2sql/synonym/list", response_model=SynonymResponse, summary="查询某同义词信息"
)
async def list_synonyms(request: SynonymListRequest):
    """List synonyms for a business domain."""
    result = business_manager.list_synonyms(request.bizid, request.primary)
    return SynonymResponse(
        status=StatusEnum(result["status"]),
        synonyms=[Synonym(**s) for s in result.get("synonyms", [])],
        message=result.get("message"),
    )


# Generate related endpoints
@router.post(
    "/nl2sql/generate",
    response_model=GenerateResponse,
    summary="输入自然语言，生成对应SQL。可采用SSE方式流式返回。",
)
async def generate_sql(request: GenerateRequest):
    """Generate SQL from natural language input."""
    context = {
        "nl2sql_config": config,
        "bizid": request.bizid,
    }

    # 提前检查业务域是否存在
    if not business_manager.business_exists(request.bizid):
        return QueryMetadataResponse(
            status=StatusEnum.error,
            message=f"Business domain with ID {request.bizid} does not exist",
            tables=[],
            alpha_keys=[],
        )

    # Add table_id to context if provided
    if request.table_id:
        context["table_id"] = request.table_id

    if (
        hasattr(request, "settings")
        and getattr(request.settings, "table_retrieve_threshold", None) is not None
    ):
        context["table_retrieve_threshold"] = request.settings.table_retrieve_threshold

    if (
        hasattr(request, "settings")
        and getattr(request.settings, "deep_semantic_search", None) is not None
    ):
        context["deep_semantic_search"] = (
            request.settings.deep_semantic_search
        )

    if request.stream:
        try:

            async def stream_sql():
                async for sql_chunk in nl2sql.stream_generate(
                    query=request.query, context=context
                ):
                    if sql_chunk is None:
                        # No tables matched, return error
                        yield "data: ERROR: 没有匹配到任何相似的表或者指标"
                        return
                    yield f"data: {sql_chunk}"

            # return StreamingResponse(stream_sql(), media_type="text/event-stream")
            return EventSourceResponse(stream_sql(), media_type="text/event-stream")
        except Exception as e:
            logger.error(f"Error in stream setup: {str(e)}")
            return GenerateResponse(
                status=StatusEnum.error,
                sqls=[],
                message=f"Error during streaming setup: {str(e)}",
            )
    else:
        nl_text, sql_text = nl2sql.generate(query=request.query, context=context)

        if not sql_text:
            # 表推荐没有匹配，直接返回
            return GenerateResponse(
                status=StatusEnum.error,
                sqls=[],
                message="没有匹配到任何相似的表或者指标",
            )

        # Return the generated SQL response
        return GenerateResponse(
            status=StatusEnum.success,
            sqls=[
                SQL(
                    sql_text=sql_text,
                    nl_text=nl_text,
                )
            ],
        )


# Dimension Values related endpoints
@router.post(
    "/nl2sql/dim_values/create_or_update",
    response_model=DimValueResponse,
    summary="批量创建或更新维度值信息，提供更灵活的值存储和查询方式。",
)
async def create_or_update_dim_values(request: DimValueCreateOrUpdateRequest):
    """
    Create or update dimension values for a field.

    This endpoint allows storing dimension values with fuzzy search capabilities.

    - **bizid**: Business domain ID
    - **table_id**: Table ID
    - **field_id**: Field ID
    - **values**: List of dimension values
    """
    values_list = [value.model_dump() for value in request.values]
    result = business_manager.create_or_update_dim_value(
        request.bizid, request.table_id, request.field_id, values_list
    )

    return DimValueResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/dim_values/delete",
    response_model=BusinessResponse,
    summary="删除维度值信息，可以删除特定值或删除某字段的所有值。",
)
async def delete_dim_value(request: DimValueDeleteRequest):
    """
    Delete dimension values for a field.

    If a specific value is provided, only that value is deleted.
    Otherwise, all values for the specified field are deleted.

    - **bizid**: Business domain ID
    - **table_id**: Table ID
    - **field_id**: Field ID
    - **value**: Optional specific value to delete
    """
    result = business_manager.delete_dim_value(
        request.bizid, request.table_id, request.field_id, request.value
    )

    return BusinessResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
    )


@router.post(
    "/nl2sql/dim_values/list",
    response_model=DimValueResponse,
    summary="列出维度值信息，可以按业务域、表和字段筛选。",
)
async def list_dim_values(request: DimValueListRequest):
    """
    List dimension values for a business domain.

    Results can be filtered by table ID and/or field ID.

    - **bizid**: Business domain ID
    - **table_id**: Optional table ID to filter by
    - **field_id**: Optional field ID to filter by
    """
    result = business_manager.list_dim_values(
        request.bizid, request.table_id, request.field_id
    )

    return DimValueResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
        values=result.get("values", []),
    )


@router.post(
    "/nl2sql/dim_values/search",
    response_model=DimValueResponse,
    summary="通过模糊匹配搜索维度值，支持对值进行模糊搜索。",
)
async def search_dim_values(request: DimValueSearchRequest):
    """
    Search dimension values using fuzzy matching.

    This endpoint performs fuzzy matching on the value field,
    returning results sorted by relevance score.

    - **bizid**: Business domain ID
    - **query**: Search query text
    - **table_id**: Optional table ID to filter by
    - **field_id**: Optional field ID to filter by
    """
    result = business_manager.search_dim_values(
        request.bizid, request.query, request.table_id, request.field_id
    )

    return DimValueResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
        values=result.get("values", []),
    )


@router.post(
    "/nl2sql/query_metadata",
    response_model=QueryMetadataResponse,
    summary="获取查询相关的元数据信息，包括匹配的表和alpha知识关键词。",
)
async def get_query_metadata(request: QueryMetadataRequest):
    """
    获取查询相关的元数据信息

    根据自然语言查询，返回匹配的表信息和alpha知识关键词

    - **bizid**: 业务域ID
    - **query**: 查询文本
    """
    try:
        logger.debug(f"get_query_metadata request: {request}")

        context = {
            "nl2sql_config": config,
            "bizid": request.bizid,
        }

        if (hasattr(request, "settings")):
            if getattr(request.settings, "table_retrieve_threshold", None) is not None:
                context["table_retrieve_threshold"] = (
                    request.settings.table_retrieve_threshold
                )
            if getattr(request.settings, "deep_semantic_search", None) is not None:
                context["deep_semantic_search"] = (
                    request.settings.deep_semantic_search
                )

        # 提前检查业务域是否存在
        if not business_manager.business_exists(request.bizid):
            return QueryMetadataResponse(
                status=StatusEnum.error,
                message=f"Business domain with ID {request.bizid} does not exist",
                tables=[],
                alpha_keys=[],
            )

        metadata = nl2sql.get_query_metadata(query=request.query, context=context)

        table_info = [
            TableInfo(table_id=x["table_id"], table_name=x["table_name"])
            for x in metadata.get("table_info_list", [])
        ]

        return QueryMetadataResponse(
            status=StatusEnum.success,
            tables=table_info,
            alpha_keys=metadata.get("alpha_keys", []),
        )

    except Exception as e:
        logger.error(
            f"Error in query metadata: {str(e)} Full trackback: {traceback.format_exc()}"
        )
        return QueryMetadataResponse(
            status=StatusEnum.error,
            message=f"Error retrieving query metadata: {str(e)}",
            tables=[],
            alpha_keys=[],
        )


@router.post(
    "/nl2sql/sql_explain",
    response_model=SQLExplainResponse,
    summary="解析SQL语句。",
)
async def sql_explain(request: SQLExplainRequset):
    """
    解析SQL语句。

    - **bizid**: 业务域ID
    - **sql**: SQL语句
    - **table_info**: 表信息
    """
    result = nl2sql.sql_explain(request.bizid, request.sql, request.table_info)

    return SQLExplainResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
        result=result.get("result", ""),
    )


@router.post(
    "/nl2sql/sql_comment",
    response_model=SQLCommentResponse,
    summary="为SQL语句添加注释。",
)
async def sql_comment(request: SQLCommentRequest):
    """
    为SQL语句添加注释。

    - **bizid**: 业务域ID
    - **sql**: SQL语句
    """
    result = nl2sql.sql_comment(request.bizid, request.sql)

    return SQLCommentResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
        result=result.get("result", ""),
    )


@router.post(
    "/nl2sql/sql_correct",
    response_model=SQLCorrectResponse,
    summary="纠正SQL语句。",
)
async def sql_correct(request: SQLCorrectRequset):
    """
    纠正SQL语句。

    - **bizid**: 业务域ID
    - **sql**: SQL语句
    """
    result = nl2sql.sql_correct(
        request.bizid,
        request.sql,
    )

    return SQLCorrectResponse(
        status=StatusEnum(result["status"]),
        message=result.get("message"),
        result=result.get("result", ""),
    )

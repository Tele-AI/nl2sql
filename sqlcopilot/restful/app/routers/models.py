from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from enum import Enum


# Enum for status
class StatusEnum(str, Enum):
    success = "success"
    error = "error"


# Pydantic models for request and response
class BusinessCreateRequest(BaseModel):
    bizid: str = Field(
        ..., description="新增的业务域id，客户端应使用合适的UUID算法来生成"
    )


class BusinessDeleteRequest(BaseModel):
    bizid: str = Field(..., description="要删除的业务域id")


class BusinessListRequest(BaseModel):
    pass  # No parameters needed for listing all businesses


class BusinessResponse(BaseModel):
    status: StatusEnum = Field(..., description="success创建成功, error创建失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")


class BusinessListResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    data: List[Dict[str, Any]] = Field([], description="业务域列表")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Knowledge related models
class Knowledge(BaseModel):
    knowledge_id: str = Field(
        ...,
        description="业务知识id，客户端应使用合适的UUID算法来生成。需保证该业务域下唯一",
    )
    table_id: str = Field(..., description="该条业务知识所属表的id")
    key_alpha: Optional[str] = Field(
        None, description="业务知识的A标签，用于表召回环节的标签"
    )
    key_beta: Optional[List[str]] = Field(
        None, description="业务知识的B标签，用于业务知识的字符匹配召回"
    )
    value: str = Field(..., description="业务知识")


class KnowledgeCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="该条业务知识所属业务域id")
    knowledges: List[Knowledge] = Field(..., description="新增的业务知识")


class KnowledgeDeleteRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    knowledge_ids: List[str] = Field(..., description="要删除的业务知识id列表")


class KnowledgeListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    table_id: Optional[str] = Field(
        None, description="可选的表id，用于筛选特定表下的知识"
    )


class KnowledgeResponse(BaseModel):
    status: StatusEnum = Field(
        ..., description="success接口调用成功, error接口调用失败"
    )
    data: List[dict] = Field(..., description="每一条业务知识的操作情况")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# SQL Cases related models
class SQLCase(BaseModel):
    case_id: str = Field(
        ...,
        description="案例id，客户端应使用合适的UUID算法来生成。需保证该业务域下唯一。",
    )
    querys: List[str] = Field(
        ..., description="该条SQL案例的自然语言，可以是多条。任意一条匹配都会响应。"
    )
    sql: str = Field(..., description="该条SQL案例的SQL语句。")


class SQLCaseCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="需新增案例库的业务域id")
    sqlcases: List[SQLCase] = Field(..., description="SQL语句案例")


class SQLCaseDeleteRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    case_id: str = Field(..., description="要删除的案例id")


class SQLCaseListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")


class SQLCaseResponse(BaseModel):
    status: StatusEnum = Field(..., description="success创建成功, error创建失败")
    sqlcases: List[dict] = Field(..., description="查询结果数据")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Prompt related models
class Prompt(BaseModel):
    time_convert_agent: Optional[str] = Field(None, description="时间转换agent prompt")
    nl2sql_agent: Optional[str] = Field(None, description="NL2SQL prompt")
    element_extract_agent: Optional[str] = Field(None, description="要素抽取 prompt")


class PromptUpdateRequest(BaseModel):
    bizid: str = Field(..., description="操作的业务域id")
    prompts: Prompt = Field(..., description="需修改的prompt")


class PromptListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")


class PromptResponse(BaseModel):
    status: StatusEnum = Field(..., description="success更新成功, error更新失败")
    prompts: Prompt = Field(..., description="prompts")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Table Info related models
class Fields(BaseModel):
    field_id: str = Field(..., description="字段id, 客户端应使用合适的UUID算法来生成")
    name: str = Field(..., description="字段名")
    datatype: str = Field(
        ..., description="字段类型。字段类型所属方言，应该与text2sql prompt相匹配。"
    )
    comment: str = Field(..., description="字段描述")


class Table(BaseModel):
    table_id: str = Field(
        ..., description="新增的表id，客户端应使用合适的UUID算法来生成"
    )
    table_name: str = Field(..., description="表名")
    table_comment: str = Field(..., description="表的描述")
    fields: List[Fields] = Field(..., description="表的字段")


class TableCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="关联的业务域")
    tables: List[Table] = Field(
        ..., description="批量创建或更新的表列表，最多支持10个表"
    )

    def model_post_init(self, __context):
        """Validate the request."""
        # Ensure tables don't exceed the limit
        if len(self.tables) > 10:
            raise ValueError("Maximum of 10 tables allowed per request")
        # Ensure tables list is not empty
        if len(self.tables) == 0:
            raise ValueError("At least one table must be provided")


class TableDeleteRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    table_ids: List[str] = Field(..., description="要删除的表id列表，支持单个或多个")


class TableListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    table_id: Optional[str] = Field(None, description="可选的表id，用于查询特定表")


class TableResponse(BaseModel):
    status: StatusEnum = Field(..., description="success创建成功, error创建失败")
    tables: List[Table] = Field(..., description="查询的表信息")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Settings related models
class Settings(BaseModel):
    table_retrieve_threshold: Optional[str] = Field(
        None, description="表召回阈值。（0 - 1）之间。"
    )
    enable_table_auth: Optional[bool] = Field(None, description="是否开启表权限校验")
    deep_semantic_search: Optional[bool] = Field(False, description="是否开启深度语义搜索")


class SettingsUpdateRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    settings: Settings = Field(..., description="生成流程相关参数设置")


class SettingsListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")


class SettingsResponse(BaseModel):
    status: StatusEnum = Field(..., description="success更新成功, error更新失败")
    data: Settings = Field(..., description="查询结果数据")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Synonym related models
class Synonym(BaseModel):
    primary: str = Field(..., description="主义词。")
    secondary: List[str] = Field(..., description="副义词。允许多个。")


class SynonymCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    synonyms: List[Synonym] = Field(..., description="同义词信息")


class SynonymDeleteRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    primary: str = Field(..., description="主义词")


class SynonymListRequest(BaseModel):
    bizid: str = Field(..., description="业务域id")
    primary: Optional[str] = Field(
        None, description="可选的主义词，用于查询特定同义词组"
    )


class SynonymResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    synonyms: List[Synonym] = Field(..., description="查询结果数据")
    message: Optional[str] = Field(None, description="失败时的错误信息")


# Generate related models
class GenerateRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    query: str = Field(..., description="自然语言输入")
    summary: Optional[str] = Field(None, description="查询摘要")
    settings: Optional[Settings] = Field(
        None, description="可以在单次输入中，指定所使用的相关超参数设置。"
    )
    stream: bool = Field(..., description="是否使用SSE流式返回")
    table_id: Optional[str] = Field(
        None, description="可选的表ID，如果提供则直接使用此表，不进行表推荐"
    )


class SQL(BaseModel):
    sql_text: str = Field(..., description="生成的sql代码")
    nl_text: str = Field(..., description="输入nl2sql模型的最终意图")


class GenerateResponse(BaseModel):
    status: StatusEnum = Field(..., description="success发起成功, error发起失败")
    sqls: List[SQL] = Field(..., description="生成的sql")
    message: Optional[str] = Field(None, description="失败时的报错信息")


class FieldValueCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    table_id: str = Field(..., description="表id")
    field_id: str = Field(..., description="字段id")
    values: List[str] = Field(..., description="字段值")


class FieldValueResponse(BaseModel):
    status: StatusEnum = Field(..., description="success创建成功, error创建失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")


class DimValue(BaseModel):
    value: str = Field(..., description="维度值")


class DimValueCreateOrUpdateRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    table_id: str = Field(..., description="表id")
    field_id: str = Field(..., description="字段id")
    values: List[DimValue] = Field(..., description="维度值列表")


class DimValueDeleteRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    table_id: str = Field(..., description="表id")
    field_id: str = Field(..., description="字段id")
    value: Optional[str] = Field(
        None, description="如果不提供，则删除该字段的所有维度值"
    )


class DimValueListRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    table_id: Optional[str] = Field(None, description="表id")
    field_id: Optional[str] = Field(None, description="字段id")


class DimValueSearchRequest(BaseModel):
    bizid: str = Field(..., description="业务id")
    query: str = Field(..., description="查询文本")
    table_id: Optional[str] = Field(None, description="表id")
    field_id: Optional[str] = Field(None, description="字段id")


class DimValueResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    values: Optional[List[Dict[str, Any]]] = Field(None, description="维度值列表")


class KnowledgeEmbeddingSearchRequest(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    query_embedding: List[float] = Field(..., description="查询文本的向量表示")
    top_k: int = Field(5, description="返回的最大结果数量")
    min_score: float = Field(0.7, description="最小相似度阈值")


class KnowledgeEmbeddingSearchResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="匹配结果")


class TableEmbeddingSearchRequest(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    query_embedding: List[float] = Field(..., description="查询文本的向量表示")
    top_k: int = Field(5, description="返回的最大结果数量")
    min_score: float = Field(0.7, description="最小相似度阈值")


class TableEmbeddingSearchResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    tables: List[Dict[str, Any]] = Field([], description="匹配到的表信息列表")


class GenerateMetaRequest(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    query: str = Field(..., description="查询文本")
    top_k: int = Field(5, description="返回的最大结果数量")


class GenerateMetaResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    data: Optional[Dict[str, Any]] = Field(None, description="匹配结果数据")


class TableInfo(BaseModel):
    table_id: str = Field(..., description="表ID")
    table_name: str = Field(..., description="表名称")


class QueryMetadataRequest(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    query: str = Field(..., description="查询文本")
    summary: Optional[str] = Field(None, description="查询摘要")
    settings: Optional[Settings] = Field(
        None, description="可以在单次输入中，指定所使用的相关超参数设置。"
    )

class QueryMetadataResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    tables: List[TableInfo] = Field([], description="匹配到的表信息列表")
    alpha_keys: List[str] = Field([], description="匹配到的alpha知识关键词列表")


class SQLExplainRequset(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    sql: str = Field(..., description="SQL语句")
    table_info: Optional[List] = Field([], description="表信息")


class SQLExplainResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    result: Optional[str] = Field(None, description="解析结果")


class SQLCommentRequest(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    sql: str = Field(..., description="SQL语句")


class SQLCommentResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    result: Optional[str] = Field(None, description="解析结果")


class SQLCorrectRequset(BaseModel):
    bizid: str = Field(..., description="业务域ID")
    sql: str = Field(..., description="SQL语句")


class SQLCorrectResponse(BaseModel):
    status: StatusEnum = Field(..., description="success成功, error失败")
    message: Optional[str] = Field(None, description="失败时的错误信息")
    result: Optional[str] = Field(None, description="解析结果")

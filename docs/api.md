# NL2SQL API接口文档

## 修正记录

2025年3月6日初版

2025年7月23日 更新 - 补充缺失字段和修正字段可选性

## 1. 主要接口

business: 业务域相关接口。新增/更新/、删除、查询

knowledge: 业务知识相关接口。新增/更新，删除，查询

sqlcases: SQL案例库相关接口。新增/更新，删除，查询

prompt: 机器人模版配置接口。新增/更新，删除，查询

tableinfo: 库表信息相关接口。新增/更新，删除，查询 （包含字段维值的管理）

settings: 其他设置相关接口。更新，查询

synonym: 同义词配置相关接口。新增/更新，查询，删除

generate: 生成接口。

## 2. 具体设计

该服务由于会被多个业务产品集成，所以尽量保持了业务中立。

集成方在实现客户端的同时，需考虑对象字段向后兼容，以应对服务端API后续的功能扩充。

## 2.1 业务域相关接口

### 2.1.1 新增

**描述**

业务域提供基本租户隔离，所有调用方需要新建业务域才可进行调用

**Url**

`/nl2sql/business/create`

**Method**

`POST`

**Request**

| 字段  | 类型   | 是否必须 | 说明                                             |
| ----- | ------ | -------- | ------------------------------------------------ |
| bizid | string | Y        | 新增的业务域id，客户端应使用合适的UUID算法来生成 |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success创建成功, error创建失败 |
| message | string | N        | 失败时的错误信息               |

### 2.1.2 删除

**描述**

删除业务域。

**Url**
`/nl2sql/business/delete`
**Method**

`POST`
**Request**

| 字段  | 类型   | 是否必须 | 说明                                             |
| ----- | ------ | -------- | ------------------------------------------------ |
| bizid | string | Y        | 业务域id                                         |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success删除成功, error删除失败 |
| message | string | N        | 失败时的错误信息               |

### 2.1.3 查询

**描述**

列出所有业务域。

**Url**

`/nl2sql/business/list`

**Method**

`GET`

**Response**

| 字段    | 类型          | 是否必须 | 说明                           |
| ------- | ------------- | -------- | ------------------------------ |
| status  | string        | Y        | success查询成功, error查询失败 |
| data    | array<object> | Y        | 查询结果数据                   |
| message | string        | N        | 失败时的错误信息               |

其中data结构为：

| 字段        | 类型   | 是否必须 | 说明           |
| ----------- | ------ | -------- | -------------- |
| bizid       | string | 是       |                |
| create_time | string | 是       | 业务域创建时间 |



## 2.2 业务知识相关接口

### 2.2.1 新增/更新

**描述**

该接口可批量增加/修改业务知识。在创建业务知识之前，需要保证业务域和业务知识所关联的表已经创建。由于创建/更新业务知识过程耗时较长，建议设置稍微大一点的超时时间。建议15s以上。

**Url**

`/nl2sql/knowledge/create_or_update`

**Method**

`POST`

**Request**

| 字段      | 类型   | 是否必须 | 说明                                             |
| --------- | ------ | -------- | ------------------------------------------------ |
| bizid | string | Y        | 该条业务知识所属业务域id |
| knowledges | Array<knowledge> | Y       | 新增的业务知识 |

其中的knowledge结构为:

| 字段         | 类型          | 是否必须 | 说明                                                         |
| ------------ | ------------- | -------- | ------------------------------------------------------------ |
| knowledge_id | string        | Y        | 业务知识id，客户端应使用合适的UUID算法来生成。需保证该业务域下唯一 |
| table_id     | string        | Y        | 该条业务知识所属表的id                                       |
| key_alpha    | string        | N        | 业务知识的A标签，用于表召回环节的标签                        |
| key_beta     | array<string> | N        | 业务知识的B标签，用于业务知识的字符匹配召回                  |
| value        | string        | Y        | 业务知识                                                     |

**Response**

| 字段    | 类型          | 是否必须 | 说明                                                         |
| ------- | ------------- | -------- | ------------------------------------------------------------ |
| status  | string        | Y        | success接口调用成功, error接口调用失败。如果只有有某一条业务知识操作失败，这里依然会返回成功。 |
| data    | array<object> | Y        | 每一条业务知识的操作情况                                     |
| message | string        | N        | 失败时的错误信息                                             |

其中data结构为：

| 字段         | 类型   | 是否必须 | 说明                           |
| ------------ | ------ | -------- | ------------------------------ |
| knowledge_id | string | Y        | 该条业务知识的id               |
| status       | string | Y        | success操作成功, error操作失败 |
| message      | string | Y        | 失败时的错误信息               |

### 2.2.2 删除

**描述**

批量删除业务知识。

**Url**

`/nl2sql/knowledge/delete`
**Method**

`POST`

**Request**

| 字段         | 类型            | 是否必须 | 说明                                             |
| ------------ | --------------- | -------- | ------------------------------------------------ |
| bizid        | string          | Y        | 业务域id                                         |
| knowledge_ids| array\<string\> | Y        | 要删除的业务知识id列表                           |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success删除成功, error删除失败 |
| message | string | N        | 操作结果信息                   |

### 2.2.3 查询

**描述**

查询某业务域，某表下的所有的业务知识

**Url**
`/nl2sql/knowledge/list`
**Method**

`GET`
**Request**

| 字段      | 类型   | 是否必须 | 说明                                             |
| --------- | ------ | -------- | ------------------------------------------------ |
| bizid | string | Y       | 业务域id                             |
| table_id | string | N | 可根据表id进行筛选 |

**Response**

| 字段    | 类型             | 是否必须 | 说明                           |
| ------- | ---------------- | -------- | ------------------------------ |
| status  | string           | Y        | success查询成功, error查询失败 |
| data    | array<knowledge> | N        | 查询结果数据                   |
| message | string           | N        | 失败时的错误信息               |

其中的knowledge结构为:

| 字段         | 类型          | 是否必须 | 说明                                        |
| ------------ | ------------- | -------- | ------------------------------------------- |
| knowledge_id | string        | Y        | 业务知识id                                  |
| table_id     | string        | Y        | 该条业务知识所属表的id                      |
| key_alpha    | string        | N        | 业务知识的A标签，用于表召回环节的标签       |
| key_beta     | array<string> | N        | 业务知识的B标签，用于业务知识的字符匹配召回 |
| value        | string        | Y        | 业务知识文本内容                            |

## 2.3 案例库相关接口
### 2.3.1 新增/更新

**描述**

新增/更新SQL语句案例库。支持批量更新。

**Url**

`/nl2sql/sqlcases/create_or_update`

**Method**

`POST`

**Request**

| 字段     | 类型           | 是否必须 | 说明                   |
| -------- | -------------- | -------- | ---------------------- |
| bizid    | string         | Y        | 需新增案例库的业务域id |
| sqlcases | array<sqlcase> | Y        | SQL语句案例            |

其中sqlcase的结构为:

| 字段    | 类型          | 是否必须 | 说明                                                         |
| ------- | ------------- | -------- | ------------------------------------------------------------ |
| case_id | string        | Y        | 案例id，客户端应使用合适的UUID算法来生成。需保证该业务域下唯一。 |
| querys  | array<string> | Y        | 该条SQL案例的自然语言，可以是多条。任意一条匹配都会响应。    |
| sql     | sql           | Y        | 该条SQL案例的SQL语句。                                       |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success创建成功, error创建失败 |
| message | string | N        | 失败时的错误信息               |

### 2.3.2 删除

**描述**

删除某条SQL案例

**Url**
`/nl2sql/sqlcases/delete`
**Method**

`POST`
**Request**

| 字段    | 类型   | 是否必须 | 说明             |
| ------- | ------ | -------- | ---------------- |
| bizid  | string | Y        | 所操作的业务域id |
| case_id | string | Y        | 所操作的案例id   |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success删除成功, error删除失败 |
| message | string | N        | 失败时的错误信息               |

### 2.3.3 查询

**描述**

查询该业务下的所有案例库。

**Url**
`/nl2sql/sqlcases/list`
**Method**

`GET`
**Request**

| 字段   | 类型   | 是否必须 | 说明             |
| ------ | ------ | -------- | ---------------- |
| bizid | string | Y        | 所查询的业务域id |

**Response**

| 字段     | 类型           | 是否必须 | 说明                           |
| -------- | -------------- | -------- | ------------------------------ |
| status   | string         | Y        | success查询成功, error查询失败 |
| sqlcases | array<sqlcase> | Y        | 查询结果数据                   |
| message  | string         | N        | 失败时的错误信息               |

其中sqlcase的结构为

| 字段    | 类型          | 是否必须 | 说明                                                         |
| ------- | ------------- | -------- | ------------------------------------------------------------ |
| case_id | string        | Y        | 案例id，客户端应使用合适的UUID算法来生成。需保证该业务域下唯一。 |
| querys  | array<string> | Y        | 该条SQL案例对应的自然语言。                                  |
| sql     | sql           | Y        | 该条SQL案例的SQL语句。                                       |

## 2.4 Prompt配置接口
### 2.4.1 更新

**描述**

NL2SQL相关所有的Prompt设置。业务域新创之后，会使用默认prompt模版配置。

**Url**

`/nl2sql/prompt/update`

**Method**

`POST`

**Request**

| 字段    | 类型   | 是否必须 | 说明           |
| ------- | ------ | -------- | -------------- |
| bizid   | string | Y        | 操作的业务域id |
| prompts | object | Y        | 需修改的prompt |

其中prompts的结构为

| 字段                  | 类型   | 是否必须 | 说明                 |
| --------------------- | ------ | -------- | -------------------- |
| time_convert_agent    | string | N        | 时间转换agent prompt |
| nl2sql_agent          | string | N        | NL2SQL prompt        |
| element_extract_agent | string | N        | 要素抽取 prompt      |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success更新成功, error更新失败 |
| message | string | N        | 失败时的错误信息               |

### 2.4.2 查询

**描述**

查询某业务域的所有prompt配置。

**Url**
`/nl2sql/prompt/list`

**Method**

`POST`

**Request**

| 字段  | 类型   | 是否必须 | 说明   |
| ----- | ------ | -------- | ------ |
| bizid | string | Y        | 业务id |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success查询成功, error查询失败 |
| prompts | object | Y        | prompts                        |
| message | string | N        | 失败时的错误信息               |

其中prompts的结构为:

| 字段                  | 类型   | 是否必须 | 说明                 |
| --------------------- | ------ | -------- | -------------------- |
| time_convert_agent    | string | N        | 时间转换agent prompt |
| nl2sql_agent          | string | N        | NL2SQL prompt        |
| element_extract_agent | string | N        | 要素抽取 prompt      |

## 2.5 库表信息相关接口
### 2.5.1 新增/更新

**描述**

在某业务域下批量新建/更新数据表信息，每次最多10个表。

**Url**
`/nl2sql/tableinfo/create_or_update`
**Method**

`POST`
**Request**

| 字段  | 类型          | 是否必须 | 说明                                 |
| ----- | ------------- | -------- | ------------------------------------ |
| bizid | string        | Y        | 关联的业务域                         |
| tables | array<object> | Y        | 库表信息列表，最少1个表，最多10个表 |

其中table的结构为：

| 字段          | 类型          | 是否必须 | 说明                                         |
| ------------- | ------------- | -------- | -------------------------------------------- |
| table_id      | string        | Y        | 新增的表id，客户端应使用合适的UUID算法来生成 |
| table_name    | string        | Y        | 表名                                         |
| table_comment | string        | Y        | 表的描述                                     |
| fields        | array<object> | Y        | 表的字段                                     |

其中field的结构为：

| 字段     | 类型   | 是否必须 | 说明                                                      |
| -------- | ------ | -------- | --------------------------------------------------------- |
| field_id | string | Y        | 字段UUID                                                  |
| name     | string | Y        | 字段名                                                    |
| datatype | string | Y        | 字段类型。字段类型所属方言，应该与text2sql prompt相匹配。 |
| comment  | string | Y        | 字段描述                                                  |

**Response**

| 字段    | 类型          | 是否必须 | 说明                                                         |
| ------- | ------------- | -------- | ------------------------------------------------------------ |
| status  | string        | Y        | success创建成功, error创建失败                               |
| tables  | array<object> | Y        | 成功创建或更新的表信息                                       |
| message | string        | N        | 失败时的错误信息，如果批量操作中有部分表失败，会包含具体错误 |

### 2.5.2 删除

**描述**

删除某张表或多张表的所有信息，同时删除相关的业务知识和维度值。

**Url**
`/nl2sql/tableinfo/delete`
**Method**

`POST`
**Request**

| 字段      | 类型             | 是否必须 | 说明                                   |
| --------- | ---------------- | -------- | -------------------------------------- |
| bizid     | string           | Y        | 业务id                                 |
| table_ids | array\<string\>  | Y        | 要删除的表id列表，可以包含一个或多个id  |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success删除成功, error删除失败 |
| message | string | N        | 操作结果信息，包含删除的表数量和相关资源数量 |

### 2.5.3 查询

**描述**

根据bizid和table_id查询某张表的所有元信息。

**Url**
`/nl2sql/tableinfo/list`
**Method**

`POST`

**Request**

| 字段     | 类型   | 是否必须 | 说明                                             |
| -------- | ------ | -------- | ------------------------------------------------ |
| bizid    | string | Y        | 业务id                                           |
| table_id | string | N        | 表id。如果不提供，默认查询该业务下的所有表信息。 |

**Response**

| 字段    | 类型          | 是否必须 | 说明                           |
| ------- | ------------- | -------- | ------------------------------ |
| status  | string        | Y        | success创建成功, error创建失败 |
| message | string        | N        | 失败时的错误信息               |
| tables  | array<object> | Y        | 查询的表信息                   |

其中table的结构为：

| 字段          | 类型          | 是否必须 | 说明     |
| ------------- | ------------- | -------- | -------- |
| table_id      | string        | Y        | 表id     |
| table_name    | string        | Y        | 表名     |
| table_comment | string        | Y        | 表的描述 |
| fields        | array<object> | Y        | 表的字段 |

其中field的结构为：

| 字段     | 类型   | 是否必须 | 说明                                                      |
| -------- | ------ | -------- | --------------------------------------------------------- |
| field_id | string | Y        | 字段UUID                                                  |
| name     | string | Y        | 字段名                                                    |
| datatype | string | Y        | 字段类型。字段类型所属方言，应该与text2sql prompt相匹配。 |
| comment  | string | Y        | 字段描述                                                  |

### 2.5.4 基于向量搜索表

**描述**

根据语义向量匹配最相似的表。

**Url**
`/nl2sql/tableinfo/search_by_embedding`
**Method**

`POST`

**Request**

| 字段            | 类型          | 是否必须 | 说明                                 |
| --------------- | ------------- | -------- | ------------------------------------ |
| bizid           | string        | Y        | 业务域ID                             |
| query_embedding | array<float>  | Y        | 查询文本的向量表示                   |
| top_k           | int           | N        | 返回的最大结果数量（默认为5）        |
| min_score       | float         | N        | 最小相似度阈值（默认为0.7）          |

**Response**

| 字段    | 类型          | 是否必须 | 说明                           |
| ------- | ------------- | -------- | ------------------------------ |
| status  | string        | Y        | success成功, error失败         |
| message | string        | N        | 失败时的错误信息               |
| tables  | array<object> | Y        | 匹配到的表信息列表             |

## 2.6 其他设置相关接口

### 2.6.1 更新

**描述**

nl2sql流程相关参数设置。

**Url**
`/nl2sql/settings/update`
**Method**

`POST`
**Request**

| 字段                     | 类型   | 是否必须 | 说明                        |
| ------------------------ | ------ | -------- | --------------------------- |
| bizid                    | string | Y        | 业务域id                    |
| table_retrieve_threshold | string | N        | 表召回阈值。（0 - 1）之间。 |
| enable_table_auth        | bool   | N        | 是否开启表权限校验          |
| deep_semantic_search     | bool   | N        | 是否开启深度语义搜索        |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success更新成功, error更新失败 |
| message | string | N        | 失败时的错误信息               |

### 2.6.2 查询

**Url**
`/nl2sql/settings/list`
**Method**

`POST`
**Request**

| 字段  | 类型   | 是否必须 | 说明     |
| ----- | ------ | -------- | -------- |
| bizid | string | Y        | 业务域id |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success查询成功, error查询失败 |
| data    | object | N        | 查询结果数据                   |
| message | string | N        | 失败时的错误信息               |

其中data的结构为：

| 字段                     | 类型   | 是否必须 | 说明                        |
| ------------------------ | ------ | -------- | --------------------------- |
| table_retrieve_threshold | string | N        | 表召回阈值。（0 - 1）之间。 |
| enable_table_auth        | bool   | N        | 是否开启表权限校验          |
| deep_semantic_search     | bool   | N        | 是否开启深度语义搜索        |

## 2.7 同义词配置相关接口
### 2.7.1 新增/更新

**描述**

新增一个同义词信息。当输入中有匹配到副义词，会自动把主义词拼接到问题之中。

**Url**
`/nl2sql/synonym/create_or_update`
**Method**

`POST`
**Request**

| 字段     | 类型          | 是否必须 | 说明       |
| -------- | ------------- | -------- | ---------- |
| bizid    | string        | Y        | 业务id     |
| synonyms | array<object> | Y        | 同义词信息 |

其中synonym的结构为：

| 字段      | 类型          | 是否必须 | 说明               |
| --------- | ------------- | -------- | ------------------ |
| primary   | string        | Y        | 主义词。           |
| secondary | array<string> | Y        | 副义词。允许多个。 |

**Response**

| 字段    | 类型   | 是否必须 | 说明                   |
| ------- | ------ | -------- | ---------------------- |
| status  | string | Y        | success成功, error失败 |
| message | string | N        | 失败时的错误信息       |

### 2.7.2 删除

**描述**

删除一个同义词信息

**Url**
`/nl2sql/synonym/delete`
**Method**

`POST`
**Request**

| 字段    | 类型   | 是否必须 | 说明                   |
| ------- | ------ | -------- | ---------------------- |
| bizid   | string | Y        | 业务id                 |
| primary | string | Y        | 待删除的主义词相关信息 |

**Response**

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success删除成功, error删除失败 |
| message | string | N        | 失败时的错误信息               |

### 2.7.3 查询

**描述**

查询某同义词信息

**Url**
`/nl2sql/synonym/list`
**Method**

`GET`
**Request**

| 字段    | 类型   | 是否必须 | 说明                                       |
| ------- | ------ | -------- | ------------------------------------------ |
| bizid   | string | Y        | 业务id                                     |
| primary | string | N        | 若不传，默认查询该业务下所有的同义词信息。 |

**Response**

| 字段     | 类型          | 是否必须 | 说明                           |
| -------- | ------------- | -------- | ------------------------------ |
| status   | string        | Y        | success查询成功, error查询失败 |
| synonyms | array<object> | Y        | 查询结果数据                   |
| message  | string        | N        | 失败时的错误信息               |

其中synonym的结构为：

| 字段      | 类型          | 是否必须 | 说明               |
| --------- | ------------- | -------- | ------------------ |
| primary   | string        | Y        | 主义词。           |
| secondary | array<string> | Y        | 副义词。允许多个。 |



## 2.8 生成接口
### 2.8.1 单次生成接口

**描述**

输入自然语言，生成对应SQL。可采用SSE方式流式返回。

**Url**
`/nl2sql/generate`
**Method**

`POST`
**Request**

| 字段     | 类型   | 是否必须 | 说明                                                         |
| -------- | ------ | -------- | ------------------------------------------------------------ |
| bizid    | string | Y        | 业务id                                                       |
| query    | string | Y        | 自然语言输入                                                 |
| summary  | string | N        | 查询摘要，用于上下文理解                                     |
| settings | Settings | N      | 可以在单次输入中，指定所使用的相关超参数设置。具体参数可见`settings`接口 |
| stream   | bool   | Y        | 是否使用SSE流式返回                                          |
| table_id | string | N        | 可选的表ID，如果提供则直接使用此表，不进行表推荐             |

**Response**

非流式返回

| 字段    | 类型   | 是否必须 | 说明                           |
| ------- | ------ | -------- | ------------------------------ |
| status  | string | Y        | success发起成功, error发起失败 |
| message | string | N        | 失败时的报错信息               |
| sqls    | array<object> | Y       | 生成的sql                      |

其中sql的结构为：

| 字段     | 类型   | 是否必须 | 说明                     |
| -------- | ------ | -------- | ------------------------ |
| sql_text | string | Y        | 生成的sql代码            |
| nl_text  | string | Y        | 输入nl2sql模型的最终意图 |

流式返回

TODO

### 2.8.2 元数据查询接口

**描述**

输入自然语言，返回该查询可能匹配的表信息和指标信息，不生成SQL语句。适用于分析用户意图及进行调试。

**Url**
`/nl2sql/query_metadata`
**Method**

`POST`
**Request**

| 字段     | 类型    | 是否必须 | 说明                         |
| -------- | ------- | -------- | ---------------------------- |
| bizid    | string  | Y        | 业务id                       |
| query    | string  | Y        | 自然语言输入                 |
| summary  | string  | N        | 查询摘要，用于上下文理解     |
| settings | Settings | N      | 可指定相关超参数设置         |

**Response**

| 字段       | 类型          | 是否必须 | 说明                           |
| ---------- | ------------- | -------- | ------------------------------ |
| status     | string        | Y        | success查询成功, error查询失败 |
| message    | string        | N        | 失败时的报错信息               |
| tables     | array<object> | Y        | 匹配到的表信息列表             |
| alpha_keys | array<string> | Y        | 匹配到的alpha知识关键词列表     |

其中tables的结构为：

| 字段       | 类型   | 是否必须 | 说明   |
| ---------- | ------ | -------- | ------ |
| table_id   | string | Y        | 表ID   |
| table_name | string | Y        | 表名称 |

### 2.8.3 SQL解析接口

**描述**

解析SQL语句，返回易于理解的描述。

**Url**
`/nl2sql/sql_explain`
**Method**

`POST`
**Request**

| 字段      | 类型          | 是否必须 | 说明     |
| --------- | ------------- | -------- | -------- |
| bizid     | string        | Y        | 业务域ID |
| sql       | string        | Y        | SQL语句  |
| table_info| array<object> | N        | 表信息   |

**Response**

| 字段    | 类型   | 是否必须 | 说明                     |
| ------- | ------ | -------- | ------------------------ |
| status  | string | Y        | success成功, error失败   |
| message | string | N        | 失败时的错误信息         |
| result  | string | N        | 解析结果                 |

### 2.8.4 SQL注释接口

**描述**

为SQL语句添加注释。

**Url**
`/nl2sql/sql_comment`
**Method**

`POST`
**Request**

| 字段  | 类型   | 是否必须 | 说明     |
| ----- | ------ | -------- | -------- |
| bizid | string | Y        | 业务域ID |
| sql   | string | Y        | SQL语句  |

**Response**

| 字段    | 类型   | 是否必须 | 说明                     |
| ------- | ------ | -------- | ------------------------ |
| status  | string | Y        | success成功, error失败   |
| message | string | N        | 失败时的错误信息         |
| result  | string | N        | 添加注释后的SQL          |

### 2.8.5 SQL纠正接口

**描述**

纠正SQL语句中的错误。

**Url**
`/nl2sql/sql_correct`
**Method**

`POST`
**Request**

| 字段  | 类型   | 是否必须 | 说明     |
| ----- | ------ | -------- | -------- |
| bizid | string | Y        | 业务域ID |
| sql   | string | Y        | SQL语句  |

**Response**

| 字段    | 类型   | 是否必须 | 说明                     |
| ------- | ------ | -------- | ------------------------ |
| status  | string | Y        | success成功, error失败   |
| message | string | N        | 失败时的错误信息         |
| result  | string | N        | 纠正后的SQL              |

## 2.9 维度值相关接口
### 2.9.1 新增/更新

**描述**

批量创建或更新维度值信息，提供更灵活的值存储和查询方式。

**Url**
`/nl2sql/dim_values/create_or_update`
**Method**

`POST`
**Request**

| 字段     | 类型          | 是否必须 | 说明         |
| -------- | ------------- | -------- | ------------ |
| bizid    | string        | Y        | 业务域ID     |
| table_id | string        | Y        | 表ID         |
| field_id | string        | Y        | 字段ID       |
| values   | array<object> | Y        | 维度值列表   |

其中维度值的结构为:

| 字段  | 类型   | 是否必须 | 说明     |
| ----- | ------ | -------- | -------- |
| value | string | Y        | 维度值   |

**Response**

| 字段    | 类型   | 是否必须 | 说明                   |
| ------- | ------ | -------- | ---------------------- |
| status  | string | Y        | success成功, error失败 |
| message | string | N        | 失败时的错误信息       |

### 2.9.2 删除

**描述**

删除维度值信息，可以删除特定值或删除某字段的所有值。

**Url**
`/nl2sql/dim_values/delete`
**Method**

`POST`
**Request**

| 字段     | 类型   | 是否必须 | 说明                               |
| -------- | ------ | -------- | ---------------------------------- |
| bizid    | string | Y        | 业务域ID                           |
| table_id | string | Y        | 表ID                               |
| field_id | string | Y        | 字段ID                             |
| value    | string | N        | 特定值，不提供则删除该字段所有维度值 |

**Response**

| 字段    | 类型   | 是否必须 | 说明                   |
| ------- | ------ | -------- | ---------------------- |
| status  | string | Y        | success成功, error失败 |
| message | string | N        | 失败时的错误信息       |

### 2.9.3 查询

**描述**

列出维度值信息，可以按业务域、表和字段筛选。

**Url**
`/nl2sql/dim_values/list`
**Method**

`POST`
**Request**

| 字段     | 类型   | 是否必须 | 说明           |
| -------- | ------ | -------- | -------------- |
| bizid    | string | Y        | 业务域ID       |
| table_id | string | N        | 表ID           |
| field_id | string | N        | 字段ID         |

**Response**

| 字段    | 类型          | 是否必须 | 说明                   |
| ------- | ------------- | -------- | ---------------------- |
| status  | string        | Y        | success成功, error失败 |
| message | string        | N        | 失败时的错误信息       |
| values  | array<object> | Y        | 维度值列表             |

### 2.9.4 搜索

**描述**

通过模糊匹配搜索维度值，支持对值进行模糊搜索。

**Url**
`/nl2sql/dim_values/search`
**Method**

`POST`
**Request**

| 字段     | 类型   | 是否必须 | 说明     |
| -------- | ------ | -------- | -------- |
| bizid    | string | Y        | 业务域ID |
| query    | string | Y        | 搜索词   |
| table_id | string | N        | 表ID     |
| field_id | string | N        | 字段ID   |

**Response**

| 字段    | 类型          | 是否必须 | 说明                   |
| ------- | ------------- | -------- | ---------------------- |
| status  | string        | Y        | success成功, error失败 |
| message | string        | N        | 失败时的错误信息       |
| values  | array<object> | Y        | 匹配的维度值列表       |

## 2.10 知识向量搜索接口

**描述**

根据语义向量匹配最相似的知识条目。

**Url**
`/nl2sql/knowledge/search_by_embedding`
**Method**

`POST`
**Request**

| 字段            | 类型         | 是否必须 | 说明                          |
| --------------- | ------------ | -------- | ----------------------------- |
| bizid           | string       | Y        | 业务域ID                      |
| query_embedding | array<float> | Y        | 查询文本的向量表示            |
| top_k           | int          | N        | 返回的最大结果数量（默认为5） |
| min_score       | float        | N        | 最小相似度阈值（默认为0.7）   |

**Response**

| 字段    | 类型          | 是否必须 | 说明                   |
| ------- | ------------- | -------- | ---------------------- |
| status  | string        | Y        | success成功, error失败 |
| message | string        | N        | 失败时的错误信息       |
| data    | array<object> | N        | 匹配结果               |

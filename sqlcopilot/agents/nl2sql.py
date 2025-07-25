from typing import Optional, Dict
from string import Template
from datetime import datetime, timedelta

import json
from loguru import logger

from llm import openai_client

default_key_element_prompt = Template(
    """

用户输入一段自然语言, 请将其中的筛选条件、分组维度类型和排序维度类型, 仿照sql语句中的where, group_by, order_by抽取出来.
---
根据以下格式输出
Query: 用户的输入 
Sql Clauses: 解析出来的数组格式json 字符串, 抽取的时候, 不要考虑任何可能的聚合手段, 
当成维度或者维值输出. 遇到任何时间,地理,位置相关的维度或者维值, 都需要输出.
具体格式为：{"where":[],"group_by":[],"order_by":[]}

##Notes
注意，只输出SqlClauses的抽取结果，不要有任何其他解释内容
---
Query: 按部门统计处理的投诉的工单有多少?限定南山区，按照投诉量排序.
Sql Clauses: {"where":["南山区","投诉"],"group_by":["部门"],"order_by":["投诉量"]}
---
Query: 2023年1月23日各省的宽带收入？
Sql Clauses: {"where":["2023年1月23日","宽带"],"group_by":["省份"],"order_by":[]}
---
Query: 2023-01至2023-09的深圳不同本地网的流动人口数，按本地网排序
Sql Clauses: {"where":["2023-01至2023-09","深圳","流动"],"group_by":["本地网"],"order_by":["本地网"]}
---
Query: ${user_input}

Sql Clauses: 

"""
)

default_time_convert_prompt = Template(
    """

请根据当前系统时间，将用户的输入中的相对时间筛选条件，转换为绝对时间。如果用户的输入中没有指定时间，则直接返回原始的输入。
在输出的时候，不要有任何reasoing

请根据以下格式处理输入输出：

current_time: 当前系统时间
user_input: 用户的文字输入，一般来说是对sql数据库的自然语言查询。
output: 附带了查询时间的输出
---
current_time: ${current_time}
user_input: 查询昨天的工单量
reasoning: 因为当前时间为${current_time}, 则昨天是${yesterday}
output: 查询${yesterday}的工单量
---
current_time: ${current_time}
user_input: 查询建单时间在前三个月的工单量
reasoning: 因为时间为${current_time}, 则三个月前是${three_months_ago}, 用户指定了筛选字段为建单时间
output: 查询建单时间为${three_months_ago}到${current_time}的工单量
---
current_time: ${current_time}
user_input: 查询成都工单量
reasoning: 因为用户在原始查询中没有附带任何时间，则直接输出原始输入
output: 查询成都工单量
---
current_time: ${current_time}
user_input: 查询2024年3月的工单量
reasoning: 因为用户指定了绝对时间，不需要作任何处理。
output: 查询2024年3月的工单量
---

注意：
如果用户输入提到"去年一年", 那么查询的是从去年1月1日到去年12月31日。而不是从去年今天到今年今天

Let's think step by step!

current_time: ${current_time}
user_input: ${user_input}
output: 

"""
)


default_nl2sql_prompt = Template(
    """

### Task
Generate a MySQL database query to answer [QUESTION]${query}[/QUESTION]

### Instructions
- database schema里面可能含有多余的信息，要自行筛选
- 注意只能用database schema的字段信息，不允许编造字段
- 如果有as关键字，后面一定要加空格，例如：as '投诉量'；
- sql请直接输出, 其中不要出现任何注释解释，不要编造字段。
- 如果问题中有时间信息，时间使用between and，大于、小于，取值注意时间格式；
- 如果Metric有提供，一定要按照metric里面的规则，来生成sql语句，并在此基础上根据用户输入增加或者修改条件。
- 如果EXTRA INFO有提供，请参考提供的信息生成sql。
- 不要生成任何带有having clause条件的sql.
- 如果有metric和extrainfo等信息，请在不影响SQL语法，不违反查询语义的情况下，参考。
- 如果提供了示例，当示例和用户输入的查询语义相似的情况下，请一定参考。
- 生成的SQL一定要用markdown block包裹住。如```sql ```

### Metric
${metric}

### Extra Info
${business_knowledge}
${synonym}
${field_value_info}

### Possible Examples
${fewshot}

### Database Schema
The query will run on a database with the following schema in markdown format:
${schema}

### Answer
根据提供的数据库信息和其他信息，这里是符合[QUESTION]${query}[/QUESTION]的SQL查询语句：

"""
)


default_sql_explain_prompt = Template(
    """

# 给你sql语句
```
${sql}
```
# 给你表的信息
${table_info}

请用中文解释给你的sql语句，表信息做参考，如果没有表信息则直接解释。

"""
)


default_sql_comment_prompt = Template(
    """

你是一名做数据分析的SQL工程师，你被要求根据提供的sql建表语句生成字段的中文注释，返回新的sql语句。
请注意，在SQL中，你可以使用`COMMENT`关键字来为表、列或视图添加注释。我的SQL服务器支持中文字符集，并且你正在使用的客户端也支持它。
下面是一些例子
示例1:
user: '''
create table if not exists table1 
(file_name TEXT
)
'''
Assistant: 
'''
create table if not exists table1 
(file_name TEXT '文件名'
)
'''

示例2:
user: '''
create table if not exists table1 
(ent_name TEXT
desc TEXT 
)
'''
Assistant: 
'''
create table if not exists table1 
(ent_name TEXT comment '企业名称'
desc TEXT comment '描述'
)
'''
请按照示例的格式，输出assistant的回答，只返回sql！
对下面的sql语句生成"字段"的中文comment
# 给你的sql语句
```
${sql}
```
'''
"""
)


default_sql_correct_prompt = Template(
    """

### Task
根据给定的sql语句进行分析判度是否语法错误, 如果错误则改写成正确的sql语句, 如果没有错误则返回原sql语句.

### Introduction
不需要任何解释和提示！直接以markdown格式返回代码'

### 给定的sql语句
```
${sql}
```

### 正确的sql语句是

"""
)


default_query_parse_prompt = Template(
    """
    你是一个数据工程师，需要你做下面的工作：

# 要求
1.分析用户输入的query，解析出实体。不要解析时间。
2.对实体赋予实体类型，如：字段、省份等。
3.如果用户输入中包含表名，则将表名作为table的值。
4.结构化输出结果，如果有参考信息，按参考信息输出，没有参考信息按通用语义理解输出。
每个实体的输出格式：
{      
        "entity_text": str,
        "entity_name": str,
        "entity_type": str
}

entity_text，代表输入中提取到的实体的实际内容
entity_value，代表输入中提取到的实体的具体分类，如果是表字段，该值为空。
entity_type，代表实体的类型，如果推测是表字段，则是field；如推测是地域，则是location。
4.只输出结构化结果，不要解释。

# 例子
1.用户输入：根据事故统计分析表查询去年每月各省高速公路死亡人数和经济损失
输出： 
 {
    "table": "事故统计分析表",
    "entity": [
        {
            "entity_text": "四川",
            "entity_name": "省份",
            "entity_type": "location"
        },
        {
            "entity_text": "交通事故数",
            "entity_name": "",
            "entity_type": "field"
        }
    ]
}

2.用户输入：福田区近三月投诉的工单量是多少？
输出：
{
    "table": "",
    "entity": [
        {
            "entity_text": "福田区",
            "entity_name": "区县",
            "entity_type": "location"
        },
        {
            "entity_text": "投诉的工单量",
            "entity_name": "",
            "entity_type": "field"
        }
    ]
}

用户输入：${query}
 """
)


class CustomTextAgent:
    def __init__(self, template: Template):
        self.template = template
        self.system_prompt = "你是codecopilot助手，善于解决各种问题。/no_think"

    def _generate(self, **kargs) -> str:
        user_input = self.template.substitute(kargs)
        logger.debug(user_input)
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_input})
        response = openai_client.generate(messages)
        return (
            response.choices[0].message.content
            if response.choices[0].message.content
            else ""
        )

    def _generate_stream(self, **kargs):
        user_input = self.template.substitute(kargs)
        logger.debug(user_input)
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_input})
        response = openai_client.generate(messages, stream=True)
        return response


class TimeConvertAgent(CustomTextAgent):
    def __init__(self, time_convert_prompt):
        super().__init__(time_convert_prompt)

    def generate(self, **kargs) -> Optional[str]:
        assert "current_time" in kargs, "current_time is required"
        assert "user_input" in kargs, "user_input is required"

        more_date = {
            "yesterday": kargs["current_time"] - timedelta(days=1),
            "three_months_ago": kargs["current_time"]
            - timedelta(days=90),  # approximation for 3 months
            "last_year": kargs["current_time"] - timedelta(days=365),
        }

        final_args = more_date | kargs

        return super()._generate(**final_args)


class KeyElementExtractAgent(CustomTextAgent):
    def __init__(self, key_element_prompt):
        super().__init__(key_element_prompt)

    def generate(self, **kargs) -> Dict:
        assert "user_input" in kargs, "user_input is required"
        resp = super()._generate(**kargs)

        # Strip "Sql Clauses: " prefix if it exists
        if resp.strip().startswith("Sql Clauses:"):
            resp = resp.strip()[len("Sql Clauses:") :].strip()

        try:
            element = json.loads(resp)
        except Exception as e:
            logger.info(f"Error: {str(e)}, element_text: {resp}")
            return {}
        return element


class Text2SQLAgent(CustomTextAgent):
    def __init__(self, template):
        super().__init__(template)

    @staticmethod
    def _parse_sql_from_code(inputs: str) -> str:
        import re

        # Extract SQL code from markdown code blocks
        sql_pattern = r"```sql\s+(.*?)\s*```"
        matches = re.findall(sql_pattern, inputs, re.DOTALL)

        if matches:
            # Return the first SQL code block found
            return matches[0].strip()
        else:
            # If no SQL code block is found, return the original input
            return inputs.strip()

    def generate(self, **kargs) -> str:
        for variable in [
            "query",
            "fewshot",
            "business_knowledge",
            "schema",
            "metric",
            "synonym",
            "field_value_info",
        ]:
            assert variable in kargs, f"{variable} is required!"
        try:
            resp = super()._generate(**kargs)
            return self._parse_sql_from_code(resp)
        except Exception as e:
            logger.info(f"Generating SQL Error: {str(e)} ")
            return ""

    async def generate_stream(self, **kargs):
        """
        Generate SQL in a streaming fashion, stripping away code block markers.

        Returns:
            An async generator that streams SQL code directly, without code block markers.
        """
        for variable in [
            "query",
            "fewshot",
            "business_knowledge",
            "schema",
            "metric",
            "synonym",
            "field_value_info",
        ]:
            assert variable in kargs, f"{variable} is required!"

        try:
            # Get the raw stream from OpenAI
            raw_stream = super()._generate_stream(**kargs)

            # Process the stream to extract SQL without code block markers
            inside_sql_block = False
            sql_start_marker = "```sql"
            sql_end_marker = "```"
            buffer = ""

            # raw_stream is not an async iterable, so we need to use a regular for loop
            for chunk in raw_stream:
                # Log the raw chunk for debugging
                # logger.debug(f"Raw stream chunk: {chunk}")
                if not hasattr(chunk.choices[0], "delta") or not hasattr(
                    chunk.choices[0].delta, "content"
                ):
                    continue

                content = chunk.choices[0].delta.content
                if not content:
                    continue

                # logger.debug("raw content: " + content)

                # Remove "data: " prefix if it exists
                if content.startswith("data: "):
                    content = content[6:]

                buffer += content

                # Process buffer to extract SQL
                if sql_start_marker in buffer and not inside_sql_block:
                    inside_sql_block = True
                    # Split at the SQL marker and keep the part after it
                    parts = buffer.split(sql_start_marker, 1)
                    buffer = parts[1] if len(parts) > 1 else ""
                    # If we have content to yield, yield it
                    if buffer:
                        # logger.debug("inside sql block: " + buffer)
                        yield buffer
                        buffer = ""
                elif sql_end_marker in buffer and inside_sql_block:
                    inside_sql_block = False
                    # Split at the end marker and keep only what's before it
                    parts = buffer.split(sql_end_marker, 1)
                    if parts[0]:
                        # logger.debug("outside sql block: " + parts[0])
                        yield parts[0]
                    buffer = parts[1] if len(parts) > 1 else ""
                elif inside_sql_block:
                    # Inside SQL block, yield buffer
                    # logger.debug("inside sql block: " + buffer)
                    yield buffer
                    buffer = ""
                else:
                    # Handle case where SQL is generated without code block markers
                    sql_keywords = [
                        "SELECT",
                        "FROM",
                        "WHERE",
                        "GROUP BY",
                        "ORDER BY",
                        "LIMIT",
                        "JOIN",
                    ]

                    # Check if buffer contains SQL keywords that strongly indicate it's an SQL statement
                    if any(keyword in buffer.upper() for keyword in sql_keywords):
                        # logger.debug("outside sql block: " + buffer)
                        yield buffer
                        buffer = ""
                    # If buffer gets too large, yield it anyway to prevent accumulation
                    elif len(buffer) > 100:
                        # logger.debug("outside sql block: " + buffer)
                        yield buffer
                        buffer = ""

            # Make sure to yield any remaining content in the buffer at the end
            if buffer:
                # Remove any "data: " prefix from the buffer
                if buffer.startswith("data: "):
                    buffer = buffer[6:]

                if inside_sql_block:
                    # logger.debug("outside sql block: " + buffer)
                    yield buffer
                else:
                    # For content outside SQL blocks, check if it looks like SQL
                    sql_keywords = [
                        "SELECT",
                        "FROM",
                        "WHERE",
                        "GROUP BY",
                        "ORDER BY",
                        "LIMIT",
                        "JOIN",
                    ]
                    if (
                        any(keyword in buffer.upper() for keyword in sql_keywords)
                        or len(buffer) > 0
                    ):
                        # logger.debug("outside sql block: " + buffer)
                        yield buffer

        except Exception as e:
            # logger.info(f"Streaming SQL Error: {str(e)}")
            yield f"Error generating SQL: {str(e)}"


class SqlExplainAgent(CustomTextAgent):
    def __init__(self, template):
        super().__init__(template)

    def generate(self, **kargs):
        """
        Process the SQL explanation request.

        Returns:
            A string containing the explanation of the SQL statement.
        """

        for variable in [
            "table_info",
            "sql",
        ]:
            assert variable in kargs, f"{variable} is required!"
        try:
            return super()._generate(**kargs)

        except Exception as e:
            logger.info(f"SQL Explain Error: {str(e)} ")
            return ""


class SqlCommentAgent(CustomTextAgent):
    def __init__(self, template):
        super().__init__(template)

    def generate(self, **kargs):
        """
        Process the SQL comment request.

        Returns:
            A string containing the SQL statement with added comments.
        """

        for variable in [
            "sql",
        ]:
            assert variable in kargs, f"{variable} is required!"
        try:
            return super()._generate(**kargs)

        except Exception as e:
            logger.info(f"SQL Comment Error: {str(e)} ")
            return ""


class SqlCorrectAgent(CustomTextAgent):
    def __init__(self, template):
        super().__init__(template)

    @staticmethod
    def _parse_sql_from_code(inputs: str) -> str:
        import re

        # Extract SQL code from markdown code blocks
        sql_pattern = r"```sql\s+(.*?)\s*```"
        matches = re.findall(sql_pattern, inputs, re.DOTALL)

        if matches:
            # Return the first SQL code block found
            return matches[0].strip()
        else:
            # If no SQL code block is found, return the original input
            return inputs.strip()

    def generate(self, **kargs):
        """
        Process the SQL correction request.

        Returns:
            A string containing the corrected SQL statement.
        """

        for variable in [
            "sql",
        ]:
            assert variable in kargs, f"{variable} is required!"
        try:
            resp = super()._generate(**kargs)
            return self._parse_sql_from_code(resp)

        except Exception as e:
            logger.info(f"SQL Correction Error: {str(e)} ")
            return ""


class QueryParseAgent(CustomTextAgent):
    def __init__(self, template):
        super().__init__(template)

    def generate(self, **kargs):
        """
        Process the query parse request.

        Returns:
            A string containing the query parse result.
        """
        
        for variable in [
            "query",
        ]:
            assert variable in kargs, f"{variable} is required!"

        logger.info(f"Query Parse Input: {kargs['query']}")
        try:
            return super()._generate(**kargs)

        except Exception as e:
            logger.info(f"Query Parse Error: {str(e)} ")
            return ""
import pytest
import requests
import uuid
import random
import time
import atexit
from loguru import logger

# Track all created business IDs for cleanup
_created_bizids = set()


# Cleanup function to delete all created business domains
def cleanup_resources():
    """Clean up all created test business domains, even for interrupted tests"""
    logger.info(f"Cleaning up {len(_created_bizids)} business domains...")
    for bizid in _created_bizids:
        try:
            response = requests.post(
                f"{BASE_URL}/nl2sql/business/delete", json={"bizid": bizid}
            )
            if response.status_code == 200:
                response_data = response.json()
                if response_data["status"] == "success":
                    logger.info(f"Successfully cleaned up business domain: {bizid}")
                else:
                    logger.warning(
                        f"Failed to clean up business domain {bizid}: Status was {response_data['status']}, message: {response_data.get('message', 'No message')}"
                    )
            else:
                logger.warning(
                    f"Failed to clean up business domain {bizid}: HTTP status {response.status_code}, response: {response.text}"
                )
        except Exception as e:
            logger.error(f"Error cleaning up business domain {bizid}: {str(e)}")
    _created_bizids.clear()


# Register cleanup function to run on exit
atexit.register(cleanup_resources)


# Register cleanup with pytest to handle KeyboardInterrupt and other exceptions
@pytest.fixture(scope="session", autouse=True)
def cleanup_fixture():
    """Pytest fixture to ensure cleanup runs even on KeyboardInterrupt"""
    yield
    cleanup_resources()


# Base URL for the API
BASE_URL = (
    "http://localhost:8001"  # Change this if your server runs on a different host/port
)


@pytest.fixture
def test_data():
    """Setup test data and create a unique business ID for isolation"""
    bizid = f"test-biz-{uuid.uuid4()}"
    test_table_id = f"test-table-{uuid.uuid4()}"
    test_field_id = f"test-field-{uuid.uuid4()}"

    # Track this bizid for cleanup
    _created_bizids.add(bizid)

    # Create a test business domain
    response = requests.post(
        f"{BASE_URL}/nl2sql/business/create", json={"bizid": bizid}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait a bit for the business to be fully created
    time.sleep(1)

    # Create test table (needed for other tests)
    test_table = {
        "bizid": bizid,
        "tables": [
            {
                "table_id": test_table_id,
                "table_name": "客服工单表",
                "table_comment": "这是一张客服工单表，记录了一个电话客服工单的整个生命周期情况",
                "fields": [
                    {
                        "field_id": test_field_id,
                        "name": "test_field",
                        "datatype": "string",
                        "comment": "Field for automated testing",
                    },
                    {
                        "field_id": f"{test_field_id}-order-code",
                        "name": "order_code",
                        "datatype": "string",
                        "comment": "工单编码，唯一标识一个客服工单",
                    },
                    {
                        "field_id": f"{test_field_id}-create-time",
                        "name": "create_time",
                        "datatype": "datetime",
                        "comment": "提单时间，客户提交工单的时间",
                    },
                    {
                        "field_id": f"{test_field_id}-location",
                        "name": "location",
                        "datatype": "string",
                        "comment": "所属行政区",
                    },
                    {
                        "field_id": f"{test_field_id}-address",
                        "name": "address",
                        "datatype": "string",
                        "comment": "详细地址，客户所在的详细地址",
                    },
                    {
                        "field_id": f"{test_field_id}-content",
                        "name": "content",
                        "datatype": "string",
                        "comment": "诉求内容，客户的具体问题或需求描述",
                    },
                    {
                        "field_id": f"{test_field_id}-is-satisfied",
                        "name": "is_satisfied",
                        "datatype": "int",
                        "comment": "工单是否满意，1表示满意，0表示不满意",
                    },
                    {
                        "field_id": f"{test_field_id}-complete-time",
                        "name": "complete_time",
                        "datatype": "datetime",
                        "comment": "办结时间，工单完成处理的时间",
                    },
                    {
                        "field_id": f"{test_field_id}-is-valid",
                        "name": "is_valid",
                        "datatype": "int",
                        "comment": "是否有效，1表示有效工单，0表示无效工单",
                    },
                ],
            }
        ],
    }
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/create_or_update", json=test_table
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Add location field values for the test table
    location_values = {
        "bizid": bizid,
        "table_id": test_table_id,
        "field_id": f"{test_field_id}-location",
        "values": [
            {"value": "武侯区"},
            {"value": "金牛区"},
            {"value": "高新区"},
            {"value": "青羊区"},
            {"value": "成华区"},
        ],
    }
    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/create_or_update",
        json=location_values,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Add synonym for Chengdu
    chengdu_synonym = {
        "bizid": bizid,
        "synonyms": [{"primary": "成都", "secondary": ["蓉城", "锦官城"]}],
    }
    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/create_or_update", json=chengdu_synonym
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Add business knowledge
    knowledge_items = {
        "bizid": bizid,
        "knowledges": [
            {
                "knowledge_id": f"knowledge-satisfied-{uuid.uuid4()}",
                "table_id": test_table_id,
                "key_alpha": "工单满意度",
                "value": "筛选is_satisfied=1",
            },
            {
                "knowledge_id": f"knowledge-valid-{uuid.uuid4()}",
                "table_id": test_table_id,
                "key_beta": ["有效工单"],
                "value": "筛选is_valid=1",
            },
        ],
    }
    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/create_or_update", json=knowledge_items
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for the table to be created
    time.sleep(2)

    # Return test data
    data = {
        "bizid": bizid,
        "test_table_id": test_table_id,
        "test_field_id": test_field_id,
    }

    yield data

    # Cleanup after tests
    response = requests.post(
        f"{BASE_URL}/nl2sql/business/delete", json={"bizid": bizid}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


# Business tests
def test_business_crud(test_data):
    """Test business domain CRUD operations"""
    # Test business creation (already done in fixture)

    # Test business listing
    response = requests.post(f"{BASE_URL}/nl2sql/business/list")
    assert response.status_code == 200

    # Verify our test business is in the list
    businesses = response.json()
    assert any(
        business["bizid"] == test_data["bizid"] for business in businesses["data"]
    ), f"Test business {test_data['bizid']} not found in business list"

    # The delete test is done in fixture cleanup


# Table tests
def test_table_crud(test_data):
    """Test basic CRUD operations for tables."""
    # Create is already tested in the fixture

    # Test list tables
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/list",
        json={"bizid": test_data["bizid"], "table_id": test_data["test_table_id"]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Test delete table
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/delete",
        json={"bizid": test_data["bizid"], "table_ids": [test_data["test_table_id"]]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify table is deleted
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/list",
        json={"bizid": test_data["bizid"], "table_id": test_data["test_table_id"]},
    )
    assert response.status_code == 200
    assert len(response.json()["tables"]) == 0


# Knowledge tests
def test_knowledge_crud(test_data):
    """Test knowledge CRUD operations"""
    # We need to recreate the test table that was deleted in test_table_crud
    test_table = {
        "bizid": test_data["bizid"],
        "tables": [
            {
                "table_id": test_data["test_table_id"],
                "table_name": "test_table",
                "table_comment": "Table for automated testing",
                "fields": [
                    {
                        "field_id": test_data["test_field_id"],
                        "name": "test_field",
                        "datatype": "string",
                        "comment": "Field for automated testing",
                    }
                ],
            }
        ],
    }
    requests.post(f"{BASE_URL}/nl2sql/tableinfo/create_or_update", json=test_table)

    # Create multiple knowledge entries to test batch operations
    knowledge_id1 = f"test-knowledge-{uuid.uuid4()}"
    knowledge_id2 = f"test-knowledge-{uuid.uuid4()}"
    create_request = {
        "bizid": test_data["bizid"],
        "knowledges": [
            {
                "knowledge_id": knowledge_id1,
                "table_id": test_data["test_table_id"],
                "key_alpha": "test_alpha_1",
                "key_beta": ["test_beta1", "test_beta2"],
                "value": "This is test knowledge 1 for automated testing",
            },
            {
                "knowledge_id": knowledge_id2,
                "table_id": test_data["test_table_id"],
                "key_alpha": "test_alpha_2",
                "key_beta": ["test_beta3", "test_beta4"],
                "value": "This is test knowledge 2 for automated testing",
            },
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/create_or_update", json=create_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for knowledge to be processed
    time.sleep(3)

    # Update one of the knowledge entries
    update_request = {
        "bizid": test_data["bizid"],
        "knowledges": [
            {
                "knowledge_id": knowledge_id1,
                "table_id": test_data["test_table_id"],
                "key_alpha": "updated_alpha",
                "key_beta": ["updated_beta1", "updated_beta2", "updated_beta3"],
                "value": "This is updated test knowledge for automated testing",
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/create_or_update", json=update_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for knowledge to be processed
    time.sleep(1)

    # List knowledge
    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/list",
        json={"bizid": test_data["bizid"], "table_id": test_data["test_table_id"]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify our knowledge data
    knowledge_list = response.json()["data"]
    assert len(knowledge_list) >= 2, "Not enough knowledge entries found"

    # Verify first knowledge entry was updated
    found_knowledge1 = next(
        (k for k in knowledge_list if k["knowledge_id"] == knowledge_id1), None
    )
    assert found_knowledge1 is not None, f"Test knowledge {knowledge_id1} not found"
    assert found_knowledge1["key_alpha"] == "updated_alpha"
    assert len(found_knowledge1["key_beta"]) == 3

    # Verify second knowledge entry exists
    found_knowledge2 = next(
        (k for k in knowledge_list if k["knowledge_id"] == knowledge_id2), None
    )
    assert found_knowledge2 is not None, f"Test knowledge {knowledge_id2} not found"
    assert found_knowledge2["key_alpha"] == "test_alpha_2"

    # Test batch deletion with multiple knowledge IDs
    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/delete",
        json={
            "bizid": test_data["bizid"],
            "knowledge_ids": [knowledge_id1, knowledge_id2],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for the deletion to be fully processed
    time.sleep(2)

    # Verify deletion of both entries
    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/list",
        json={"bizid": test_data["bizid"], "table_id": test_data["test_table_id"]},
    )
    knowledge_list = response.json()["data"]
    assert not any(k["knowledge_id"] == knowledge_id1 for k in knowledge_list), (
        f"Test knowledge {knowledge_id1} still exists after deletion"
    )
    assert not any(k["knowledge_id"] == knowledge_id2 for k in knowledge_list), (
        f"Test knowledge {knowledge_id2} still exists after deletion"
    )


# SQL Cases tests
def test_sqlcases_crud(test_data):
    """Test SQL cases CRUD operations"""
    # Create SQL case
    case_id = f"test-case-{uuid.uuid4()}"
    create_request = {
        "bizid": test_data["bizid"],
        "sqlcases": [
            {
                "case_id": case_id,
                "querys": ["How many records are there?", "Count all records"],
                "sql": "SELECT COUNT(*) FROM test_table",
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/sqlcases/create_or_update", json=create_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for SQL cases to be processed
    time.sleep(3)

    # Update SQL case
    update_request = {
        "bizid": test_data["bizid"],
        "sqlcases": [
            {
                "case_id": case_id,
                "querys": [
                    "How many records are there?",
                    "Count all records",
                    "Get total count",
                ],
                "sql": "SELECT COUNT(*) FROM test_table WHERE 1=1",
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/sqlcases/create_or_update", json=update_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for SQL cases to be processed
    time.sleep(1)

    # List SQL cases
    response = requests.post(
        f"{BASE_URL}/nl2sql/sqlcases/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify our SQL case data
    sqlcases = response.json()["sqlcases"]
    assert len(sqlcases) > 0, "No SQL cases found"
    found_case = next((c for c in sqlcases if c["case_id"] == case_id), None)
    assert found_case is not None, f"Test SQL case {case_id} not found"
    assert len(found_case["querys"]) == 3
    assert found_case["sql"] == "SELECT COUNT(*) FROM test_table WHERE 1=1"

    # Delete SQL case
    response = requests.post(
        f"{BASE_URL}/nl2sql/sqlcases/delete",
        json={"bizid": test_data["bizid"], "case_id": case_id},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for the deletion to be fully processed
    time.sleep(2)

    # Verify deletion
    response = requests.post(
        f"{BASE_URL}/nl2sql/sqlcases/list", json={"bizid": test_data["bizid"]}
    )
    sqlcases = response.json()["sqlcases"]
    assert not any(c["case_id"] == case_id for c in sqlcases), (
        f"Test SQL case {case_id} still exists after deletion"
    )


# Prompt tests
def test_prompt_crud(test_data):
    """Test prompt update and listing"""
    # Update prompts
    update_request = {
        "bizid": test_data["bizid"],
        "prompts": {
            "time_convert_agent": "This is a test time convert agent prompt",
            "nl2sql_agent": "This is a test NL2SQL agent prompt",
            "element_extract_agent": "This is a test element extract agent prompt",
        },
    }

    response = requests.post(f"{BASE_URL}/nl2sql/prompt/update", json=update_request)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # List prompts
    response = requests.post(
        f"{BASE_URL}/nl2sql/prompt/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify our prompt data
    prompts = response.json()["prompts"]
    assert prompts["time_convert_agent"] == "This is a test time convert agent prompt"
    assert prompts["nl2sql_agent"] == "This is a test NL2SQL agent prompt"
    assert (
        prompts["element_extract_agent"]
        == "This is a test element extract agent prompt"
    )


# Settings tests
def test_settings_crud(test_data):
    """Test settings update and listing"""
    # Update settings
    update_request = {
        "bizid": test_data["bizid"],
        "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
    }

    response = requests.post(f"{BASE_URL}/nl2sql/settings/update", json=update_request)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # List settings
    response = requests.post(
        f"{BASE_URL}/nl2sql/settings/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify our settings data
    settings = response.json()["data"]
    assert settings["table_retrieve_threshold"] == "0.85"
    assert settings["enable_table_auth"] == True


# Synonym tests
def test_synonym_crud(test_data):
    """Test synonym CRUD operations"""
    # Create synonym
    create_request = {
        "bizid": test_data["bizid"],
        "synonyms": [
            {"primary": "revenue", "secondary": ["income", "earnings", "proceeds"]}
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/create_or_update", json=create_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for synonyms to be processed
    time.sleep(3)

    # Update synonym
    update_request = {
        "bizid": test_data["bizid"],
        "synonyms": [
            {
                "primary": "revenue",
                "secondary": ["income", "earnings", "proceeds", "sales"],
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/create_or_update", json=update_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for synonyms to be processed
    time.sleep(1)

    # List synonyms
    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/list",
        json={"bizid": test_data["bizid"], "primary": "revenue"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify our synonym data
    synonyms = response.json()["synonyms"]
    assert len(synonyms) > 0, "No synonyms found"
    found_synonym = next((s for s in synonyms if s["primary"] == "revenue"), None)
    assert found_synonym is not None, "Test synonym 'revenue' not found"
    assert len(found_synonym["secondary"]) == 4
    assert "sales" in found_synonym["secondary"]

    # Delete synonym
    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/delete",
        json={"bizid": test_data["bizid"], "primary": "revenue"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for the deletion to be fully processed
    time.sleep(2)

    # Verify deletion
    response = requests.post(
        f"{BASE_URL}/nl2sql/synonym/list", json={"bizid": test_data["bizid"]}
    )
    synonyms = response.json()["synonyms"]
    assert not any(s["primary"] == "revenue" for s in synonyms), (
        "Test synonym 'revenue' still exists after deletion"
    )


# Field value tests
def test_field_value_crud(test_data):
    """Test field value CRUD operations"""
    # We need to recreate the test table if it was deleted in previous tests
    test_table = {
        "bizid": test_data["bizid"],
        "tables": [
            {
                "table_id": test_data["test_table_id"],
                "table_name": "test_table",
                "table_comment": "Table for automated testing",
                "fields": [
                    {
                        "field_id": test_data["test_field_id"],
                        "name": "test_field",
                        "datatype": "string",
                        "comment": "Field for automated testing",
                    }
                ],
            }
        ],
    }

    requests.post(f"{BASE_URL}/nl2sql/tableinfo/create_or_update", json=test_table)

    # Create field values
    create_request = {
        "bizid": test_data["bizid"],
        "table_id": test_data["test_table_id"],
        "field_id": test_data["test_field_id"],
        "values": ["value1", "value2", "value3"],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/create_or_update_field_value",
        json=create_request,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Update field values
    update_request = {
        "bizid": test_data["bizid"],
        "table_id": test_data["test_table_id"],
        "field_id": test_data["test_field_id"],
        "values": ["value1", "value2", "value3", "value4", "value5"],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/create_or_update_field_value",
        json=update_request,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


# Dimension Value tests
def test_dim_value_crud(test_data):
    """Test dimension value CRUD operations"""
    # We need to recreate the test table if it was deleted in previous tests
    test_table = {
        "bizid": test_data["bizid"],
        "tables": [
            {
                "table_id": test_data["test_table_id"],
                "table_name": "test_table",
                "table_comment": "Table for automated testing",
                "fields": [
                    {
                        "field_id": test_data["test_field_id"],
                        "name": "test_field",
                        "datatype": "string",
                        "comment": "Field for automated testing",
                    }
                ],
            }
        ],
    }

    requests.post(f"{BASE_URL}/nl2sql/tableinfo/create_or_update", json=test_table)

    # Create dimension values
    create_request = {
        "bizid": test_data["bizid"],
        "table_id": test_data["test_table_id"],
        "field_id": test_data["test_field_id"],
        "values": [
            {"value": "dimension1"},
            {"value": "dimension2"},
            {"value": "dimension3"},
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/create_or_update", json=create_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Update dimension values
    update_request = {
        "bizid": test_data["bizid"],
        "table_id": test_data["test_table_id"],
        "field_id": test_data["test_field_id"],
        "values": [
            {"value": "dimension1"},
            {"value": "dimension2"},
            {"value": "dimension3"},
            {"value": "dimension4"},
            {"value": "dimension5"},
        ],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/create_or_update", json=update_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Wait for dimension values to be processed
    time.sleep(1)

    # List dimension values
    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/list",
        json={
            "bizid": test_data["bizid"],
            "table_id": test_data["test_table_id"],
            "field_id": test_data["test_field_id"],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Search dimension values
    search_request = {
        "bizid": test_data["bizid"],
        "query": "dimension",
        "table_id": test_data["test_table_id"],
        "field_id": test_data["test_field_id"],
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/search", json=search_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify search results
    values = response.json()["values"]
    assert len(values) > 0, "No dimension values found in search"

    # Delete dimension value
    response = requests.post(
        f"{BASE_URL}/nl2sql/dim_values/delete",
        json={
            "bizid": test_data["bizid"],
            "table_id": test_data["test_table_id"],
            "field_id": test_data["test_field_id"],
            "value": "dimension1",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


# Generate SQL test
def test_generate_sql(test_data):
    """Test SQL generation from natural language"""
    inputs = [
        # "去年三月，蓉城武侯区满意的工单量有多少",
        "今年工单满意度",
        # "前天有效工单里面多少是满意的"
    ]

    for q in inputs:
        generate_request = {
            "bizid": test_data["bizid"],
            "query": q,
            "stream": False,
            "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
        }

        response = requests.post(f"{BASE_URL}/nl2sql/generate", json=generate_request)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify SQL generation
        sqls = response.json()["sqls"]
        assert len(sqls) > 0, "No SQL generated"
        assert "sql_text" in sqls[0], "SQL result doesn't contain 'sql_text' field"
        assert "nl_text" in sqls[0], "SQL result doesn't contain 'nl_text' field"

    # Test with specified table_id
    generate_request = {
        "bizid": test_data["bizid"],
        "query": "哪些是满意的工单?",
        "stream": False,
        "table_id": test_data["test_table_id"],  # Specify the table_id
        "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
    }

    response = requests.post(f"{BASE_URL}/nl2sql/generate", json=generate_request)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify SQL generation with specified table
    sqls = response.json()["sqls"]
    assert len(sqls) > 0, "No SQL generated"
    assert "sql_text" in sqls[0], "SQL result doesn't contain 'sql_text' field"
    assert "nl_text" in sqls[0], "SQL result doesn't contain 'nl_text' field"


def test_generate_sql_streaming(test_data):
    """Test SQL generation with streaming response"""
    inputs = [
        "今年工单满意度",
    ]

    for q in inputs:
        generate_request = {
            "bizid": test_data["bizid"],
            "query": q,
            "stream": True,
            "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
        }

        # When requesting a streaming response, use stream=True
        response = requests.post(
            f"{BASE_URL}/nl2sql/generate", json=generate_request, stream=True
        )

        assert response.status_code == 200
        assert (
            response.headers.get("content-type") == "text/event-stream; charset=utf-8"
        )

        # Collect streamed chunks
        collected_chunks = []
        for chunk in response.iter_lines():
            if chunk:
                # Skip empty chunks
                decoded_chunk = chunk.decode("utf-8")
                if not decoded_chunk.startswith("data: "):
                    continue

                # Remove "data: " prefix
                sql_chunk = decoded_chunk[6:]
                print(f"Received SQL chunk: {sql_chunk}")

                # Check for error messages
                if sql_chunk.startswith("ERROR:"):
                    assert False, f"Received error in stream: {sql_chunk}"

                collected_chunks.append(sql_chunk)

        # Verify we received some chunks
        assert len(collected_chunks) > 0, "No SQL chunks received in the stream"

        # Combine chunks to form complete SQL
        complete_sql = "".join(collected_chunks)

        # Basic validation that it looks like SQL
        assert "SELECT" in complete_sql.upper() or "WITH" in complete_sql.upper(), (
            f"Generated content doesn't look like SQL: {complete_sql}"
        )

    # Test streaming with specified table_id
    generate_request = {
        "bizid": test_data["bizid"],
        "query": "今年工单满意度",
        "stream": True,
        "table_id": test_data["test_table_id"],  # Specify the table_id
        "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
    }

    # When requesting a streaming response, use stream=True
    response = requests.post(
        f"{BASE_URL}/nl2sql/generate", json=generate_request, stream=True
    )

    assert response.status_code == 200
    assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"

    # Collect streamed chunks
    collected_chunks = []
    for chunk in response.iter_lines():
        if chunk:
            # Skip empty chunks
            decoded_chunk = chunk.decode("utf-8")
            if not decoded_chunk.startswith("data: "):
                continue

            # Remove "data: " prefix
            sql_chunk = decoded_chunk[6:]
            print(f"Received SQL chunk with specified table: {sql_chunk}")

            # Check for error messages
            if sql_chunk.startswith("ERROR:"):
                assert False, f"Received error in stream: {sql_chunk}"

            collected_chunks.append(sql_chunk)

    # Verify we received some chunks
    assert len(collected_chunks) > 0, "No SQL chunks received in the stream"

    # Combine chunks to form complete SQL
    complete_sql = "".join(collected_chunks)

    # Basic validation that it looks like SQL
    assert "SELECT" in complete_sql.upper() or "WITH" in complete_sql.upper(), (
        f"Generated content doesn't look like SQL: {complete_sql}"
    )


# Knowledge Embedding Search test
def test_knowledge_embedding_search(test_data):
    """Test searching knowledge by embedding vector"""
    # Generate a random embedding vector for testing
    # (In a real scenario, this would be generated by an embedding model)
    test_embedding = [random.uniform(-1, 1) for _ in range(768)]

    search_request = {
        "bizid": test_data["bizid"],
        "query_embedding": test_embedding,
        "top_k": 3,
        "min_score": 0.3,  # Lower threshold for testing
    }

    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/search_by_embedding", json=search_request
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


# Table Embedding Search test
def test_table_embedding_search(test_data):
    """Test searching tables by embedding."""
    # Create embedding for a test query
    query_embedding = [
        random.random() for _ in range(768)
    ]  # 768-dimensional random vector

    # Test table embedding search
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/search_by_embedding",
        json={
            "bizid": test_data["bizid"],
            "query_embedding": query_embedding,
            "top_k": 2,
            "min_score": 0.1,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_query_metadata(test_data):
    """Test retrieving query metadata including matched tables and alpha keys."""
    # Prepare test query
    test_query = "查询成都地区的工单满意度"

    # Test query metadata endpoint
    response = requests.post(
        f"{BASE_URL}/nl2sql/query_metadata",
        json={
            "bizid": test_data["bizid"],
            "query": test_query,
        },
    )

    # Verify response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "success"

    # Verify tables are returned
    assert "tables" in response_data
    assert isinstance(response_data["tables"], list)

    # Verify alpha keys are returned
    assert "alpha_keys" in response_data
    assert isinstance(response_data["alpha_keys"], list)

    # Since we used "工单满意度" in our query, and added this alpha key in the fixture,
    # we should find it in the response
    if response_data["alpha_keys"]:
        assert "工单满意度" in response_data["alpha_keys"], (
            "Expected alpha key not found in response"
        )

    # Verify that at least the test table is in the response
    if response_data["tables"]:
        table_ids = [table.get("table_id") for table in response_data["tables"]]
        assert test_data["test_table_id"] in table_ids, (
            "Test table not found in response"
        )


def test_table_batch_delete(test_data):
    """Test batch deletion of tables and related resources."""
    # 清理可能残留的测试数据
    try:
        for i in range(2):
            table_id = f"test_table_batch_{i}"
            # 尝试删除旧的表数据
            requests.post(
                f"{BASE_URL}/nl2sql/tableinfo/delete",
                json={"bizid": test_data["bizid"], "table_ids": [table_id]},
            )
        # 等待删除操作完成
        time.sleep(1)
        print("Cleared any existing test tables")
    except Exception as e:
        print(f"Error clearing old test data: {e}")

    # Create two tables
    tables = []
    for i in range(2):
        table_id = f"test_table_batch_{i}"
        tables.append(
            {
                "table_id": table_id,
                "table_name": f"test_table_{i}",
                "table_comment": f"Test table {i} for batch deletion",
                "fields": [
                    {
                        "field_id": f"field_{i}_1",
                        "name": f"field_{i}_1",
                        "datatype": "string",
                        "comment": f"Field {i}_1",
                    }
                ],
            }
        )

    # Create tables
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/create_or_update",
        json={"bizid": test_data["bizid"], "tables": tables},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Create knowledge entries for both tables
    knowledges = []
    for i in range(2):
        knowledges.append(
            {
                "knowledge_id": f"knowledge_{i}",
                "table_id": f"test_table_batch_{i}",
                "key_alpha": f"key_alpha_{i}",
                "key_beta": [f"key_beta_{i}"],
                "value": f"Test knowledge {i}",
            }
        )

    # Print knowledge objects for debugging
    print(f"Creating knowledge entries: {knowledges}")

    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/create_or_update",
        json={"bizid": test_data["bizid"], "knowledges": knowledges},
    )
    assert response.status_code == 200
    print(f"Knowledge creation response: {response.json()}")
    assert response.json()["status"] == "success"

    # 增加等待时间以确保索引刷新
    print("Waiting for knowledge entries to be indexed...")
    time.sleep(5)  # 增加到5秒

    # Create dimension values for both tables
    for i in range(2):
        response = requests.post(
            f"{BASE_URL}/nl2sql/dim_values/create_or_update",
            json={
                "bizid": test_data["bizid"],
                "table_id": f"test_table_batch_{i}",
                "field_id": f"field_{i}_1",
                "values": [{"value": f"dim_value_{i}"}],
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    # Verify tables, knowledge, and dimension values exist
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    tables_data = response.json()["tables"]
    batch_tables = [
        t for t in tables_data if t["table_id"].startswith("test_table_batch_")
    ]
    assert len(batch_tables) == 2

    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    # 添加调试输出
    knowledge_response = response.json()
    print(f"Knowledge list response: {knowledge_response}")

    # 确保响应中包含data字段
    if "data" not in knowledge_response:
        print("ERROR: 'data' field missing in knowledge response")
        print(f"Complete response: {knowledge_response}")
        assert False, "Missing 'data' field in knowledge response"

    batch_knowledge = [
        k
        for k in knowledge_response["data"]
        if k["table_id"].startswith("test_table_batch_")
    ]
    print(f"Filtered knowledge entries: {batch_knowledge}")
    # 如果长度不等于2，打印更详细的调试信息
    if len(batch_knowledge) != 2:
        print(f"Expected 2 knowledge entries, but found {len(batch_knowledge)}")
        print(f"All knowledge entries: {knowledge_response['data']}")
        print(f"Table IDs we're looking for: test_table_batch_0, test_table_batch_1")
    assert len(batch_knowledge) == 2

    # Test batch deletion
    table_ids = [f"test_table_batch_{i}" for i in range(2)]
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/delete",
        json={"bizid": test_data["bizid"], "table_ids": table_ids},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify tables are deleted
    response = requests.post(
        f"{BASE_URL}/nl2sql/tableinfo/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    tables_data = response.json()["tables"]
    batch_tables = [
        t for t in tables_data if t["table_id"].startswith("test_table_batch_")
    ]
    assert len(batch_tables) == 0

    # Verify knowledge entries are deleted
    response = requests.post(
        f"{BASE_URL}/nl2sql/knowledge/list", json={"bizid": test_data["bizid"]}
    )
    assert response.status_code == 200
    batch_knowledge = [
        k
        for k in response.json()["data"]
        if k["table_id"].startswith("test_table_batch_")
    ]
    assert len(batch_knowledge) == 0

    # Verify dimension values are deleted
    for i in range(2):
        response = requests.post(
            f"{BASE_URL}/nl2sql/dim_values/list",
            json={
                "bizid": test_data["bizid"],
                "table_id": f"test_table_batch_{i}",
                "field_id": f"field_{i}_1",
            },
        )
        assert response.status_code == 200
        assert len(response.json().get("values", [])) == 0

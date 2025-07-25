import requests

generate_request = {
    "bizid": "copilot",
    "query": "按省份编码，统计死亡人数",
    "stream": True,
    "settings": {"table_retrieve_threshold": "0.85", "enable_table_auth": True},
}

# When requesting a streaming response, use stream=True
response = requests.post(
    f"http://localhost:8001/nl2sql/generate", json=generate_request, stream=True
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
# assert len(collected_chunks) > 0, "No SQL chunks received in the stream"

# Combine chunks to form complete SQL
complete_sql = "".join(collected_chunks)

# Basic validation that it looks like SQL
assert "SELECT" in complete_sql.upper() or "WITH" in complete_sql.upper(), (
    f"Generated content doesn't look like SQL: {complete_sql}"
)
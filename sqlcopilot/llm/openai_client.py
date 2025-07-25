import httpx
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion
from restful.app.settings import config

url = config.llm.url
key = config.llm.key

# default_headers = {
#     "User-Agent": "SQLCopilot/1.0.0",
#     "X-Client-Version": "1.0.0"
# }
default_headers = {}

def get_headers_from_config():
    try:
        if hasattr(config.llm, 'headers'):
            headers_obj = config.llm.headers
            if hasattr(headers_obj, 'to_dict'):
                return headers_obj.to_dict()
            elif hasattr(headers_obj, '__dict__'):
                return headers_obj.__dict__
            else:
                return {}
        return {"userId": "-1"}
    except Exception:
        return {"userId": "-1"}

extra_headers = get_headers_from_config()

all_headers = {**default_headers, **extra_headers}

http_client = httpx.Client(headers=all_headers)

client = OpenAI(
    api_key=key, 
    base_url=url,
    http_client=http_client
)

model = (
    config.llm.model
    if config.llm.model
    else client.models.list().data[0].id
)


def generate(messages, stream=False) -> ChatCompletion:
    return client.chat.completions.create(
        messages=messages,
        model=model,
        stream=stream,
        temperature=0,
    )


if __name__ == "__main__":
    response = generate([{"role": "user", "content": "hello"}])
    print(response.choices[0].message.content)

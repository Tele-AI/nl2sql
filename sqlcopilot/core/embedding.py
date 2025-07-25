import json

import requests
from typing import Dict, List
from loguru import logger


class EmbeddingService:
    def __init__(self, config: Dict):
        if config.embedding.provider == "siliconflow":
            self._service = SiliconFlowEmbeddingService(
                url=config.embedding.url,
                token=config.embedding.siliconflow.token,
                model=config.embedding.siliconflow.model,
            )
        elif config.embedding.provider == "aiplatform-test-bge":
            self._service = CustomBgeService(url=config.embedding.url)
        elif config.embedding.provider == "datapilot-bge":
            self._service = CopilotBgeService(url=config.embedding.url)
        else:
            raise ValueError(
                f"Unsupported embedding service: {config.embedding.service}"
            )

    def get_embedding(self, text: str) -> List:
        return self._service.get_embedding(text)


class CustomBgeService:
    """开发测试环境，ai中台的推理服务"""

    def __init__(self, url: str):
        self.url = url

    def get_embedding(self, text: str) -> List:
        payload = {"sentences": [text]}

        try:
            resp = requests.post(self.url, json=payload)
            return resp.json()["embeddings"][0]
        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(f"Error traceback: {error_traceback}")
            resp = {}  # Initialize resp as empty dict in case it's not defined in the exception
            logger.error(f"Failed to connect to CustomBgeService: {str(e)}, {resp}")
            return None


class CopilotBgeService:
    """Copilot环境，部署的推理服务"""

    def __init__(self, url: str):
        self.url = url

    def get_embedding(self, text: str) -> List:
        payload = {"input": [text]}

        try:
            resp = requests.post(self.url, json=payload)
            return resp.json()["embedding"][0]
        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(f"Error traceback: {error_traceback}")
            resp = {}  # Initialize resp as empty dict in case it's not defined in the exception
            logger.error(f"Failed to connect to CopilotBgeService: {str(e)}, {resp}")
            return None


class SiliconFlowEmbeddingService:
    """Ref: https://docs.siliconflow.cn/cn/api-reference/embeddings/create-embeddings"""

    def __init__(self, url: str, token: str, model: str):
        self.url = url
        self.token = token
        self.model = model

    def get_embedding(self, text: str) -> List:
        payload = {"model": self.model, "input": text, "encoding_fomat": "float"}

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request("post", self.url, json=payload, headers=headers)
            resp = json.loads(response.text)
            return resp["data"][0]["embedding"]
        except Exception as e:
            import traceback

            error_traceback = traceback.format_exc()
            logger.error(f"Error traceback: {error_traceback}")
            resp = {}  # Initialize resp as empty dict in case it's not defined in the exception
            logger.error(
                f"Failed to connect to silicon flow embeddings service: {str(e)}, {resp}"
            )
            return None


if __name__ == "__main__":
    import sys
    from pathlib import Path

    current_dir = Path(__file__).parent
    parent_dir = str(current_dir.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    from restful.app.settings import config
    # Load the configuration

    try:
        # Initialize the embedding service
        embedding_service = EmbeddingService(config)

        # Test with sample text
        sample_text = (
            "This is a test sentence to check if the embedding service works properly."
        )
        result = embedding_service.get_embedding(sample_text)

        # Print the result
        print(f"Successfully retrieved embedding. Result type: {type(result)}")
        print(
            f"Result preview: {result[:100]}..." if isinstance(result, str) else result
        )
    except Exception as e:
        logger.error(f"Error while testing embedding service: {str(e)}")

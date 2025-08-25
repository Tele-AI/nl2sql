# 向量模型Provider接入文档

## 概述

NL2SQL项目支持多种向量模型服务提供商，通过统一的Provider接口进行接入。本文档详细说明了如何配置和使用不同的向量模型服务，以及如何扩展新的向量模型提供商。

## 支持的向量模型提供商

### 1. SiliconFlow Embedding Service

SiliconFlow是一个专业的向量模型服务提供商，支持多种预训练模型。

#### 配置方式

**配置文件方式** (`sqlcopilot/restful/app/settings/config.dev.yaml`):
```yaml
embedding:
  provider: "siliconflow"
  url: "https://api.siliconflow.cn/v1/embeddings"
  vector_dimension: 1024
  siliconflow:
    token: "your_api_token"
    model: "bge-large-zh-v1.5"
```

**环境变量方式**:
```bash
export EMBEDDING_PROVIDER=siliconflow
export EMBEDDING_URL=https://api.siliconflow.cn/v1/embeddings
export EMBEDDING_VECTOR_DIMENSION=1024
export EMBEDDING_SILICONFLOW_TOKEN=your_api_token
export EMBEDDING_SILICONFLOW_MODEL=bge-large-zh-v1.5
```

**Docker Compose方式**:
```yaml
environment:
  - EMBEDDING_PROVIDER=siliconflow
  - EMBEDDING_URL=https://api.siliconflow.cn/v1/embeddings
  - EMBEDDING_VECTOR_DIMENSION=1024
  - EMBEDDING_SILICONFLOW_TOKEN=your_api_token
  - EMBEDDING_SILICONFLOW_MODEL=bge-large-zh-v1.5
```

#### API接口规范

SiliconFlow使用标准的OpenAI兼容接口：

**请求格式**:
```json
{
  "model": "bge-large-zh-v1.5",
  "input": "要编码的文本",
  "encoding_fomat": "float"
}
```

**响应格式**:
```json
{
  "data": [
    {
      "embedding": [0.1, 0.2, 0.3, ...],
      "index": 0
    }
  ]
}
```

### 2. BGE服务

开源的BGE服务。

#### 配置方式

**配置文件方式**:
```yaml
embedding:
  provider: "datapilot-bge"
  url: "http://your-bge-server:8080/embed"
  vector_dimension: 1024
```

**环境变量方式**:
```bash
export EMBEDDING_PROVIDER=datapilot-bge
export EMBEDDING_URL=http://your-bge-server:8080/embed
export EMBEDDING_VECTOR_DIMENSION=1024
```

#### API接口规范

**请求格式**:
```json
{
  "input": ["要编码的文本"]
}
```

**响应格式**:
```json
{
  "embedding": [[0.1, 0.2, 0.3, ...]]
}
```


### 3. 自定义emb服务

用于开发测试环境的自定义BGE服务。

#### 配置方式

**配置文件方式**:
```yaml
embedding:
  provider: "your-emb"
  url: "http://your-emb-server:8080/embed"
  vector_dimension: 1024
```

**环境变量方式**:
```bash
export EMBEDDING_PROVIDER=your-emb
export EMBEDDING_URL=http://your-emb-server:8080/embed
export EMBEDDING_VECTOR_DIMENSION=1024
```

#### API接口规范

**请求格式**:
```json
{
  "sentences": ["要编码的文本"]
}
```

**响应格式**:
```json
{
  "embeddings": [[0.1, 0.2, 0.3, ...]]
}
```

## 向量维度配置

### 重要说明

向量维度配置是系统的重要参数，它决定了：

1. **Elasticsearch索引结构**：向量字段的维度必须与配置一致
2. **模型兼容性**：必须与所选向量模型的输出维度匹配
3. **性能影响**：维度越高，存储和计算成本越高

### 支持的维度

- **BGE-Large-ZH-V1.5**: 1024维
- **BGE-Base-ZH-V1.5**: 768维
- **BGE-Small-ZH-V1.5**: 512维

### 配置验证

系统启动时会验证向量维度配置：

1. 检查配置文件中的`vector_dimension`设置
2. 验证与所选模型的输出维度是否一致
3. 确保Elasticsearch索引的向量字段维度匹配

## 扩展新的向量模型提供商

### 步骤1：创建新的服务类

在`sqlcopilot/core/embedding.py`中添加新的服务类：

```python
class YourCustomEmbeddingService:
    """您的自定义向量模型服务"""
    
    def __init__(self, url: str, api_key: str = None, **kwargs):
        self.url = url
        self.api_key = api_key
        # 其他初始化参数
        
    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示
        
        Args:
            text: 要编码的文本
            
        Returns:
            List[float]: 向量表示
        """
        payload = {
            "text": text,
            # 其他请求参数
        }
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["Content-Type"] = "application/json"
        
        try:
            response = requests.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 根据您的API响应格式解析向量
            return result["embedding"]
            
        except Exception as e:
            logger.error(f"Failed to get embedding from YourCustomService: {str(e)}")
            return None
```

### 步骤2：更新EmbeddingService类

在`EmbeddingService.__init__`方法中添加新的条件分支：

```python
class EmbeddingService:
    def __init__(self, config: Dict):
        if config.embedding.provider == "your-custom-provider":
            self._service = YourCustomEmbeddingService(
                url=config.embedding.url,
                api_key=config.embedding.your_custom.api_key,
                # 其他参数
            )
        elif config.embedding.provider == "siliconflow":
            # 现有代码...
        # 其他现有条件...
        else:
            raise ValueError(f"Unsupported embedding service: {config.embedding.provider}")
```

### 步骤3：更新配置文件

在`sqlcopilot/restful/app/settings/config.dev.yaml`中添加新提供商的配置：

```yaml
embedding:
  provider: "your-custom-provider"
  url: "https://your-api-endpoint.com/embed"
  vector_dimension: 1024
  
  your_custom:
    api_key: "your_api_key"
    # 其他配置参数
```

### 步骤4：添加环境变量支持

在配置加载逻辑中添加环境变量支持：

```python
# 在配置加载代码中添加
your_custom_api_key = os.getenv("EMBEDDING_YOUR_CUSTOM_API_KEY")
```

## 最佳实践

### 1. 错误处理

所有向量服务类都应该包含完善的错误处理：

```python
try:
    response = requests.post(self.url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()["embedding"]
except requests.exceptions.Timeout:
    logger.error("Embedding service timeout")
    return None
except requests.exceptions.RequestException as e:
    logger.error(f"Embedding service request failed: {str(e)}")
    return None
except Exception as e:
    logger.error(f"Unexpected error in embedding service: {str(e)}")
    return None
```

### 2. 性能优化

- 使用连接池复用HTTP连接
- 设置合理的超时时间
- 考虑添加重试机制
- 使用异步请求（如适用）

### 3. 监控和日志

- 记录请求响应时间
- 监控错误率
- 记录向量维度信息
- 添加健康检查接口

### 4. 安全性

- 使用HTTPS进行API调用
- 安全存储API密钥
- 实现请求频率限制
- 添加输入验证

## 故障排除

### 常见问题

1. **向量维度不匹配**
   - 错误：`Vector dimension mismatch`
   - 解决：检查配置文件中的`vector_dimension`设置

2. **API连接失败**
   - 错误：`Failed to connect to embedding service`
   - 解决：检查网络连接和API端点配置

3. **认证失败**
   - 错误：`Authentication failed`
   - 解决：验证API密钥和认证信息

4. **响应格式错误**
   - 错误：`Invalid response format`
   - 解决：检查API响应格式是否符合预期

### 调试工具

使用内置的测试脚本验证配置：

```bash
cd sqlcopilot/core
python embedding.py
```

这将测试当前配置的向量服务是否正常工作。

## 版本兼容性

### 当前版本支持

- **SiliconFlow**: 最新版本
- **BGE模型**: v1.5及以上版本
- **Python**: 3.12+
- **Requests**: 2.31+

### 向后兼容性

- 配置文件格式向后兼容
- API接口保持稳定
- 新增提供商不影响现有功能

## 更新日志

### v1.0.0 (2025-01-XX)
- 初始版本
- 支持SiliconFlow、AI平台测试环境、Copilot环境三种提供商
- 统一的Provider接口设计
- 完整的配置和错误处理机制

---

**注意**：本文档会随着新功能的添加而更新，请定期查看最新版本。

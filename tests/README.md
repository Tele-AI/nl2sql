# NL2SQL API 自动化测试

这个目录包含了针对NL2SQL API端点的自动化测试。测试遵循CRUD模式（创建、读取、更新、删除）对每种API资源类型进行测试。

## 文件结构

- `test_nl2sql_api.py`: 包含所有API端点的测试用例
- `run_api_tests.py`: 运行测试的Python脚本
- `run_tests.sh`: 运行测试的Shell脚本
- `config.py`: 测试配置文件，包含默认设置和环境配置
- `__init__.py`: 使tests目录成为Python包的文件
- `README.md`: 本文档，包含测试说明和使用方法

## 要求

- Python 3.7+
- `requests` 库
- 运行中的 NL2SQL API 服务器

## 如何运行测试

1. 确保 NL2SQL API 服务器已经启动
2. 使用以下任一方式运行测试:

### 使用Shell脚本运行测试

```bash
# 在项目根目录运行
./tests/run_tests.sh

# 或者在tests目录内运行
cd tests
./run_tests.sh
```

## 测试流程

每个测试遵循类似的模式:

1. 准备: 创建一个唯一的业务域用于测试隔离
2. 测试特定资源的操作:
   - 创建资源
   - 更新资源
   - 列出/获取资源
   - 删除资源
   - 验证删除
3. 清理: 删除测试业务域进行清理

## 添加新测试

要添加新的测试:

1. 在`test_nl2sql_api.py`文件的`NL2SQLAPITests`类中添加新的测试方法
2. 遵循现有测试中建立的CRUD模式
3. 使用唯一标识符作为测试资源，避免冲突

## 测试环境配置

测试支持多种环境配置，这些配置定义在`config.py`文件中：

- `development`: 本地开发环境
- `staging`: 预发布环境
- `production`: 生产环境

您可以通过`--env`参数选择使用哪个环境：

```bash
./tests/run_tests.sh --env=staging
```

或者自定义主机和端口：

```bash
./tests/run_tests.sh --host=custom-api.example.com --port=9000
```

## 故障排除

如果测试失败，请检查:

1. API服务器是否正在运行且可访问
2. API端点是否与测试预期匹配
3. 是否有创建和删除资源的必要权限

## 依赖关系

测试按以下顺序创建具有依赖关系的资源:

1. 业务域
2. 表信息
3. 其他资源（知识、SQL案例等）

这种结构确保测试可以独立运行，并且不会互相冲突。 
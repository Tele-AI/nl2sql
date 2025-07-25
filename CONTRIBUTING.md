# 贡献指南

感谢您对 SQL Copilot 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 报告问题和提出建议
- 修复 bug
- 添加新功能
- 改进文档
- 优化性能

## 开始之前

1. Fork 本项目到您的 GitHub 账号
2. Clone 您 fork 的仓库到本地
3. 创建一个新的分支进行开发

```bash
git clone https://github.com/yourusername/sqlcopilot.git
cd sqlcopilot
git checkout -b feature/your-feature-name
```

## 开发环境设置

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r sqlcopilot/restful/requirements.txt
```

### 2. 配置开发环境

复制环境配置示例文件并根据需要修改：

```bash
cp .env.example .env
```

### 3. 启动依赖服务

使用 Docker Compose 启动 Elasticsearch：

```bash
docker-compose up -d elasticsearch
```

## 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 对导入进行排序
- 函数和类需要添加文档字符串

```bash
# 格式化代码
black sqlcopilot/
isort sqlcopilot/
```

### 提交信息规范

请使用语义化的提交信息：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码风格调整（不影响功能）
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

示例：
```
feat: 添加多表联合查询支持
fix: 修复时间转换 Agent 的边界条件问题
docs: 更新 API 文档示例
```

## 提交 Pull Request

### 1. 确保代码质量

在提交 PR 之前，请确保：

- [ ] 代码通过所有测试
- [ ] 代码符合项目的编码规范
- [ ] 新功能有相应的测试覆盖
- [ ] 文档已更新（如果需要）

### 2. 运行测试

```bash
# 运行单元测试
pytest tests/

# 运行代码检查
flake8 sqlcopilot/
mypy sqlcopilot/
```

### 3. 创建 Pull Request

1. 推送您的分支到 GitHub
2. 在 GitHub 上创建 Pull Request
3. 填写 PR 模板，说明：
   - 修改的内容
   - 解决的问题
   - 测试方法

### 4. PR 审核流程

- 维护者会尽快审核您的 PR
- 可能会要求您进行一些修改
- 通过审核后，PR 会被合并到主分支

## 报告问题

如果您发现 bug 或有功能建议，请：

1. 先搜索是否已有相关 issue
2. 如果没有，创建新的 issue
3. 使用 issue 模板提供详细信息：
   - 问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息

## 功能请求

欢迎提出新功能建议！请在 issue 中说明：

- 功能描述
- 使用场景
- 可能的实现方案

## 文档贡献

文档同样重要！您可以：

- 修正错别字和语法错误
- 改进示例代码
- 添加更多使用案例
- 翻译文档到其他语言

## 社区行为准则

请遵守以下准则：

- 尊重所有贡献者
- 使用友善和包容的语言
- 接受建设性的批评
- 关注项目和社区的最佳利益

## 获取帮助

如果您在贡献过程中遇到问题：

- 查看项目文档
- 在 issue 中提问
- 联系项目维护者

## 致谢

再次感谢您的贡献！每一份贡献都让 SQL Copilot 变得更好。
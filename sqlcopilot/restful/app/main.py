import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from loguru import logger

from settings import config

logger.info(config)

# add parent path
for i in range(3):
    sys.path.append(str(Path(__file__).resolve().parents[i]))

from routers import nl2sql

# 创建FastAPI应用，添加文档配置
app = FastAPI(
    title="SQL Copilot API",
    description="SQL Copilot API for natural language to SQL conversion",
    version="1.0.0",
    docs_url=None,  # 禁用默认的/docs路径
    redoc_url=None,  # 禁用默认的/redoc路径
)

# 包含路由
app.include_router(nl2sql.router)

# swagger挂载静态文件目录
current_dir = Path(__file__).parent
static_dir = current_dir / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 自定义/docs路径，使用我们自己的Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon-32x32.png",
    )
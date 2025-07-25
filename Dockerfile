FROM python:3.12

WORKDIR /app

ENV PIP_SOURCE="https://pypi.tuna.tsinghua.edu.cn/simple"

RUN pip install uv -i ${PIP_SOURCE}

COPY ./sqlcopilot/restful/requirements.txt /app/requirements.txt

RUN uv pip install --no-cache-dir --upgrade -r /app/requirements.txt -i ${PIP_SOURCE} --system

COPY . /app

WORKDIR /app/sqlcopilot/restful

CMD ["fastapi", "run", "app/main.py", "--port", "80"]
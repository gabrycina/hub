FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY hub ./hub
COPY hub_mcp ./hub_mcp

RUN pip install --no-cache-dir .

ENV HUB_HOST=127.0.0.1
ENV HUB_PORT=8080
ENV HUB_DATA_DIR=/data

EXPOSE 8080
CMD ["hub", "run"]
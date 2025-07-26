#!/bin/bash

# 启动FastAPI服务器，配置适当的超时参数来处理长时间运行的请求
echo "启动API服务器，配置超时参数..."

# 临时禁用代理，避免网络连接问题
export http_proxy=""
export https_proxy=""
export HTTP_PROXY=""
export HTTPS_PROXY=""
export no_proxy="localhost,127.0.0.1"
export NO_PROXY="localhost,127.0.0.1"

echo "已禁用代理设置，避免网络连接问题..."

uvicorn api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --timeout-keep-alive 600 \
    --timeout-graceful-shutdown 600 \
    --workers 1 \
    --log-level debug \
    --access-log \
    --use-colors

echo "服务器已停止" 
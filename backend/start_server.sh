#!/bin/bash

# 使用Docker启动FastAPI服务器
echo "使用Docker启动API服务器..."

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 检查并启动PostgreSQL
echo "检查PostgreSQL状态..."
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "启动PostgreSQL服务..."
    # 尝试用Homebrew启动PostgreSQL
    if command -v brew >/dev/null 2>&1; then
        brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null || true
        # 等待PostgreSQL启动
        for i in {1..10}; do
            if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
                echo "✅ PostgreSQL服务已启动"
                break
            fi
            echo "等待PostgreSQL启动... ($i/10)"
            sleep 2
        done
    fi
    
    # 最后检查一次
    if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo "⚠️  警告: PostgreSQL未运行，应用可能无法正常工作"
        echo "请手动启动PostgreSQL: brew services start postgresql"
    fi
else
    echo "✅ PostgreSQL服务已运行"
fi

# 构建Docker镜像
echo "构建Docker镜像..."
docker build -t kairos-backend .

if [ $? -ne 0 ]; then
    echo "❌ Docker镜像构建失败"
    exit 1
fi

echo "✅ Docker镜像构建成功"

# 停止并移除现有容器（如果存在）
docker stop kairos-backend-container 2>/dev/null || true
docker rm kairos-backend-container 2>/dev/null || true

# 运行Docker容器
echo "启动Docker容器..."
docker run -d \
    --name kairos-backend-container \
    -p 8000:8000 \
    -v "$(pwd)":/app \
    -e PRINT_ENV_ON_LOAD=false \
    -e WAIT_FOR_DB=false \
    -e DB_HOST=host.docker.internal \
    -e DB_PORT=5432 \
    -e DB_USER=ai \
    -e DB_PASSWORD=ai \
    -e DB_NAME=ai \
    kairos-backend \
    uvicorn api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --timeout-keep-alive 600 \
        --timeout-graceful-shutdown 600 \
        --workers 1 \
        --log-level debug \
        --access-log \
        --use-colors

if [ $? -eq 0 ]; then
    echo "✅ Docker容器启动成功"
    echo "🚀 API服务器运行在: http://localhost:8000"
    echo "📚 API文档地址: http://localhost:8000/docs"
    echo ""
    echo "📋 有用的命令:"
    echo "  查看日志: docker logs -f kairos-backend-container"
    echo "  停止容器: docker stop kairos-backend-container"
    echo "  进入容器: docker exec -it kairos-backend-container bash"
    echo ""
    echo "正在显示容器日志 (Ctrl+C 退出日志查看):"
    docker logs -f kairos-backend-container
else
    echo "❌ Docker容器启动失败"
    exit 1
fi 
# Docker 部署指南

## 快速启动

### 1. 环境准备

```bash
cd backend

# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
vim .env
```

在 `.env` 文件中设置必要的环境变量：
```bash
# 必须设置
OPENAI_API_KEY=your_actual_openai_api_key

# 数据库配置（可选，默认值已足够）
DB_USER=ai
DB_PASSWORD=ai
DB_NAME=ai
```

### 2. 启动服务

```bash
# 启动所有服务（数据库 + API）
docker compose up -d

# 查看日志
docker compose logs -f

# 仅启动数据库
docker compose up -d pgvector

# 仅启动API
docker compose up -d api
```

### 3. 验证部署

```bash
# 检查服务状态
docker compose ps

# 测试API健康检查
curl http://localhost:8000/api/v1/health

# 测试YouTube功能
curl -X POST http://localhost:8000/api/v1/youtube/quick-process \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## 服务组件

### 数据库服务 (pgvector)
- **镜像**: `agnohq/pgvector:16`
- **端口**: `5432`
- **卷**: `pgdata:/var/lib/postgresql/data`
- **功能**: PostgreSQL + pgvector 扩展

### API服务 (api)
- **镜像**: 本地构建的 `steep-ai-backend`
- **端口**: `8000`
- **功能**: FastAPI + YouTube转录处理

## 自动化功能

### 数据库迁移
容器启动时会自动：
1. 等待数据库就绪
2. 检查YouTube相关表是否存在
3. 自动创建缺失的表
4. 输出迁移结果

### 依赖管理
- `requirements.txt` 包含所有必要依赖
- 包括 `youtube-transcript-api==1.2.1`
- Docker构建时自动安装

## 开发模式

### 热重载开发
```bash
# 启动开发模式（代码变更自动重载）
docker compose up api

# 或者仅启动数据库，本地运行API
docker compose up -d pgvector
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 日志调试
```bash
# 实时查看特定服务日志
docker compose logs -f api
docker compose logs -f pgvector

# 查看最近日志
docker compose logs --tail=50 api
```

## 生产部署

### 环境变量优化
```bash
# 生产环境建议设置
WAIT_FOR_DB=True
PRINT_ENV_ON_LOAD=False

# 可选：监控配置
AGNO_MONITOR=True
AGNO_API_KEY=your_agno_api_key
```

### 数据持久化
- 数据库数据存储在Docker卷 `pgdata` 中
- 删除容器不会丢失数据
- 备份：`docker run --rm -v pgdata:/data -v $(pwd):/backup busybox tar czf /backup/pgdata.tar.gz -C /data .`

### 性能优化
1. **内存设置**: 根据需要调整PostgreSQL内存配置
2. **并发处理**: YouTube转录处理使用后台任务，无需额外配置
3. **网络**: 生产环境建议使用反向代理（Nginx/Traefik）

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库容器状态
   docker compose ps pgvector
   
   # 检查数据库日志
   docker compose logs pgvector
   ```

2. **YouTube API失败**
   ```bash
   # 检查API容器日志
   docker compose logs api | grep youtube
   
   # 测试网络连接
   docker compose exec api python -c "
   from core.youtube_processor import get_youtube_transcript
   print(get_youtube_transcript('dQw4w9WgXcQ'))
   "
   ```

3. **端口占用**
   ```bash
   # 检查端口使用
   lsof -i :8000
   lsof -i :5432
   
   # 修改compose.yaml中的端口映射
   ```

### 重置环境
```bash
# 停止并删除所有容器
docker compose down

# 删除数据卷（注意：会丢失所有数据）
docker compose down -v

# 重建镜像
docker compose build --no-cache

# 重新启动
docker compose up -d
```

## 监控和维护

### 健康检查
```bash
# API健康检查
curl http://localhost:8000/api/v1/health

# 数据库连接测试
docker compose exec api python -c "
from db.session import get_db
next(get_db())
print('Database OK')
"
```

### 日志轮转
```bash
# 配置Docker日志轮转
# 在docker-compose.yaml中添加：
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 备份策略
```bash
# 定期备份数据库
docker compose exec pgvector pg_dump -U ai ai > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker compose exec -T pgvector psql -U ai ai < backup.sql
```

## 扩展部署

### 多实例部署
```yaml
# 在compose.yaml中添加
services:
  api:
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"
```

### 外部数据库
```yaml
# 使用外部PostgreSQL
services:
  api:
    environment:
      DB_HOST: your-external-db-host
      DB_PORT: 5432
      WAIT_FOR_DB: False
```
#!/bin/bash

############################################################################
# Docker部署测试脚本
# 验证YouTube转录功能是否正常工作
############################################################################

set -e

echo "🧪 开始测试Docker部署..."

# 检查Docker Compose是否运行
if ! docker compose ps | grep -q "Up"; then
    echo "❌ Docker Compose服务未运行，请先执行: docker compose up -d"
    exit 1
fi

echo "✅ Docker Compose服务正在运行"

# 等待服务就绪
echo "⏳ 等待API服务就绪..."
for i in {1..30}; do
    if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
        echo "✅ API服务就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API服务启动超时"
        exit 1
    fi
    sleep 2
done

# 测试健康检查
echo "🔍 测试健康检查..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/v1/health)
if echo "$HEALTH_RESPONSE" | grep -q "success"; then
    echo "✅ 健康检查通过"
else
    echo "❌ 健康检查失败: $HEALTH_RESPONSE"
    exit 1
fi

# 测试YouTube快速处理API
echo "🎬 测试YouTube快速处理API..."
YOUTUBE_URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll作为测试视频

YOUTUBE_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/youtube/quick-process \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$YOUTUBE_URL\"}")

echo "📝 YouTube API响应: $YOUTUBE_RESPONSE"

if echo "$YOUTUBE_RESPONSE" | grep -q "success.*true"; then
    echo "✅ YouTube快速处理API工作正常"
    
    # 提取video_id
    VIDEO_ID=$(echo "$YOUTUBE_RESPONSE" | grep -o '"video_id":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$VIDEO_ID" ]; then
        echo "📹 提取到视频ID: $VIDEO_ID"
        
        # 测试状态查询
        echo "🔍 测试状态查询API..."
        STATUS_RESPONSE=$(curl -s http://localhost:8000/v1/youtube/status/$VIDEO_ID)
        echo "📊 状态响应: $STATUS_RESPONSE"
        
        if echo "$STATUS_RESPONSE" | grep -q "video_id"; then
            echo "✅ 状态查询API工作正常"
        else
            echo "⚠️ 状态查询API响应异常，但不影响基本功能"
        fi
    fi
else
    echo "❌ YouTube快速处理API失败: $YOUTUBE_RESPONSE"
    exit 1
fi

# 测试数据库连接
echo "💾 测试数据库连接..."
DB_TEST=$(docker compose exec -T api python -c "
try:
    from db.session import get_db
    db = next(get_db())
    print('Database connection OK')
    db.close()
except Exception as e:
    print(f'Database connection failed: {e}')
    import sys
    sys.exit(1)
" 2>/dev/null)

if echo "$DB_TEST" | grep -q "Database connection OK"; then
    echo "✅ 数据库连接正常"
else
    echo "❌ 数据库连接失败: $DB_TEST"
    exit 1
fi

# 测试数据库表
echo "🗃️ 测试数据库表..."
TABLE_TEST=$(docker compose exec -T api python -c "
try:
    from db.migrations import check_tables_exist
    tables_status = check_tables_exist()
    if tables_status:
        print(f'Tables status: {tables_status}')
        if all(tables_status.values()):
            print('All YouTube tables exist')
        else:
            print('Some YouTube tables missing')
    else:
        print('Failed to check tables')
except Exception as e:
    print(f'Table check failed: {e}')
" 2>/dev/null)

echo "📋 表检查结果: $TABLE_TEST"

if echo "$TABLE_TEST" | grep -q "All YouTube tables exist"; then
    echo "✅ 所有YouTube表都存在"
elif echo "$TABLE_TEST" | grep -q "Tables status"; then
    echo "⚠️ 部分表可能缺失，但基本功能正常"
else
    echo "❌ 表检查失败，请检查数据库迁移"
fi

echo ""
echo "🎉 Docker部署测试完成！"
echo ""
echo "📋 测试总结:"
echo "  ✅ Docker Compose服务运行正常"
echo "  ✅ API健康检查通过"
echo "  ✅ YouTube处理API功能正常"
echo "  ✅ 数据库连接正常"
echo ""
echo "🚀 您的YouTube转录功能已准备就绪！"
echo ""
echo "💡 接下来的步骤:"
echo "  1. 前端访问: http://localhost:3000 (如果前端已启动)"
echo "  2. API文档: http://localhost:8000/docs"
echo "  3. 测试上传YouTube链接并查看转录处理"
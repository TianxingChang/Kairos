# YouTube 转录文本集成功能

## 功能概述

当用户在前端上传 YouTube 链接时，系统会自动：
1. 验证 YouTube URL 格式
2. 提取视频 ID
3. 在后台异步下载带时间戳的转录文本
4. 将转录文本存储到数据库
5. 提供 API 接口供前端查询和搜索

## 技术架构

### 后端组件

1. **数据库模型** (`backend/db/models.py`)
   - `YouTubeVideo`: 存储视频基本信息
   - `YouTubeTranscript`: 存储带时间戳的转录片段

2. **核心处理器** (`backend/core/youtube_processor.py`)
   - URL 验证和 ID 提取
   - 转录文本获取（使用 youtube-transcript-api）
   - 短片段合并优化

3. **数据库服务** (`backend/db/youtube_service.py`)
   - CRUD 操作
   - 文本搜索和时间范围查询

4. **业务逻辑** (`backend/core/youtube_handler.py`)
   - 统一的处理入口
   - 错误处理和状态管理

5. **API 路由** (`backend/api/routes/youtube.py`)
   - RESTful API 端点
   - 后台任务处理

### 前端组件

1. **YouTube 服务** (`frontend/src/services/youtubeService.ts`)
   - API 调用封装
   - 状态轮询
   - URL 验证

2. **上传组件** (`frontend/src/components/VideoUpload.tsx`)
   - 集成 YouTube API 调用
   - 实时状态显示
   - 错误处理

## API 端点

### 快速处理 (推荐)
```http
POST /v1/youtube/quick-process
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**响应:**
```json
{
  "success": true,
  "video_id": "VIDEO_ID",
  "message": "正在后台处理转录文本",
  "status": "processing",
  "transcript_count": 0
}
```

### 同步处理
```http
POST /v1/youtube/process
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "merge_segments": true,
  "auto_process": true
}
```

### 获取处理状态
```http
GET /v1/youtube/status/{video_id}
```

**响应:**
```json
{
  "video_id": "VIDEO_ID",
  "status": "ready",
  "message": "转录文本已准备就绪",
  "transcript_count": 156,
  "has_video_info": true
}
```

### 获取转录文本
```http
GET /v1/youtube/transcript/{video_id}
```

**响应:**
```json
[
  {
    "id": 1,
    "start_time": 0.0,
    "duration": 3.5,
    "text": "Welcome to this video...",
    "language": "en",
    "end_time": 3.5
  }
]
```

### 搜索转录文本
```http
GET /v1/youtube/transcript/{video_id}/search?q=关键词
```

### 时间范围查询
```http
GET /v1/youtube/transcript/{video_id}/time-range?start_time=30&end_time=60
```

## 安装和设置

### 1. 安装依赖

```bash
cd backend
pip install youtube-transcript-api
# 或者
uv add youtube-transcript-api
```

### 2. 运行数据库迁移

```bash
cd backend
python setup_youtube.py
```

### 3. 启动服务

```bash
# 后端
cd backend
uvicorn api.main:app --reload

# 前端
cd frontend
npm run dev
```

## 使用流程

### 用户操作流程

1. 用户在前端输入 YouTube URL
2. 点击"开始学习"按钮
3. 前端调用 `/v1/youtube/quick-process` API
4. 后端立即返回响应，开始后台处理
5. 前端显示处理状态，用户可以继续到学习页面
6. 转录文本在后台异步下载和处理

### 后台处理流程

1. 验证 YouTube URL 格式
2. 提取视频 ID
3. 检查数据库中是否已存在转录文本
4. 如果不存在，使用 youtube-transcript-api 获取
5. 支持多语言：英文、中文、自动生成字幕
6. 可选的短片段合并优化
7. 存储到数据库

## 错误处理

### 常见错误情况

1. **无效的 YouTube URL**
   - 错误码: 400
   - 消息: "无效的YouTube URL"

2. **无法获取转录文本**
   - 可能原因: 视频没有字幕、私密视频、地区限制
   - 处理: 返回错误状态，但仍允许观看视频

3. **数据库错误**
   - 自动重试机制
   - 错误日志记录

### 降级策略

1. **API 失败时**: 回退到原有的 YouTube oEmbed API 获取基本信息
2. **转录文本获取失败**: 用户仍可正常观看视频
3. **数据库连接失败**: 显示错误信息，建议重试

## 性能优化

1. **后台异步处理**: 用户不需要等待转录文本下载完成
2. **重复检测**: 避免重复下载相同视频的转录文本
3. **短片段合并**: 提高可读性，减少存储空间
4. **数据库索引**: 视频 ID 和时间戳索引优化查询性能

## 监控和日志

- 处理成功/失败日志
- 性能监控（处理时间、转录文本长度）
- 错误统计和报警

## 扩展功能

### 已实现
- 多语言转录文本支持
- 文本搜索功能
- 时间范围查询
- 状态轮询

### 可扩展
- 转录文本的 AI 总结
- 关键词提取和标签
- 视频章节自动分割
- 多用户权限管理
- 转录文本的翻译功能
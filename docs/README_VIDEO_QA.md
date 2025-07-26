# 视频问答功能使用指南

本文档介绍如何使用视频时间点问答功能，包括前后端的完整实现。

## 功能概述

视频问答功能允许用户：
1. 上传YouTube视频并自动处理转录文本
2. 针对视频中的特定时间点提出问题
3. 获得基于视频内容的AI智能回答
4. 查看相关的转录文本上下文

## 架构设计

### 后端结构
```
backend/
├── agents/
│   ├── video_qa_agent.py          # 视频问答Agent实现
│   └── full_video_qa_agent.py     # 完整视频问答Agent
├── api/routes/
│   ├── frontend_video_qa.py       # 前端视频问答API
│   ├── frontend_youtube.py        # 前端YouTube API
│   ├── video_qa.py               # 基础视频问答API
│   └── youtube.py                # YouTube处理API
├── db/
│   ├── models.py                 # 数据库模型
│   ├── youtube_service.py        # YouTube服务
│   └── session.py               # 数据库会话
└── test_video_qa.py             # API测试脚本
```

### 前端结构
```
frontend/src/
├── components/
│   └── VideoQAPanel.tsx          # 视频问答面板组件
├── services/
│   └── videoQAService.ts         # 视频问答服务
├── config/
│   └── api.ts                   # API配置
└── app/
    └── video-qa-test/
        └── page.tsx             # 测试页面
```

## API 端点

### 视频问答 API

#### POST `/v1/frontend/video-qa/ask`
针对视频特定时间点提问

**请求参数:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "timestamp": 30.0,
  "question": "这个时间点在说什么？",
  "user_id": "frontend_user",
  "context_before": 20,
  "context_after": 5
}
```

**响应格式:**
```json
{
  "success": true,
  "answer": "AI生成的回答",
  "context_transcript": "时间点附近的转录文本",
  "timestamp_info": {
    "target_time": 30.0,
    "target_formatted": "00:30",
    "context_start": 10.0,
    "context_end": 35.0,
    "context_duration": 25.0
  },
  "video_info": {
    "video_id": "dQw4w9WgXcQ",
    "title": "视频标题",
    "duration": 212,
    "channel": "频道名称"
  }
}
```

#### GET `/v1/frontend/video-qa/context/{video_id}`
获取视频时间点上下文

**查询参数:**
- `timestamp`: 时间戳 (支持 "1:23" 或 "83" 格式)
- `before`: 前向上下文秒数 (默认: 20)
- `after`: 后向上下文秒数 (默认: 5)

#### GET `/v1/frontend/video-qa/video-status/{video_id}`
检查视频处理状态

**响应格式:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "has_video_info": true,
  "has_transcript": true,
  "ready_for_qa": true,
  "video_info": {
    "title": "视频标题",
    "duration": 212,
    "channel": "频道名称",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "transcript_info": {
    "segment_count": 150,
    "language": "en",
    "file_size": 12345
  }
}
```

### YouTube 上传 API

#### POST `/v1/frontend/youtube/upload`
上传并处理YouTube视频

**请求参数:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "user_id": "frontend_user"
}
```

**响应格式:**
```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "message": "视频已提交后台处理",
  "status": "processing",
  "video_info": {
    "video_id": "dQw4w9WgXcQ",
    "title": "视频标题",
    "duration": 212,
    "channel": "频道名称"
  }
}
```

#### GET `/v1/frontend/youtube/status/{video_id}`
获取YouTube视频处理状态

## 使用步骤

### 1. 启动服务

**后端服务:**
```bash
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

**前端服务:**
```bash
cd frontend
npm run dev
```

### 2. 测试功能

访问测试页面: http://localhost:3000/video-qa-test

或者使用测试脚本:
```bash
cd backend
python test_video_qa.py
```

### 3. 使用流程

1. **上传视频**: 
   - 输入YouTube链接
   - 等待视频处理完成

2. **提出问题**:
   - 输入视频ID (例如: dQw4w9WgXcQ)
   - 输入时间点 (例如: 1:23 或 83)
   - 输入问题 (例如: "这个时间点在说什么?")

3. **获得回答**:
   - AI会基于时间点附近的转录文本回答问题
   - 可以查看相关的转录上下文
   - 可以将回答插入到笔记中

## 配置说明

### 环境变量
```bash
# OpenAI API配置
OPENAI_API_KEY=your_api_key_here

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/dbname

# 文件存储配置
TRANSCRIPT_STORAGE_PATH=./data/transcripts
```

### 模型配置
- 默认使用 `gpt-4o` 模型
- 可在Agent配置中修改模型ID
- 支持上下文长度控制 (最大20000字符)

## 故障排除

### 常见问题

1. **连接失败**
   - 检查后端服务是否运行在 http://localhost:8000
   - 检查数据库连接是否正常

2. **视频处理失败**
   - 确认YouTube URL格式正确
   - 检查是否有网络访问权限
   - 查看后端日志获取详细错误信息

3. **问答失败**
   - 确认OpenAI API密钥配置正确
   - 检查视频是否已完成转录处理
   - 确认时间戳格式正确

### 调试工具

1. **API测试脚本**: `backend/test_video_qa.py`
2. **前端测试页面**: http://localhost:3000/video-qa-test
3. **健康检查**: http://localhost:8000/v1/health

## 开发指南

### 扩展功能

1. **添加新的问答模式**:
   - 在 `agents/` 目录下创建新的Agent
   - 在 `api/routes/` 下添加对应的API端点

2. **自定义转录处理**:
   - 修改 `db/youtube_service.py` 中的处理逻辑
   - 添加新的转录格式支持

3. **前端界面定制**:
   - 修改 `components/VideoQAPanel.tsx` 组件
   - 添加新的UI功能和交互

### 代码结构
- **Agent层**: 处理AI逻辑和对话管理
- **API层**: 提供RESTful接口
- **服务层**: 处理业务逻辑
- **数据层**: 管理数据库和文件存储

## 更新日志

### v1.0.0 (当前版本)
- ✅ 基础视频时间点问答功能
- ✅ YouTube视频自动处理
- ✅ 前端交互界面
- ✅ API测试工具
- ✅ 完整的错误处理

### 计划功能
- 🔄 视频全文问答
- 🔄 多语言转录支持
- 🔄 批量视频处理
- 🔄 高级搜索功能
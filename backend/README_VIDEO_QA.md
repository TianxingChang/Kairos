# 🎥 视频时间点问答系统

## 功能概述

这是一个基于YouTube视频转录文本的智能问答系统，能够根据用户指定的时间点提供精准的内容分析和回答。

## 核心特性

### ✅ 已实现功能

1. **YouTube 视频处理**
   - 自动下载视频转录文本
   - 文件存储架构（JSON格式）
   - 支持多语言转录

2. **时间点上下文提取**
   - 目标时间点前20秒、后5秒的内容
   - 智能片段筛选和合并
   - 时间戳格式化显示

3. **AI智能问答**
   - 基于GPT-4的内容分析
   - 上下文感知的回答生成
   - 支持中英文问答

4. **前端集成接口**
   - RESTful API设计
   - 完整的错误处理
   - 实时状态查询

## API 接口

### 1. YouTube 视频处理

#### 上传并处理视频
```bash
POST /v1/frontend/youtube/upload
```
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "user_id": "frontend_user"
}
```

#### 检查视频状态
```bash
GET /v1/frontend/youtube/status/{video_id}
```

### 2. 视频问答

#### 智能问答（推荐）
```bash
POST /v1/frontend/ask
```
```json
{
  "video_id": "dQw4w9WgXcQ",
  "timestamp": 30,
  "question": "这个时间点在说什么？",
  "user_id": "frontend_user"
}
```

#### 获取上下文转录
```bash
GET /v1/frontend/context/{video_id}?timestamp=1:23&before=20&after=5
```

### 3. 辅助工具

#### 时间戳解析
```bash
GET /v1/frontend/parse-timestamp?timestamp=1:23
```

## 前端演示

访问 `http://localhost:8000/static/video_qa_demo.html` 查看完整的演示界面。

### 使用流程

1. **上传视频**: 粘贴YouTube链接，系统自动提取ID并处理转录
2. **等待处理**: 首次处理需要时间，系统会自动轮询状态
3. **提出问题**: 指定时间点（支持MM:SS或秒数），输入问题
4. **获得答案**: AI基于转录内容提供精准回答

## 技术架构

### 核心组件

1. **视频处理器** (`agents/video_qa_agent.py`)
   - 转录文本获取和上下文提取
   - AI问答逻辑实现

2. **前端接口** (`api/routes/frontend_video_qa.py`)
   - 用户友好的API封装
   - 完整的错误处理和状态管理

3. **文件存储** (`core/file_storage.py`)
   - JSON格式转录文本存储
   - 高效的文件组织结构

### 数据流

```
YouTube URL → 视频ID提取 → 转录下载 → 文件存储 → 上下文提取 → AI分析 → 用户回答
```

## 示例使用

### 示例1: 询问视频内容
```bash
curl -X POST "http://localhost:8000/v1/frontend/ask" \\
-H "Content-Type: application/json" \\
-d '{
  "video_id": "dQw4w9WgXcQ",
  "timestamp": 30,
  "question": "这段歌词的含义是什么？"
}'
```

**响应示例:**
```json
{
  "success": true,
  "answer": "在30秒时间点，歌词表达的是'我正在考虑全心投入的承诺，你不会从其他人那里得到这样的承诺。'这体现了歌曲主题中对爱情的坚定承诺。",
  "context_transcript": "[00:27] ♪ A full commitment's what I'm thinking of ♪\\n[00:31] ♪ You wouldn't get this from any other guy ♪",
  "timestamp_info": {
    "target_time": 30.0,
    "target_formatted": "00:30",
    "context_duration": 25.0
  }
}
```

### 示例2: 解析时间戳
```bash
curl "http://localhost:8000/v1/frontend/parse-timestamp?timestamp=2:15"
```

**响应:**
```json
{
  "success": true,
  "original": "2:15",
  "seconds": 135,
  "formatted": "02:15"
}
```

## 错误处理

系统提供详细的错误信息：

- **视频未找到**: 提示用户先上传处理视频
- **转录缺失**: 自动触发后台处理
- **时间点无效**: 提供有效时间范围建议
- **AI调用失败**: 提供基础转录内容作为备用

## 性能特性

- **文件存储**: 减少数据库负载，提高查询速度
- **智能上下文**: 仅提取相关时间段，减少AI处理负担
- **缓存机制**: 已处理视频立即可用
- **异步处理**: 后台处理不阻塞用户操作

## 扩展性

系统设计支持：

- **多语言转录**: 自动检测和处理
- **自定义时间范围**: 可调整上下文窗口
- **批量处理**: 支持多视频并发处理
- **API定制**: 轻松扩展新的问答功能

## 部署说明

1. 确保YouTube转录处理服务正常运行
2. 配置OpenAI API密钥用于AI问答
3. 设置文件存储目录权限
4. 启动FastAPI服务

```bash
# 检查服务状态
curl http://localhost:8000/v1/health

# 访问演示页面
open http://localhost:8000/static/video_qa_demo.html
```

## 常见问题

**Q: 视频处理需要多长时间？**
A: 首次处理通常需要10-30秒，取决于视频长度和网络状况。

**Q: 支持哪些YouTube视频？**
A: 支持所有有自动生成或手动添加字幕的公开视频。

**Q: 时间戳格式有什么要求？**
A: 支持多种格式：`1:23`、`01:23:45`、`83`、`83.5`等。

**Q: AI回答的准确性如何？**
A: 基于GPT-4分析转录文本，准确性取决于转录质量和问题清晰度。
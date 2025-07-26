# Kairos

A Python tool that builds structured knowledge graphs for educational topics and scrapes related learning resources.

## Features

1. **Knowledge Graph Construction** (`kg_construction`)
   - Builds structured knowledge graphs for educational topics
   - Supports multiple LLM providers (Gemini, Kimi)
   - Generates prerequisite relationships and learning paths

2. **Learning Resource Scraping** (`scraping`)
   - Scrapes educational resources from various platforms
   - Organizes content by topics and difficulty levels

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Setup API keys:
   - Copy `.env.example` to `.env`
   - Add your API keys to the `.env` file:
```bash
cp .env.example .env
# Edit .env and add your API keys:
# - GOOGLE_API_KEY: for Gemini (from Google AI Studio)
# - OPENAI_API_KEY: for Kimi
```

## Run with Docker (Recommended for Team/Production)

The project provides a `docker-compose` setup that will automatically start both the API service and a Postgres (pgvector) database.

### 1. Prepare your `.env` file

Copy the example and fill in your secrets:

```bash
cp .env.example .env
# Edit .env and add your API keys and (optionally) database credentials
```

### 2. Start all services (API + Database)

From the `backend` directory, run:

```bash
docker compose up -d
```

- This will automatically start the API and a Postgres database (with pgvector extension).
- The database will be available at `pgvector:5432` inside the Docker network.
- Data is persisted in a local Docker volume (`pgdata`).

### 3. Check service status

```bash
docker compose ps
```

### 4. Access the API

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/v1/health](http://localhost:8000/v1/health)

### 5. Stop all services

```bash
docker compose down
```

**Note:**
- You do **not** need to install Postgres or create the database manually.
- All teammates can use the same workflow: just pull the repo, set up `.env`, and run `docker compose up -d`.

## Run Backend API (Local Development)

### 1. Start the backend API server

From the project root, run:

```bash
cd backend
./start_server.sh
```

- This script will launch the FastAPI server with extended timeout settings, suitable for long-running knowledge graph generation requests.

### 2. Test the API

You can use the provided test script to verify the API endpoints:

```bash
./test_api.sh
```

- This script will:
  - Check the health endpoint
  - Test the knowledge graph creation endpoint (with a long timeout)

You can also manually test with curl:

```bash
curl --max-time 600 --connect-timeout 30 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"topic": "机器学习基础", "model_type": "gemini-2.5-pro", "save_to_file": true}' \
  http://127.0.0.1:8000/v1/knowledge-graph/create
```

### 3. Access the API documentation

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/v1/health](http://localhost:8000/v1/health)

## Database Inspection (PostgreSQL)

You can inspect the contents of the Postgres database directly using the `psql` command-line tool.

### 1. Connect to the database

```bash
source venv/bin/activate  # (if not already activated)
psql -U ai -h localhost -d ai
```

### 2. List all tables

```sql
\dt
```

### 3. Show the structure of a table

For example, to see the structure of the `learning_resource` table:

```sql
\d learning_resource
```

### 4. Query table contents

For example, to view the first 10 learning resources:

```sql
SELECT * FROM learning_resource LIMIT 10;
```

### 5. Exit the database shell

```sql
\q
```

**Note:**
- The default database user and name are both `ai`.
- If you are running Postgres in Docker, you may need to use `docker exec -it <container> psql ...` instead.

## Database Export/Import

### Export database

To create a backup of the entire database:

```bash
# Export to SQL file (human-readable)
pg_dump -U ai -h localhost -d ai > kairos_backup_$(date +%Y%m%d_%H%M%S).sql

# Export to custom format (compressed, faster for large databases)
pg_dump -U ai -h localhost -d ai -Fc > kairos_backup_$(date +%Y%m%d_%H%M%S).dump
```

### Import database

To restore from a backup:

```bash
# From SQL file
psql -U ai -h localhost -d ai < kairos_backup_20241201_143000.sql

# From custom format
pg_restore -U ai -h localhost -d ai kairos_backup_20241201_143000.dump
```

### Export specific tables

To export only specific tables (e.g., learning resources):

```bash
pg_dump -U ai -h localhost -d ai -t learning_resource -t knowledge > learning_data_backup.sql
```

### Export using Python script (Alternative method)

If you encounter version mismatch issues with `pg_dump`, you can use the Python export script:

```bash
cd backend
python scripts/export_database.py
```

This will create a JSON file with all database contents, including:
- Knowledge points
- Learning resources  
- Association relationships
- Export timestamp and statistics

The exported file will be named `kairos_database_export_YYYYMMDD_HHMMSS.json`.

**Note:**
- Replace `ai` with your actual database user if different
- The backup files will be created in your current directory
- Use custom format (`.dump`) for large databases as it's faster and compressed
- The Python script method is useful when `pg_dump` version doesn't match the server version

## Usage

### Knowledge Graph Construction

Generate knowledge graphs using either Gemini or Kimi:

```bash
# Using Gemini
python -m backend.core.plan.kg_construction.kg_main --model_type gemini-2.5-pro

# Using Kimi
python -m backend.core.plan.kg_construction.kg_main --model_type kimi-k2-0711-preview
```

The script will:
1. Generate a knowledge graph for the specified topic
2. Save it as a JSON file with timestamp (e.g., `machine_learning_20240324_153000.json`)
3. Validate the graph structure and relationships

### Video Analysis API - **[✅ COMPLETED]**

**API 3: 给一个视频，按transcript中什么时间段对应什么知识点进行切割**

The video segmentation API automatically analyzes YouTube videos, extracts transcripts, and intelligently segments them by knowledge points.

#### Features:
- 🎬 **YouTube Video Processing**: Automatically extracts subtitles from video URLs
- 🧠 **AI-Powered Segmentation**: Uses LLM to match transcript content with L3 atomic knowledge points
- ⏱️ **Precise Time Mapping**: Creates time-stamped segments with start/end times
- 📊 **Database Storage**: Stores results in structured format for easy querying
- 🔄 **Async Processing**: Background job processing with status monitoring

#### Quick Start:

```bash
# Install dependencies
pip install requests psycopg2-binary

# Run complete video analysis example
python video_analysis_example.py

# Query existing analyzed videos
python video_analysis_example.py demo

# Quick analysis (simplified version)
python quick_video_analysis.py
```

#### API Endpoints:

```bash
# Submit video for analysis
curl -X POST "http://localhost:8000/v1/videos/analyze-segments-from-video-link" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtu.be/OAKAZhFmYoI",
    "knowledge_context_id": 1,
    "preferred_subtitle_language": "en"
  }'

# Check analysis status
curl "http://localhost:8000/v1/videos/analyze-segments/status/{job_id}"
```

#### Example Output:
```json
{
  "video_info": {
    "resource_id": 298,
    "title": "PPO Algorithm Explanation",
    "url": "https://youtu.be/OAKAZhFmYoI",
    "total_segments": 8
  },
  "segments": [
    {
      "id": 123,
      "title": "On-Policy vs Off-Policy",
      "timeRange": {
        "start": 43,
        "end": 90,
        "startTime": "00:00:43.460",
        "endTime": "00:01:30.300",
        "duration": 47
      },
      "description": "Explains the difference between on-policy and off-policy training methods...",
      "knowledge": {
        "domain": "深度学习",
        "importance": 3
      }
    }
  ]
}
```

#### Database Queries:
```sql
-- View all video segments for a resource
SELECT vs.start_time, vs.end_time, k.title as knowledge_title, vs.segment_description
FROM video_segment vs
JOIN knowledge k ON vs.knowledge_id = k.id
WHERE vs.resource_id = 298
ORDER BY vs.start_seconds;
```

📖 **See `FRONTEND_API_GUIDE.md` for complete integration documentation including React/Vue examples and TypeScript types.**

## API Testing Scripts

The project includes three Python test scripts to validate different API endpoints:

### 1. Question Diagnosis API (`test_question_diagnosis.py`)

Tests the synchronous question diagnosis API that analyzes user questions and identifies relevant knowledge points.

#### API Call:
```http
POST /v1/questions/diagnose/sync
Content-Type: application/json

{
  "user_question": "为什么PPO算法里要用clip函数来限制策略更新的幅度？",
  "context_resource_id": 51
}
```

#### Input:
- `user_question` (string): The question to analyze
- `context_resource_id` (int): Resource ID for context

#### Output:
```json
{
  "success": true,
  "summary": {
    "total_diagnosed": 3,
    "total_contextual": 5,
    "max_relevance_score": 0.95
  },
  "diagnosed_knowledge_points": [
    {
      "title": "PPO策略优化",
      "relevance_score": 0.95,
      "explanation": "PPO使用clip函数限制策略更新幅度..."
    }
  ],
  "contextual_candidate_knowledge_points": [
    {
      "title": "强化学习基础",
      "relevance_score": 0.8
    }
  ],
  "used_global_search": false
}
```

#### Usage:
```bash
python test_question_diagnosis.py
# Choose option 1 for single question (shows raw JSON)
# Choose option 2 for multiple questions test
```

### 2. Learning API (`test_learning_api.py`)

Tests the video prerequisite analysis API that analyzes YouTube videos to identify required knowledge.

#### API Call:
```http
POST /v1/learning/video/prerequisites
Content-Type: application/json

{
  "video_url": "https://youtu.be/OAKAZhFmYoI",
  "video_title": "PPO Algorithm Explanation",
  "model_type": "o3-mini"
}
```

#### Input:
- `video_url` (string): YouTube video URL
- `video_title` (string, optional): Custom title for the video
- `model_type` (string): AI model to use (default: "o3-mini")

#### Output:
```json
{
  "message": "分析成功",
  "confidence_score": 85,
  "analysis_model": "o3-mini",
  "video_info": {
    "title": "PPO Algorithm Explanation",
    "url": "https://youtu.be/OAKAZhFmYoI",
    "has_transcript": true
  },
  "prerequisite_knowledge": [
    {
      "title": "强化学习基础",
      "domain": "机器学习",
      "estimated_hours": 8,
      "description": "强化学习的基本概念和原理...",
      "learning_resources": [
        {
          "title": "强化学习入门教程",
          "quality_score": 9,
          "resource_type": "视频",
          "resource_url": "https://example.com/rl-intro"
        }
      ]
    }
  ]
}
```

#### Usage:
```bash
python test_learning_api.py
```

### 3. Video Segmentation API (`test_video_chunk.py`)

Tests the video analysis API that segments videos by knowledge points with precise timestamps.

#### API Call:
```http
POST /v1/videos/analyze-segments-from-video-link
Content-Type: application/json

{
  "video_url": "https://youtu.be/OAKAZhFmYoI",
  "knowledge_context_id": 1,
  "resource_title": "PPO算法讲解视频",
  "preferred_subtitle_language": "en"
}
```

#### Input:
- `video_url` (string): YouTube video URL
- `knowledge_context_id` (int): Knowledge context for filtering relevant points
- `resource_title` (string, optional): Custom resource title
- `preferred_subtitle_language` (string): Subtitle language preference

#### Output (Initial Response):
```json
{
  "job_id": "12345-67890",
  "resource_id": 298,
  "status_url": "/v1/videos/analyze-segments/status/12345-67890",
  "message": "Video analysis started"
}
```

#### Status Check API:
```http
GET /v1/videos/analyze-segments/status/{job_id}
```

#### Status Response:
```json
{
  "status": "completed",
  "progress_percentage": 100,
  "message": "Analysis completed successfully",
  "segments_created": 8
}
```

#### Final Database Query Result:
```json
{
  "resource": {
    "id": 298,
    "title": "PPO Algorithm Explanation",
    "resource_url": "https://youtu.be/OAKAZhFmYoI",
    "duration_minutes": 15
  },
  "segments": [
    {
      "segment_id": 123,
      "time_range": "00:00:43.460 - 00:01:30.300",
      "start_seconds": 43,
      "end_seconds": 90,
      "duration": 47,
      "knowledge_title": "On-Policy vs Off-Policy",
      "knowledge_domain": "深度学习",
      "knowledge_level": "L3",
      "description": "Explains the difference between on-policy and off-policy methods",
      "importance_level": 3
    }
  ],
  "summary": {
    "total_segments": 8,
    "total_duration_seconds": 450,
    "average_segment_duration": 56.25
  }
}
```

#### Usage:
```bash
# Full workflow: submit analysis, wait for completion, query results
python test_video_chunk.py

# Demo mode: query existing resource
python test_video_chunk.py demo
```

### Common Features:

- **JSON Output**: All APIs return JSON responses
- **Error Handling**: Comprehensive error handling with status codes
- **Timeout Support**: Extended timeouts for long-running operations
- **Database Integration**: Results stored in PostgreSQL with pgvector
- **Async Processing**: Video analysis uses background job processing

### Web Scraping

Run the scraping module:
```bash
python -m scraping.scraping_main
```

## Output

### Knowledge Graphs
The knowledge graphs are saved as JSON files containing:
- **Nodes**: Individual concepts with:
  - Unique IDs
  - Human-readable labels
  - Domain categorization
  - Estimated learning hours
  - Importance descriptions
- **Edges**: Prerequisite relationships between concepts

### Learning Resources
Scraped resources are organized by:
- Topic
- Difficulty level
- Platform
- Content type

## Project Structure

```
Steep/
├── kg_construction/     # Knowledge graph construction module
├── scraping/           # Web scraping module
├── data/               # Shared data directory
├── docs/               # Documentation
└── scripts/            # Utility scripts
```
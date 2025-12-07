# SeekSpider

A Seek.com.au job scraper system built on the Plombery task scheduling framework, designed for automated collection of Australian IT job listings.

## Features

- **Automated Scraping** - Scheduled crawling of Seek.com.au IT job listings
- **AI Analysis** - Automatic tech stack extraction and salary normalization using AI
- **Web UI** - Visual task management interface powered by Plombery
- **Database Storage** - PostgreSQL/Supabase data persistence
- **Multi-Pipeline Scheduling** - Support for multiple data collection pipelines running in parallel

## Project Structure

```
SeekSpider/
├── pipeline/                    # Pipeline definitions
│   └── src/
│       ├── app.py              # Application entry point
│       ├── seek_spider_pipeline.py     # Seek scraper pipeline
│       ├── flow_meter_pipeline.py      # Flow meter data pipeline
│       └── ...                         # Other pipelines
├── scraper/                     # Scraper modules
│   └── SeekSpider/             # Seek spider
│       ├── spiders/
│       │   └── seek.py         # Main spider logic
│       ├── core/
│       │   ├── config.py       # Configuration management
│       │   ├── database.py     # Database operations
│       │   └── ai_client.py    # AI API client
│       ├── utils/
│       │   ├── tech_stack_analyzer.py    # Tech stack analysis
│       │   ├── salary_normalizer.py      # Salary normalization
│       │   └── tech_frequency_analyzer.py # Tech frequency statistics
│       ├── pipelines.py        # Scrapy pipeline
│       └── settings.py         # Scrapy settings
├── src/plombery/               # Plombery core
├── frontend/                   # React frontend
└── .env                        # Environment configuration
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```env
# Database configuration
POSTGRESQL_HOST=your_host
POSTGRESQL_PORT=5432
POSTGRESQL_USER=your_user
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_DATABASE=your_database
POSTGRESQL_TABLE=seek_jobs

# AI API configuration (for post-processing)
AI_API_KEY=your_api_key
AI_API_URL=https://api.siliconflow.cn/v1/chat/completions
AI_MODEL=deepseek-ai/DeepSeek-V2.5
```

### 3. Run

```bash
# Option 1: Run via Pipeline (recommended)
cd pipeline
./run.sh

# Option 2: Run spider directly
cd scraper
scrapy crawl seek
```

Access the Web UI at `http://localhost:8000`.

## Seek Spider Pipeline

### Capabilities

- Scrapes IT job listings from Seek.com.au (Perth area)
- Covers all IT subcategories (Development, Architecture, DevOps, Testing, etc.)
- Automatically extracts job details (salary, location, job description, etc.)
- AI post-processing: tech stack extraction, salary normalization

### Scheduled Tasks

The pipeline is configured with two scheduled triggers:

- **Daily 6 AM** - Runs at 6:00 AM (Perth timezone)
- **Daily 6 PM** - Runs at 6:00 PM (Perth timezone)

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `location` | Search location | All Perth WA |
| `classification` | Job classification code | 6281 (IT) |
| `run_post_processing` | Run AI post-processing | true |
| `concurrent_requests` | Number of concurrent requests | 16 |
| `download_delay` | Request delay (seconds) | 2.0 |

## Database Schema

The spider stores data in PostgreSQL with the following main fields:

| Field | Description |
|-------|-------------|
| Id | Job ID (Seek Job ID) |
| JobTitle | Job title |
| BusinessName | Company name |
| WorkType | Work type (Full-time/Part-time/Contract) |
| JobType | Job category |
| PayRange | Salary range |
| Area | Region |
| Suburb | Detailed location |
| JobDescription | Job description (HTML) |
| TechStack | Tech stack (AI extracted) |
| Url | Job URL |
| PostedDate | Posted date |
| IsActive | Whether the job is active |

## Docker Deployment

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Tech Stack

- **Scraping Framework**: Scrapy
- **Task Scheduling**: Plombery (APScheduler)
- **Web Framework**: FastAPI
- **Frontend**: React + Vite
- **Database**: PostgreSQL
- **AI API**: DeepSeek / OpenAI-compatible API

## License

MIT License

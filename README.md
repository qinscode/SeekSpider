<div align="center">

# SeekSpider

**Smart Job Scraper for SEEK**  
A powerful, AI-augmented web scraping tool built with Scrapy, designed to extract, process, and analyze job listings
from [seek.com.au](https://www.seek.com.au). SeekSpider enables real-time job market intelligence with tech stack
trends, salary insights, and clean PostgreSQL integration.

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white&style=for-the-badge"/>
  <img alt="Scrapy" src="https://img.shields.io/badge/Scrapy-WebCrawler-2A9D8F?style=for-the-badge"/>
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-JSONB-336791?logo=postgresql&logoColor=white&style=for-the-badge"/>
  <img alt="Selenium" src="https://img.shields.io/badge/Selenium-Automation-43B02A?logo=selenium&logoColor=white&style=for-the-badge"/>
  <img alt="AI Integration" src="https://img.shields.io/badge/AI-TextAnalysis-6C63FF?style=for-the-badge"/>
  <img alt="License" src="https://img.shields.io/github/license/your-username/SeekSpider?style=for-the-badge"/>
</p>
</div>

---

## 📚 Overview

SeekSpider is a modular scraping system designed for job market analysis. It collects IT-related job postings from SEEK
using Scrapy and Selenium, enriches the data with AI-powered salary and tech stack analysis, and stores everything into
a PostgreSQL database with JSONB fields for flexibility and speed.

---

## ⚙️ Features

### 🕸 Data Collection

- Scrapy crawler with category + pagination traversal
- Selenium-based authentication
- BeautifulSoup integration for fine-grained parsing

### 🧠 AI Integration

- Extracts and analyzes technology stacks
- Normalizes salary info
- Generates demand statistics on tech usage

### 💾 Database & Storage

- PostgreSQL with JSONB for flexible schema
- Transaction-safe pipeline with smart upserts
- Automatic job status tracking

### 🧰 Architecture

- Modular class structure (`DatabaseManager`, `AIClient`, `Logger`, `Utils`)
- Environment-configured settings
- Batch-safe crawling and retry mechanisms

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL (with an active database)
- Google Chrome + ChromeDriver
- Git

### Installation

```bash
git clone https://github.com/your-username/SeekSpider.git
cd SeekSpider
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory:

```env
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=secret
POSTGRESQL_DATABASE=seek_data
POSTGRESQL_TABLE=Jobs

SEEK_USERNAME=your_email
SEEK_PASSWORD=your_password

AI_API_KEY=your_api_key
AI_API_URL=https://api.openai.com/v1/...
AI_MODEL=gpt-4
```

Make sure PostgreSQL is running and your credentials are correct.

---

## 🏃 Run the Spider

### Option 1: With main script

```bash
python main.py
```

### Option 2: With Scrapy

```bash
scrapy crawl seek
```

This will log in to SEEK, collect job data, and store it into PostgreSQL.

---

## 🔍 API Query Parameters

The spider uses Seek’s internal search API. Here’s an example:

```python
search_params = {
    'where': 'All Perth WA',
    'classification': '6281',  # IT category
    'seekSelectAllPages': 'true',
    'locale': 'en-AU',
}
```

- Supports subclassification traversal
- Automatically paginated
- SEO metadata enabled
- Auth tokens handled automatically

---

## 🧱 Project Structure

```
SeekSpider/
├── spiders/seek_spider.py      # Main spider
├── pipelines.py                # Data insertion logic
├── items.py                    # Data model
├── settings.py                 # Scrapy settings
├── main.py                     # Entry point
├── db/                         # Database utilities
├── ai/                         # AI analysis components
└── utils/                      # Parsing, token, salary analyzers
```

---

## 🧩 Key Modules

- `DatabaseManager`: Context-managed PostgreSQL operations with retries
- `Logger`: Colored logging with levels + per-component logs
- `AIClient`: Handles external API requests and formatting
- `TechStackAnalyzer`: NLP-based tech term extraction
- `SalaryNormalizer`: Converts pay ranges to numeric bounds
- `Config`: Loads and validates `.env` settings

---

## 🗃 Database Schema

```sql
CREATE TABLE "Jobs"
(
    "Id"             INTEGER PRIMARY KEY,
    "JobTitle"       VARCHAR,
    "BusinessName"   VARCHAR,
    "WorkType"       VARCHAR,
    "JobDescription" TEXT,
    "PayRange"       VARCHAR,
    "Suburb"         VARCHAR,
    "Area"           VARCHAR,
    "Url"            VARCHAR,
    "AdvertiserId"   INTEGER,
    "JobType"        VARCHAR,
    "PostedDate"     TIMESTAMP,
    "ExpiryDate"     TIMESTAMP,
    "IsActive"       BOOLEAN   DEFAULT TRUE,
    "TechStack"      JSONB,
    "MinSalary"      INTEGER,
    "MaxSalary"      INTEGER,
    "CreatedAt"      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Recommended indexes:

```sql
CREATE INDEX idx_active ON "Jobs" ("IsActive");
CREATE INDEX idx_salary ON "Jobs" ("MinSalary", "MaxSalary");
CREATE INDEX idx_techstack ON "Jobs" USING GIN ("TechStack");
```

---

## 🤝 Contributing

Pull requests are welcome!  
Please open an issue to discuss major changes.

```bash
git checkout -b feature/my-new-feature
git commit -m "feat: add new parser"
git push origin feature/my-new-feature
```

---

## 📄 License

Licensed under the [Apache License 2.0](LICENSE).

---

## 🙏 Acknowledgments

- [Scrapy](https://scrapy.org/) for the powerful crawling engine
- [Selenium](https://www.selenium.dev/) for seamless login automation
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for DOM parsing  

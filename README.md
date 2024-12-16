# SeekSpider: A Scrapy Project for Job Scraping

## Table of Contents

- [SeekSpider: A Scrapy Project for Job Scraping](#seekspider-a-scrapy-project-for-job-scraping)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Setup](#setup)
    - [Execution](#execution)
  - [Web API Parameters Explanation](#web-api-parameters-explanation)
  - [Project Components](#project-components)
    - [Core Components](#core-components)
    - [Items](#items)
    - [Spider](#spider)
    - [Pipeline](#pipeline)
    - [settings](#settings)
  - [Configuration](#configuration)
  - [Database Schema](#database-schema)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Introduction

SeekSpider is a comprehensive job market analysis tool built with Scrapy. It not only extracts job listings from seek.com.au but also performs advanced analysis of job descriptions, salaries, and technology stacks. The system uses a modular architecture with dedicated components for web scraping, data processing, and AI-powered analysis.

Key capabilities include:
- Automated data collection from SEEK's job listings
- AI-powered analysis of job descriptions and requirements
- Salary standardization and analysis
- Technology stack trend analysis
- Real-time job market statistics

## Features

Core Architecture:
- Modular architecture with clear separation of concerns
- Core components for database, logging, and AI integration
- Centralized configuration management
- Robust error handling and logging

Data Collection:
- Scrapy framework for efficient web crawling
- Selenium-based authentication system
- Smart pagination with category management
- BeautifulSoup integration for detailed parsing

Data Processing:
- PostgreSQL database with JSONB support
- Transaction management and data integrity
- Job status tracking and updates
- Batch processing capabilities

AI Integration:
- AI-powered tech stack analysis
- Salary standardization
- Technology trend analysis
- Configurable AI parameters

Monitoring and Management:
- Detailed logging system
- Performance monitoring
- Rate limiting compliance
- Automatic error recovery

## Getting Started

### Prerequisites

Ensure you have the following installed on your system:

- Python 3.9 or above
- pip (Python package installer)
- PostgreSQL server (for database storage)
- Chrome/Chromium browser (for Selenium)
- ChromeDriver (for Selenium WebDriver)
- Git (for version control)

### Installation

1. Clone the repository to your local machine.

```shell
git clone https://github.com/your-username/SeekSpider.git
cd SeekSpider
```

2. Navigate to the project directory in your terminal. Install the required Python packages listed in `requirements.txt`. You may use pip to install them:

```shell
pip install -r requirements.txt
```

3. Install ChromeDriver:

For Ubuntu/Debian:
```shell
sudo apt-get update
sudo apt-get install chromium-chromedriver
```

For macOS:
```shell
brew install chromedriver
```

For Windows, download from the official ChromeDriver website.

4. Create a `.env` file in the project root:

```env
POSTGRESQL_HOST=your_host
POSTGRESQL_PORT=5432
POSTGRESQL_USER=your_user
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_DATABASE=your_database
POSTGRESQL_TABLE=your_table

SEEK_USERNAME=your_seek_email
SEEK_PASSWORD=your_seek_password
AI_API_KEY=your_api_key
AI_API_URL=your_api_url
AI_MODEL=your_model_name
```

Be sure to have PostgreSQL installed and running on your local machine or remote server with the required database and table schema set up. Configure your database settings in `settings_local.py` to point to your PostgreSQL instance.

### Setup

1. **Database Configuration**:
   - Create your PostgreSQL database and user with appropriate privileges.
   - Define your database connection settings in `.env` file.

2. **Parameters Configuration**:
   - Customize search parameters in the `search_params` dictionary of the `SeekSpider` class for targeted scraping.

### Execution

You can run the spider in two ways:

1. Using the main script:
```bash
python main.py
```

2. Using scrapy directly:
```bash
scrapy crawl seek
```

Upon execution, the spider will start to navigate through the job listings on SEEK and insert each job's data into the database using the pipeline.

**Note:** I'm not trying to be lazy, but you can just simply run main.py instead : )


## Web API Parameters Explanation

The spider makes use of the Seek Job Search API with several query parameters to tailor the search results according to specific needs. Below is a detailed explanation of these parameters used in the spider's query string:

+ ```python
+ search_params = {
+     'siteKey': 'AU-Main',        # Identifies the main SEEK Australia site
+     'sourcesystem': 'houston',    # SEEK's internal system identifier
+     'where': 'All Perth WA',      # Location filter
+     'page': 1,                    # Current page number
+     'seekSelectAllPages': 'true', # Enable full page access
+     'classification': '6281',      # IT jobs classification
+     'subclassification': '',      # Specific IT category
+     'include': 'seodata',         # Include SEO metadata
+     'locale': 'en-AU',            # Australian English locale
+ }
+ ```

- - `where`: Refers to the location for the job search. It's set to "All Perth WA" in the current configuration.
- - `seekSelectAllPages`: A boolean parameter that, when set to True, indicates the scraper to consider all available pages of job listings.
- - `classification`: Each job category on Seek has a unique classification ID. The value `6281` refers to Information & Communication Technology.
- - `hadPremiumListings`: Indicates whether the search results include premium listings.
- - `include`: Include search engine optimization data in the response.
- - `locale`: Determines the regional setting of the API. 'en-AU' sets the locale to English - Australia.
- - `url_page`: Current page number.
+ Key API features:
+ - Systematic category traversal using subclassifications
+ - Automatic pagination handling
+ - Location-based filtering
+ - SEO data inclusion
+ - Locale support

**Note:** Seek has a 26-page limit for job listings, which means you won't go further than 26 pages of results. To overcome this limitation, the job is broken into smaller pieces using subclasses.

- The `params` are converted to a query string by the `urlencode` method, which ensures they are properly formatted for the HTTP request. Adjusting these parameters allows for a wide range of searches to collect data that's useful for different users' intents.
+ The spider automatically handles:
+ - URL encoding of parameters
+ - Authentication token management
+ - Request retries on failure
+ - Rate limiting compliance
+ - Response validation

These parameters are crucial for the spider's functionality as they dictate the scope and specificity of the web scraping task at hand. Users can modify these parameters as per their requirements to collect job listing data relevant to their own specific search criteria.

## Project Components

### Core Components

The core components of SeekSpider are responsible for database, logging, and AI integration.

+ #### Database Manager
+ The `DatabaseManager` class provides a centralized interface for all database operations:
+ - Connection and transaction management using context managers
+ - Parameterized queries to prevent SQL injection
+ - Automatic retry mechanism for failed operations
+ - Logging of all database operations
+ 
+ #### Logger
+ The `Logger` class provides a unified logging interface:
+ - Console output with formatted messages
+ - Different log levels (INFO, ERROR, WARNING, DEBUG)
+ - Component-specific logging with named loggers
+ 
+ #### AI Client
+ The `AIClient` class handles all AI-related operations:
+ - Integration with AI APIs for text analysis
+ - Automatic retry for rate-limited requests
+ - Configurable request parameters
+ - Error handling and logging
+ 
+ #### Utils
+ The utils package contains specialized analyzers:
+ - `TechStackAnalyzer`: Extracts technology stack information from job descriptions
+ - `SalaryNormalizer`: Standardizes salary information into consistent format
+ - `TechStatsAnalyzer`: Generates statistics about technology usage
+ - `get_token`: Handles SEEK authentication and token management

### Items

The `SeekspiderItem` class is defined as a Scrapy Item. Items provide a means to collect the data scraped by the spiders. The fields collected by this project are:

| Field Name     | Description                                        |
| --------------- | ---------------------------------------------------- |
| `job_id`        | The unique identifier for the job posting.         |
| `job_title`     | The title of the job.                              |
| `business_name` | The name of the business advertising the job.      |
| `work_type`     | The type of employment (e.g., full-time, part-time). |
| `job_description` | A description of the job and its responsibilities. |
| `pay_range`     | The salary or range provided for the position.     |
| `suburb`        | The suburb where the job is located.               |
| `area`          | A broader area designation for the job location.   |
| `url`           | The direct URL to the job listing.                 |
| `advertiser_id` | The unique identifier for the advertiser of the job. |
| `job_type`      | The classification of the job.                     |
| `posted_date`  | The original posting date of the job
| `is_active`    | Indicates if the job listing is still active
| `expiry_date` | When the job listing expired (if applicable)

### Spider

The heart of the SeekSpider project is the `scrapy.Spider` subclass that defines how job listings are scraped. It constructs the necessary HTTP requests, parses the responses returned from the web server, and extracts the data using selectors to populate `SeekspiderItem` objects.

+ The spider now includes several key components:
+ 
+ #### Authentication
+ - Automated login using Selenium WebDriver
+ - Token management and refresh mechanism
+ - Secure credential handling
+ 
+ #### Job Category Management
+ - Systematic traversal through IT job categories
+ - Smart pagination with subclassification support
+ - Detailed logging of category transitions
+ 
+ #### Data Extraction
+ - API-based job listing retrieval
+ - BeautifulSoup integration for detailed parsing
+ - Robust error handling and retry logic
+ 
+ #### Post-Processing
+ - Automated tech stack analysis
+ - Salary standardization
+ - Technology usage statistics generation
+ - Job status tracking (active/inactive)

### Pipeline

The `SeekspiderPipeline` is responsible for processing the items scraped by the spider. Once an item has been populated with data by the spider, it is passed to the pipeline, where it establishes a connection to the PostgreSQL database via psycopg2 and inserts the data into the corresponding table.

+ Key pipeline features:
+ - Efficient database connection management
+ - Transaction support for data integrity
+ - Automatic job deactivation for expired listings
+ - Smart update/insert logic based on job ID
+ - Batch processing capabilities

### settings
I have intentionally slowed down the speed to avoid any ban. If you feel the spider is too slow, please try to increase `CONCURRENT_REQUESTS` and decrease `DOWNLOAD_DELAY`.

Additional important settings:
- `CONCURRENT_REQUESTS = 16`: Concurrent request limit
- `DOWNLOAD_DELAY = 2`: Delay between requests
- Custom retry middleware configuration
- Logging level configuration


## Configuration

- Before running the spider, you will need to create a `settings_local.py` file in your project directory. This file should contain the configuration settings for your database connection. Here is a template for the `settings_local.py` file:
+ The project uses a centralized configuration management system through the `Config` class and environment variables. All configuration is loaded from a `.env` file in the project root.

+ Before running the spider, create a `.env` file with the following configuration:

```env
# Database Configuration
POSTGRESQL_HOST=your_host
POSTGRESQL_PORT=5432
POSTGRESQL_USER=your_user
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_DATABASE=your_database
POSTGRESQL_TABLE=your_table

# SEEK Credentials
SEEK_USERNAME=your_seek_email
SEEK_PASSWORD=your_seek_password

# AI API Configuration
AI_API_KEY=your_api_key
AI_API_URL=your_api_url
AI_MODEL=your_model_name
```

- Make sure that this file is not tracked by version control if it contains sensitive information such as your database password. You can add `settings_local.py` to your `.gitignore` file to prevent it from being committed to your git repository.
+ Make sure to add `.env` to your `.gitignore` file to prevent sensitive information from being committed to your repository.

Key configuration features:
- Environment-based configuration management
- Automatic validation of required settings
- Secure credential handling
- Centralized configuration access

You can tweak the crawl parameters like search location, category, and job type in the spider's `search_params` dictionary:

```python
search_params = {
    'siteKey': 'AU-Main',
    'sourcesystem': 'houston',
    'where': 'All Perth WA',
    'page': 1,
    'seekSelectAllPages': 'true',
    'classification': '6281',
    'subclassification': '',
    'include': 'seodata',
    'locale': 'en-AU',
}
```

+ The spider also supports configuration of:
+ - AI analysis parameters
+ - Database connection settings
+ - Logging levels and formats
+ - Retry mechanisms and delays
+ - Authentication parameters

## Database Schema

Make sure that your PostgreSQL database has a table with the correct schema to store the data. Below is a guideline schema based on the fields defined in the `SeekspiderItem`:

```sql
CREATE TABLE "Jobs" (
    "Id" INTEGER PRIMARY KEY,
    "JobTitle" VARCHAR(255),
    "BusinessName" VARCHAR(255),
    "WorkType" VARCHAR(50),
    "JobDescription" TEXT,
    "PayRange" VARCHAR(255),
    "Suburb" VARCHAR(255),
    "Area" VARCHAR(255),
    "Url" VARCHAR(255),
    "AdvertiserId" INTEGER,
    "JobType" VARCHAR(50),
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "ExpiryDate" TIMESTAMP,
    "IsActive" BOOLEAN DEFAULT TRUE,
    "IsNew" BOOLEAN DEFAULT TRUE,
    "PostedDate" TIMESTAMP,
    "TechStack" JSONB,
    "MinSalary" INTEGER,
    "MaxSalary" INTEGER
);

CREATE TABLE "tech_word_frequency" (
    "word" VARCHAR(255) PRIMARY KEY,
    "frequency" INTEGER,
    "created_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Please include relevant indices based on your query patterns for optimal performance.

+ Recommended indices:
+ ```sql
+ CREATE INDEX idx_jobs_tech_stack ON "Jobs" USING GIN ("TechStack");
+ CREATE INDEX idx_jobs_salary ON "Jobs" ("MinSalary", "MaxSalary");
+ CREATE INDEX idx_jobs_active ON "Jobs" ("IsActive");
+ CREATE INDEX idx_jobs_posted_date ON "Jobs" ("PostedDate");
+ ```
+ 
+ Key database features:
+ - JSONB support for flexible tech stack storage
+ - Automated timestamp management
+ - Salary range normalization
+ - Active job tracking
+ - Tech stack frequency analysis

## Contributing

Contributions are welcome. Fork the project, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
## Acknowledgments

The content for this README was generated with the assistance of Generative AI, ensuring accuracy and efficiency in delivering the information needed to understand

(Again, I'm not a lazy boy, definitely)


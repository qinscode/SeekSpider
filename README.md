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

SeekSpider is a powerful web scraping tool built with Scrapy, designed to extract job listings from seek.com.au. It uses Selenium for authentication and handles pagination through SEEK's API, storing the data in a PostgreSQL database. The spider efficiently navigates through job listing pages, collects vital job-related information, and manages retry logic in the event of request failures.

## Features

- Scrapy framework for robust and efficient web crawling.
- Customized settings for logging to maintain cleaner output.
- Pagination handling to iterate over multiple listing pages.
- Automatic traversal through different job classification categories.
- Integration with BeautifulSoup for detailed job description scraping.
- Built-in RetryMiddleware customization to handle HTTP error codes gracefully.
- Automated login and token retrieval using Selenium WebDriver
- API-based job data extraction with robust error handling
- Smart pagination handling with subclassification support
- PostgreSQL database integration with transaction management
- Job status tracking (active/inactive)
- Automatic token refresh mechanism

## Getting Started

### Prerequisites

Ensure you have the following installed on your system:

- Python 3.9 or above
- pip (Python package installer)
- PostgreSQL server (for database storage)
- Chrome/Chromium browser (for Selenium)

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

3. Create a `.env` file in the project root:

```env
POSTGRESQL_HOST=your_host
POSTGRESQL_PORT=5432
POSTGRESQL_USER=your_user
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_DATABASE=your_database
POSTGRESQL_TABLE=your_table

SEEK_USERNAME=your_seek_email
SEEK_PASSWORD=your_seek_password
```

Be sure to have PostgreSQL installed and running on your local machine or remote server with the required database and table schema set up. Configure your database settings in `settings_local.py` to point to your PostgreSQL instance.

### Setup

1. **Database Configuration**:
   - Create your PostgreSQL database and user with appropriate privileges.
   - Define your database connection settings in `.env` file.

2. **Parameters Configuration**:
   - Customize search parameters in the `params` dictionary of the `SeekSpider` class for targeted scraping.

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

- `where`: Refers to the location for the job search. It's set to "All Perth WA" in the current configuration.
- `seekSelectAllPages`: A boolean parameter that, when set to True, indicates the scraper to consider all available pages of job listings.
- `classification`: Each job category on Seek has a unique classification ID. The value `6281` refers to Information & Communication Technology.
- `hadPremiumListings`: Indicates whether the search results include premium listings.
- `include`: Include search engine optimization data in the response.
- `locale`: Determines the regional setting of the API. 'en-AU' sets the locale to English - Australia.
- `url_page`: Current page number.

**Note:** Seek has a 26-page limit for job listings, which means you won't go further than 26 pages of results. To overcome this limitation, the job is broken into smaller pieces using subclasses.

The `params` are converted to a query string by the `urlencode` method, which ensures they are properly formatted for the HTTP request. Adjusting these parameters allows for a wide range of searches to collect data that's useful for different users' intents.

These parameters are crucial for the spider's functionality as they dictate the scope and specificity of the web scraping task at hand. Users can modify these parameters as per their requirements to collect job listing data relevant to their own specific search criteria.

## Project Components

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

The spider now includes:
- Automatic authentication using Selenium
- Token management for API access
- Smart pagination with subclassification support
- Robust error handling and retry logic

### Pipeline

`SeekspiderPipeline` is responsible for processing the items scraped by the spider. Once an item has been populated with data by the spider, it is passed to the pipeline, where it establishes a connection to the PostgreSQL database via pymysql and inserts the data into the corresponding table.

The pipeline now handles:
- Job status tracking (active/inactive)
- Transaction management
- Automatic job deactivation for expired listings
- Efficient updates for existing jobs

### settings
I have intentionally slowed down the speed to avoid any ban. If you feel the spider is too slow, please try to increase `CONCURRENT_REQUESTS` and decrease `DOWNLOAD_DELAY`.

Additional important settings:
- `CONCURRENT_REQUESTS = 16`: Concurrent request limit
- `DOWNLOAD_DELAY = 2`: Delay between requests
- Custom retry middleware configuration
- Logging level configuration


## Configuration

Before running the spider, you will need to create a `settings_local.py` file in your project directory. This file should contain the configuration settings for your database connection. Here is a template for the `settings_local.py` file:

```python
POSTGRESQL_HOST = 'localhost'
POSTGRESQL_PORT = 5432
POSTGRESQL_USER = 'your_user'
POSTGRESQL_PASSWORD = 'your_password'
POSTGRESQL_DATABASE = 'your_database'
POSTGRESQL_TABLE = 'your_table'

SEEK_USERNAME = 'your_seek_email'
SEEK_PASSWORD = 'your_seek_password'
```

Make sure that this file is not tracked by version control if it contains sensitive information such as your database password. You can add `settings_local.py` to your `.gitignore` file to prevent it from being committed to your git repository.

You can tweak the crawl parameters like search location, category, and job type in the spider's `params` dictionary. Ensure that these parameters match the expected query parameters of the [seek.com.au](https://seek.com.au) API.

```python
params = {
  "where": "All Perth WA",
  "classification": 6281,
  "locale": "en-AU",
}
```

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
    "PostedDate" TIMESTAMP
);
```

Please include relevant indices based on your query patterns for optimal performance.

## Contributing

Contributions are welcome. Fork the project, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Acknowledgments

The content for this README was generated with the assistance of Generative AI, ensuring accuracy and efficiency in delivering the information needed to understand

(Again, I'm not a lazy boy, definitely)

# SeekSpider: A Scrapy Project for Job Crawling

## Table of Contents

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
  - [Settings](#settings)
- [Configuration](#configuration)
- [Database Schema](#database-schema)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Introduction

SeekSpider is a powerful web scraping tool built with Scrapy, a fast high-level web crawling and scraping framework for Python. Designed to extract job listings from seek.com.au, SeekSpider efficiently navigates through job listing pages, collects vital job-related information, and stores it for further analysis. It's equipped with functionality to handle pagination, navigate through different classifications, and manage retry logic in the event of request failures.

## Features

- Scrapy framework for robust and efficient web crawling.
- Customized settings for logging to maintain cleaner output.
- Pagination handling to iterate over multiple listing pages.
- Automatic traversal through different job classification categories.
- Integration with BeautifulSoup for detailed job description scraping.
- Built-in RetryMiddleware customization to handle HTTP error codes gracefully.

## Getting Started

### Prerequisites

Ensure you have the following installed on your system:

- Python 3.9 or above
- pip (Python package installer)
- MySQL server (for database storage)

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

Be sure to have MySQL installed and running on your local machine or remote server with the required database and table schema set up. Configure your database settings in `settings_local.py` to point to your MySQL instance.

### Setup

1. **Database Configuration**:
   - Create your MySQL database and user with appropriate privileges.
   - Define your database connection settings in `settings_local.py` or a settings file of your choice.

2. **Parameters Configuration**:
   - Customize search parameters in the `params` dictionary of the `SeekSpider` class for targeted scraping.

### Execution

Run the spider using the following command:

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

### Spider

The heart of the SeekSpider project is the `scrapy.Spider` subclass that defines how job listings are scraped. It constructs the necessary HTTP requests, parses the responses returned from the web server, and extracts the data using selectors to populate `SeekspiderItem` objects.

### Pipeline

`SeekspiderPipeline` is responsible for processing the items scraped by the spider. Once an item has been populated with data by the spider, it is passed to the pipeline, where it establishes a connection to the MySQL database via pymysql and inserts the data into the corresponding table.

### settings
I have intentionally slowed down the speed to avoid any ban. If you feel the spider is too slow, please try to increase `CONCURRENT_REQUESTS` and decrease `DOWNLOAD_DELAY`.


## Configuration

Before running the spider, you will need to create a `settings_local.py` file in your project directory. This file should contain the configuration settings for your database connection. Here is a template for the `settings_local.py` file:

```python
POSTGRESQL_HOST = 'localhost'
POSTGRESQL_PORT = 3306
POSTGRESQL_USER = 'POSTGRESQL_USER'
POSTGRESQL_PASSWORD = 'POSTGRESQL_PASSWORD'
POSTGRESQL_DATABASE = 'Seek'
POSTGRESQL_TABLE = 'Jobs_test'
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

Make sure that your MySQL database has a table with the correct schema to store the data. Below is a guideline schema based on the fields defined in the `SeekspiderItem`:

```sql
CREATE TABLE jobs (
  job_id VARCHAR(255) PRIMARY KEY,
  job_title VARCHAR(255),
  business_name VARCHAR(255),
  work_type VARCHAR(255),
  job_description VARCHAR(255),
  pay_range VARCHAR(255),
  suburb VARCHAR(255),
  area VARCHAR(255),
  url VARCHAR(255),
  advertiser_id VARCHAR(255),
  job_type VARCHAR(255)
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

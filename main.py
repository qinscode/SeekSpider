# coding:utf-8
__author__ = 'Jack Qin'

import os
import sys

from scrapy.cmdline import execute

try:
    # Print the file path
    print(os.path.abspath(__file__))

    # Add project directory to system path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # Disable signal handlers temporarily
    install_shutdown_handlers = lambda x: None

    # Execute spider
    execute(["scrapy", "crawl", "seek"])

except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)

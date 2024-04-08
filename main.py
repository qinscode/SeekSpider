# *_*coding:utf-8 *_*
__author__ = 'Jack Qin'
from scrapy.cmdline import execute
import sys,os


print(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
execute(["scrapy","crawl","seek"])
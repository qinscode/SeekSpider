"""Tests for the deterministic hourly/daily salary cross-check."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scraper', 'SeekSpider'))

from utils.salary_normalizer import rule_based_salary  # noqa: E402


def test_daily_rates():
    assert rule_based_salary("AUD 950 per day") == [247000, 247000]
    assert rule_based_salary("$800-850/day + super") == [208000, 221000]
    assert rule_based_salary("$850.00 - $970.00 p.d.") == [221000, 252200]
    assert rule_based_salary("Melb, Onsite, 12M Contract, $800-$1200 per day") == [208000, 312000]
    assert rule_based_salary("$1,200 per day including 12% super") == [312000, 312000]


def test_hourly_rates():
    assert rule_based_salary("$45 - $55 per hour") == [88920, 108680]
    assert rule_based_salary("$180 - $220 p.h.") == [355680, 434720]
    assert rule_based_salary("$125 – $137.50 per hour") == [247000, 271700]


def test_ambiguous_returns_none():
    assert rule_based_salary("") is None
    assert rule_based_salary("Competitive") is None
    assert rule_based_salary("150") is None
    assert rule_based_salary("$150k - $170k p.a.") is None
    assert rule_based_salary("up to $230K (inc super) OR $950/day") is None
    assert rule_based_salary("AUD 203.65 per hour, incl super 7.25 hours per day") is None
    assert rule_based_salary("$130 - $150 - inc Super - Weekly Pay Options") is None
    assert rule_based_salary("$80,000 per year") is None

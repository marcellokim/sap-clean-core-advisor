"""Tests for source catalog schema and staleness checks."""

from __future__ import annotations

import unittest
from datetime import date

from tools.verify_sources import (
    find_stale_sources,
    load_source_catalog,
    validate_source_schema,
)


class SourceVerificationTests(unittest.TestCase):
    def test_source_catalog_schema_is_valid(self) -> None:
        sources = load_source_catalog()
        issues = validate_source_schema(sources)
        self.assertFalse(issues, f"schema issues: {issues}")

    def test_source_catalog_is_not_stale_as_of_reference_date(self) -> None:
        sources = load_source_catalog()
        issues = find_stale_sources(
            sources=sources,
            max_age_days=90,
            reference_date=date(2026, 3, 10),
        )
        self.assertFalse(issues, f"staleness issues: {issues}")

    def test_staleness_detection_works_for_future_reference_date(self) -> None:
        sources = load_source_catalog()
        issues = find_stale_sources(
            sources=sources,
            max_age_days=90,
            reference_date=date(2027, 3, 10),
        )
        self.assertTrue(issues)


if __name__ == "__main__":
    unittest.main()

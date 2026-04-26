"""Tests for RAG cache invalidation helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from services.rag_pipeline import _compute_docs_hash


class RagPipelineTests(unittest.TestCase):
    def test_docs_hash_changes_when_source_metadata_changes(self) -> None:
        original = [
            SimpleNamespace(
                page_content="same clean core content",
                metadata={"source": "old.md"},
            )
        ]
        renamed = [
            SimpleNamespace(
                page_content="same clean core content",
                metadata={"source": "new.md"},
            )
        ]

        self.assertNotEqual(_compute_docs_hash(original), _compute_docs_hash(renamed))


if __name__ == "__main__":
    unittest.main()

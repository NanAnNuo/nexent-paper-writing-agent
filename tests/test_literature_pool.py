import unittest
from unittest.mock import patch

from core.literature_search import search_paper_pool


def _paper(title: str, abstract: str = "motor imagery EEG robotic arm control", source: str = "test") -> dict:
    return {
        "title": title,
        "authors": ["A. Author"],
        "year": 2024,
        "abstract": abstract,
        "url": f"https://example.test/{title}",
        "venue": "Journal",
        "retrieval_source": source,
    }


class LiteraturePoolTests(unittest.TestCase):
    @patch("core.literature_search.search_papers")
    def test_multiple_queries_expand_pool_and_remove_noise_and_duplicates(self, search_papers):
        search_papers.side_effect = [
            [
                _paper("Motor imagery EEG robotic arm control"),
                _paper("Editorial: motor imagery EEG"),
                _paper("Duplicate motor imagery EEG paper"),
            ],
            [
                _paper("Duplicate motor imagery EEG paper"),
                _paper("Tactile feedback for EEG robotic arm"),
                _paper("Noninvasive BCI rehabilitation control"),
            ],
            [
                _paper("CSP SVM classification of motor imagery EEG"),
                _paper("Deep learning motor imagery EEG decoding"),
            ],
        ]
        papers = search_paper_pool(
            [
                "motor imagery EEG robotic arm",
                "EEG robotic arm tactile feedback",
                "motor imagery EEG classification",
            ],
            target_count=6,
            per_query_limit=8,
        )
        titles = [paper["title"] for paper in papers]
        self.assertEqual(search_papers.call_count, 3)
        self.assertNotIn("Editorial: motor imagery EEG", titles)
        self.assertEqual(titles.count("Duplicate motor imagery EEG paper"), 1)
        self.assertGreaterEqual(len(papers), 5)
        self.assertEqual([paper["citation_key"] for paper in papers], [f"ref{i}" for i in range(len(papers))])

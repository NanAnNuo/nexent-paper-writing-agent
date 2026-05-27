import unittest

from core.content_normalizer import normalize_content


class ContentNormalizerTests(unittest.TestCase):
    def test_abstract_removes_meta_writing_instruction_sentence(self):
        content = (
            "本研究提出闭环控制系统。"
            "摘要作为论文的缩影，需要准确反映研究内容与方法[1]，同时应避免过度解读[2]。"
            "系统采用触觉反馈策略。"
        )

        normalized = normalize_content(content, section_title="摘要")

        self.assertIn("本研究提出闭环控制系统", normalized)
        self.assertIn("系统采用触觉反馈策略", normalized)
        self.assertNotIn("摘要作为论文的缩影", normalized)
        self.assertNotIn("避免过度解读", normalized)


if __name__ == "__main__":
    unittest.main()

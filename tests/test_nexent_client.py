import unittest
from unittest.mock import Mock, patch

from inference.nexent_client import NexentClient


class NexentClientTests(unittest.TestCase):
    def test_llm_is_initialized_only_on_first_inference_call(self):
        llm = Mock()
        llm.call.return_value = "print('ok')"

        with patch("inference.nexent_client.get_llm_client", return_value=llm) as create_llm:
            client = NexentClient()
            create_llm.assert_not_called()

            result = client.generator_coder("draw a diagram")
            self.assertEqual(result, "print('ok')")
            create_llm.assert_called_once_with()

            client.generator_coder("draw another diagram")
            create_llm.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

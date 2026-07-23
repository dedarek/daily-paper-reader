import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm import AnthropicClient, ClientFactory, create_llm_client


class LlmProviderTest(unittest.TestCase):
    def _anthropic_response(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "content": [{"type": "text", "text": "hello world"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 3, "output_tokens": 2},
        }
        return response

    @patch("llm.requests.post")
    def test_anthropic_messages_shape_and_endpoint(self, mock_post):
        mock_post.return_value = self._anthropic_response()
        client = AnthropicClient(
            api_key="sk-ant-test",
            model="astron-code-latest",
            base_url="https://maas.example.com/anthropic",
        )

        result = client.chat(
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "hello"},
            ]
        )

        self.assertEqual(result["content"], "hello world")
        self.assertEqual(
            mock_post.call_args.args[0],
            "https://maas.example.com/anthropic/v1/messages",
        )
        self.assertEqual(mock_post.call_args.kwargs["headers"]["x-api-key"], "sk-ant-test")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["system"], "Be concise.")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hello"}])
        self.assertNotIn("response_format", payload)

    def test_create_llm_client_selects_provider(self):
        self.assertIsInstance(
            create_llm_client(
                api_key="sk-ant-test",
                model="claude-sonnet",
                base_url="https://api.anthropic.com/v1",
                provider="anthropic",
            ),
            AnthropicClient,
        )
        self.assertEqual(
            type(
                create_llm_client(
                    api_key="test",
                    model="astron-code-latest",
                    base_url="https://maas.example.com/v2",
                    provider="openai-compatible",
                )
            ).__name__,
            "DeepSeekClient",
        )

    @patch.dict(
        "llm.os.environ",
        {
            "LLM_MODEL": "gpt-4.1-mini",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://api.example.com/v2",
            "LLM_PROVIDER": "openai-compatible",
        },
        clear=False,
    )
    def test_client_factory_accepts_openai_compatible(self):
        client = ClientFactory.from_env()
        self.assertEqual(client.model, "gpt-4.1-mini")
        self.assertEqual(client.base_url, "https://api.example.com/v2")


if __name__ == "__main__":
    unittest.main()

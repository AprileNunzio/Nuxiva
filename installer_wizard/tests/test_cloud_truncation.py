import asyncio
import unittest
from unittest import mock

from features.cloud import client
from features.cloud.catalog import BY_ID


def reply(content: str, finish: str = "stop") -> mock.Mock:
    response = mock.Mock(status_code=200, headers={})
    response.json.return_value = {"choices": [{"message": {"content": content}, "finish_reason": finish}], "usage": {"completion_tokens": 5}}
    return response


class Vault:
    def get(self, pid):
        return {"key": "k", "options": {}}

    def configured(self, pid):
        return True


class BodyTest(unittest.TestCase):
    def test_gemini_gets_thinking_headroom_and_low_effort(self):
        spec = BY_ID["gemini"]
        body = client._openai_body(spec, "gemini-2.5-flash", [], "", 300, 0.1, {}, True)
        self.assertEqual(body[spec.token_param], 300 + client.THINKING_HEADROOM["gemini"])
        self.assertEqual(body["reasoning_effort"], "low")

    def test_other_providers_are_untouched(self):
        spec = BY_ID["openai"]
        body = client._openai_body(spec, "gpt-5-mini", [], "", 300, 0.1, {}, True)
        self.assertEqual(body[spec.token_param], 300)
        self.assertNotIn("reasoning_effort", body)


class RetryTest(unittest.TestCase):
    def run_complete(self, responses, json_mode=True):
        posts = mock.AsyncMock(side_effect=responses)
        with mock.patch.object(client, "vault", Vault()), mock.patch.object(client, "_post", posts):
            return asyncio.run(client.complete("cloud:gemini/gemini-2.5-flash", [{"role": "user", "content": "x"}], max_tokens=300, json_mode=json_mode)), posts

    def test_truncated_json_is_retried_with_more_room(self):
        out, posts = self.run_complete([reply('{"speech": "', "length"), reply('{"speech": "ok"}')])
        self.assertEqual(out.text, '{"speech": "ok"}')
        self.assertEqual(posts.await_count, 2)
        first, second = (call.args[1] for call in posts.await_args_list)
        self.assertGreater(second[BY_ID["gemini"].token_param], first[BY_ID["gemini"].token_param])

    def test_second_truncation_is_a_clear_error_not_a_parse_failure(self):
        with self.assertRaises(client.CloudError) as caught:
            self.run_complete([reply('{"a": "', "length"), reply('{"a": "', "length")])
        self.assertIn("troncata", str(caught.exception))

    def test_plain_text_cut_is_not_retried(self):
        out, posts = self.run_complete([reply("una risposta lunga", "length")], json_mode=False)
        self.assertEqual(out.text, "una risposta lunga")
        self.assertEqual(posts.await_count, 1)


if __name__ == "__main__":
    unittest.main()

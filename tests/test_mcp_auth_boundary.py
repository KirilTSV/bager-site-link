"""MCP authentication boundary checks; requires requirements-mcp.txt."""
import asyncio
import unittest
from unittest.mock import Mock
from app.mcp_server import OAuthBoundary, TokenVerifier


class OAuthBoundaryTests(unittest.TestCase):
    def test_missing_bearer_rejected_before_mcp(self):
        inner = Mock()
        boundary = OAuthBoundary(inner, Mock(), {"subject1": "participant1"})
        messages = []

        async def send(message):
            messages.append(message)

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        asyncio.run(boundary({"type": "http", "headers": []}, receive, send))
        self.assertEqual(messages[0]["status"], 401)
        inner.assert_not_called()

    def test_unknown_subject_rejected(self):
        inner = Mock()
        verifier = Mock()
        verifier.verify.return_value = "unknown-subject"
        boundary = OAuthBoundary(inner, verifier, {"known-subject": "participant1"})
        messages = []

        async def send(message):
            messages.append(message)

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        asyncio.run(boundary({"type": "http",
                              "headers": [(b"authorization", b"Bearer token")]},
                             receive, send))
        self.assertEqual(messages[0]["status"], 401)
        inner.assert_not_called()

    def test_invalid_https_configuration_rejected(self):
        with self.assertRaises(ValueError):
            TokenVerifier("http://issuer", "audience", "https://jwks")


if __name__ == "__main__":
    unittest.main()

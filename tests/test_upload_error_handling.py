"""
Tests for the upload error-handling fix in frontend/app.py.

Verifies that a non-JSON (empty or plain-text) error response from the
/api/reports/upload/ endpoint does NOT raise requests.exceptions.JSONDecodeError
and instead returns a safe human-readable error string.
"""

import sys
import os
import types

import pytest

# ---------------------------------------------------------------------------
# Minimal stub so we can import frontend/app.py without a real Streamlit env
# ---------------------------------------------------------------------------

# Stub streamlit before importing app
streamlit_stub = types.ModuleType("streamlit")
streamlit_stub.set_page_config = lambda **kw: None
class _SessionState(dict):
    """dict subclass that also supports attribute-style access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            return None

    def __setattr__(self, key, value):
        self[key] = value


streamlit_stub.session_state = _SessionState()

for attr in (
    "title", "markdown", "error", "success", "info", "warning",
    "caption", "subheader", "divider", "spinner", "expander",
    "text", "text_input", "number_input", "selectbox", "button",
    "chat_input", "chat_message", "file_uploader", "tabs", "sidebar",
    "header", "rerun", "form", "form_submit_button",
):
    setattr(streamlit_stub, attr, lambda *a, **kw: None)

# Provide a context-manager-compatible stub for st.spinner / st.chat_message
class _CM:
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass

streamlit_stub.spinner = lambda *a, **kw: _CM()
streamlit_stub.chat_message = lambda *a, **kw: _CM()
streamlit_stub.expander = lambda *a, **kw: _CM()
streamlit_stub.sidebar = _CM()

sys.modules["streamlit"] = streamlit_stub

# Now import the helper from the frontend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from frontend.app import _safe_json_error  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal fake requests.Response
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code: int, body: bytes = b"", content_type: str = "application/json"):
        self.status_code = status_code
        self._body = body
        self.text = body.decode("utf-8", errors="replace")
        self.headers = {"Content-Type": content_type}

    def json(self):
        import json
        return json.loads(self._body)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSafeJsonError:
    def test_valid_json_error_body(self):
        """When the server returns a JSON error body, it should be stringified."""
        resp = FakeResponse(400, b'{"error": "No file provided."}')
        result = _safe_json_error(resp)
        assert "No file provided" in result

    def test_empty_body_no_exception(self):
        """Empty body (e.g. HTTP 500 with no content) must not raise JSONDecodeError."""
        resp = FakeResponse(500, b"")
        # This must NOT raise
        result = _safe_json_error(resp)
        assert "500" in result or result == ""

    def test_html_body_no_exception(self):
        """An HTML error page must not raise JSONDecodeError."""
        resp = FakeResponse(502, b"<html><body>Bad Gateway</body></html>", "text/html")
        result = _safe_json_error(resp)
        assert "Bad Gateway" in result or "502" in result

    def test_plain_text_body(self):
        """Plain-text error bodies should be returned as-is."""
        resp = FakeResponse(503, b"Service Unavailable", "text/plain")
        result = _safe_json_error(resp)
        assert "Service Unavailable" in result

    def test_returns_string(self):
        """_safe_json_error must always return a string."""
        for body in (b"", b'{"error":"x"}', b"not json"):
            resp = FakeResponse(400, body)
            assert isinstance(_safe_json_error(resp), str)

"""Tests for password validation on registration."""
import sys
import os
import requests
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8001")

def unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


class TestPasswordValidation:
    def _register(self, password, email=None):
        email = email or unique_email()
        return requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "Test User", "email": email, "password": password},
            timeout=10,
        )

    def test_short_password_123_rejected(self):
        r = self._register("123")
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    def test_short_password_1234567_rejected(self):
        r = self._register("1234567")
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

    def test_exactly_8_chars_accepted(self):
        r = self._register("12345678")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "access_token" in r.json(), "No access_token in response"

    def test_strong_password_accepted(self):
        r = self._register("MyStr0ng!Pass")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "access_token" in r.json(), "No access_token in response"

    def test_login_with_accepted_password_works(self):
        pw = "ValidPass1"
        email = unique_email()
        r = self._register(pw, email)
        assert r.status_code == 200, f"Registration failed: {r.status_code} {r.text}"

        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": pw},
            timeout=10,
        )
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        assert "access_token" in r.json(), "No access_token in login response"

    def test_wrong_password_still_rejected(self):
        email = unique_email()
        r = self._register("CorrectPass1", email)
        assert r.status_code == 200

        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": "WrongPass!"},
            timeout=10,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    def test_rejection_message_mentions_password(self):
        r = self._register("short")
        assert r.status_code == 422
        body = r.json()
        assert "detail" in body
        err_text = str(body["detail"]).lower()
        assert "password" in err_text or "8" in err_text, f"Error doesn't mention password: {body['detail']}"


if __name__ == "__main__":
    test = TestPasswordValidation()
    methods = [m for m in dir(test) if m.startswith('test_')]
    passed = 0
    failed = 0
    for method_name in sorted(methods):
        method = getattr(test, method_name)
        try:
            method()
            print(f"  PASS: {method_name}")
            passed += 1
        except (AssertionError, AssertionError) as e:
            print(f"  FAIL: {method_name} - {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {method_name} - {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

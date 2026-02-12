import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response

from api.main import health, query_bq


class _FailingJob:
    def result(self):
        raise RuntimeError("credential path /secret/key.json")


class _FailingClient:
    def query(self, _sql: str):
        return _FailingJob()


class ApiErrorHandlingTests(unittest.TestCase):
    def test_query_bq_does_not_leak_internal_error_details(self):
        with patch("api.main.get_bq_client", return_value=_FailingClient()):
            with self.assertRaises(HTTPException) as err:
                query_bq("SELECT 1")
        self.assertEqual(err.exception.status_code, 500)
        self.assertEqual(err.exception.detail, "BigQuery query failed")

    def test_health_endpoint_returns_503_without_internal_error_details(self):
        with patch("api.main.get_bq_client", return_value=_FailingClient()):
            response = Response()
            body = health(response)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            body,
            {"status": "degraded", "bigquery": "unavailable"},
        )


if __name__ == "__main__":
    unittest.main()

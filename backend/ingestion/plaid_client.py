"""Plaid API client for bank account linking (sandbox-ready)."""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import Settings, get_settings

PLAID_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


class PlaidClient:
    """Minimal Plaid client for transactions sync."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        env = self.settings.plaid_env or "sandbox"
        self.base_url = PLAID_BASE_URLS.get(env, PLAID_BASE_URLS["sandbox"])

    @property
    def configured(self) -> bool:
        return bool(self.settings.plaid_client_id and self.settings.plaid_secret)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return self._mock_transactions()

        body = {
            "client_id": self.settings.plaid_client_id,
            "secret": self.settings.plaid_secret,
            **payload,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self.base_url}{endpoint}", json=body)
            response.raise_for_status()
            return response.json()

    def get_transactions(
        self,
        access_token: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        data = self._post(
            "/transactions/get",
            {
                "access_token": access_token,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return [
            {
                "date": t.get("date"),
                "merchant": t.get("merchant_name") or t.get("name"),
                "amount": -float(t.get("amount", 0)),
                "category": (t.get("category") or ["uncategorized"])[0],
            }
            for t in data.get("transactions", [])
        ]

    @staticmethod
    def _mock_transactions() -> dict[str, Any]:
        """Sandbox fallback when Plaid credentials are not configured."""
        return {
            "transactions": [
                {
                    "date": "2026-05-02",
                    "merchant_name": "Target",
                    "amount": 62.14,
                    "category": ["Shops", "Department Stores"],
                },
                {
                    "date": "2026-05-04",
                    "merchant_name": "PG&E",
                    "amount": 142.88,
                    "category": ["Service", "Utilities"],
                },
            ]
        }

    def fetch_mock_as_list(self) -> list[dict[str, Any]]:
        """Return mock transactions as normalized list (no credentials needed)."""
        raw = self._mock_transactions()
        return [
            {
                "date": t["date"],
                "merchant": t["merchant_name"],
                "amount": -t["amount"],
                "category": t["category"][0],
            }
            for t in raw["transactions"]
        ]

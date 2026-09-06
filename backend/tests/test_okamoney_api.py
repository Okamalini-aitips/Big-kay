"""
Backend regression tests for OkaMoney AI Tips (post-fork verification).
Uses the public preview URL through same-origin /api proxy.
"""
import os
import time
import uuid
import pytest

BASE_URL = "https://repo-to-web-12.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# Existing test creds (from /app/memory/test_credentials.md)
EXISTING_EMAIL = "test@example.com"
EXISTING_PASSWORD = "testpassword123"

# Unique test user for THIS run (fresh DB safe)
UNIQUE_SUFFIX = uuid.uuid4().hex[:8]
NEW_EMAIL = f"TEST_user_{UNIQUE_SUFFIX}@example.com"
NEW_PASSWORD = "TestPass_123!"
NEW_NAME = "TEST Auto User"


# --- health & root
def test_root(api_client):
    r = api_client.get(f"{API}/")
    assert r.status_code == 200
    body = r.json()
    assert "version" in body


def test_api_health(api_client):
    r = api_client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


# --- Auth flow
class TestAuth:
    token = None
    user_id = None

    def test_auth_check_unauth(self, api_client):
        r = api_client.get(f"{API}/auth/check")
        assert r.status_code == 200
        assert r.json().get("authenticated") is False

    def test_register_new_user(self, api_client):
        r = api_client.post(f"{API}/auth/register", json={
            "email": NEW_EMAIL, "password": NEW_PASSWORD, "name": NEW_NAME
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("success") is True
        assert "token" in data and "user" in data
        assert data["user"]["email"] == NEW_EMAIL.lower()
        TestAuth.token = data["token"]
        TestAuth.user_id = data["user"]["id"]

    def test_register_duplicate_fails(self, api_client):
        r = api_client.post(f"{API}/auth/register", json={
            "email": NEW_EMAIL, "password": NEW_PASSWORD, "name": NEW_NAME
        })
        assert r.status_code == 400

    def test_login_wrong_pw(self, api_client):
        r = api_client.post(f"{API}/auth/login", json={
            "email": NEW_EMAIL, "password": "wrongpw!"
        })
        assert r.status_code == 401

    def test_login_success(self, api_client):
        r = api_client.post(f"{API}/auth/login", json={
            "email": NEW_EMAIL, "password": NEW_PASSWORD
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data
        TestAuth.token = data["token"]

    def test_me_with_token(self, api_client):
        assert TestAuth.token, "requires prior login"
        r = api_client.get(f"{API}/auth/me",
                           headers={"Authorization": f"Bearer {TestAuth.token}"})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == NEW_EMAIL.lower()

    def test_me_without_token(self, api_client):
        r = api_client.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_auth_check_authed(self, api_client):
        r = api_client.get(f"{API}/auth/check",
                           headers={"Authorization": f"Bearer {TestAuth.token}"})
        assert r.status_code == 200
        assert r.json().get("authenticated") is True


def _auth_headers():
    return {"Authorization": f"Bearer {TestAuth.token}"} if TestAuth.token else {}


# --- Picks/Games endpoints
class TestPicksGames:
    def test_games(self, api_client):
        r = api_client.get(f"{API}/games?limit=20")
        assert r.status_code == 200
        data = r.json()
        assert "games" in data and isinstance(data["games"], list)
        assert data.get("total", 0) > 0

    def test_picks(self, api_client):
        r = api_client.get(f"{API}/picks")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_yesterday_games(self, api_client):
        r = api_client.get(f"{API}/games/yesterday")
        assert r.status_code == 200
        assert "games" in r.json()

    def test_accumulators(self, api_client):
        r = api_client.get(f"{API}/accumulators")
        assert r.status_code == 200
        assert "accumulators" in r.json()

    def test_sgp(self, api_client):
        r = api_client.get(f"{API}/sgp")
        assert r.status_code == 200
        assert "sgp_picks" in r.json()

    def test_mixed_parlay(self, api_client):
        r = api_client.get(f"{API}/mixed-parlay")
        assert r.status_code == 200
        assert "mixed_parlays" in r.json()

    def test_dc_under(self, api_client):
        r = api_client.get(f"{API}/dc-under")
        assert r.status_code == 200
        assert "dc_under_picks" in r.json()

    def test_dc_over(self, api_client):
        r = api_client.get(f"{API}/dc-over")
        assert r.status_code == 200
        assert "dc_over_picks" in r.json()

    def test_markets(self, api_client):
        r = api_client.get(f"{API}/markets")
        assert r.status_code == 200
        assert "markets" in r.json()


# --- Wallet endpoints (authenticated)
class TestWallet:
    def test_wallet_balance(self, api_client):
        r = api_client.get(f"{API}/wallet/balance", headers=_auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "balance" in data
        assert isinstance(data["balance"], (int, float))

    def test_wallet_packages(self, api_client):
        r = api_client.get(f"{API}/wallet/packages")
        assert r.status_code == 200
        data = r.json()
        assert "packages" in data and len(data["packages"]) > 0
        assert "costs" in data

    def test_wallet_purchase_and_balance(self, api_client):
        # get a package id
        pkgs = api_client.get(f"{API}/wallet/packages").json()["packages"]
        package_id = pkgs[0].get("id") or pkgs[0].get("package_id") or list(pkgs[0].keys())[0]
        # some services return name-keyed dict; find id-like
        for key in ("id", "package_id", "name"):
            if key in pkgs[0]:
                package_id = pkgs[0][key]
                break
        r = api_client.post(
            f"{API}/wallet/purchase",
            params={"package_id": package_id},
            headers=_auth_headers(),
        )
        assert r.status_code == 200, r.text
        # After purchase, balance should be >= 0
        b = api_client.get(f"{API}/wallet/balance", headers=_auth_headers())
        assert b.status_code == 200

    def test_check_daily_free(self, api_client):
        r = api_client.get(
            f"{API}/wallet/check-daily-free",
            params={"feature": "ticket_machine"},
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        assert "available" in r.json()

    def test_wallet_transactions(self, api_client):
        r = api_client.get(f"{API}/wallet/transactions", headers=_auth_headers())
        assert r.status_code == 200
        assert "transactions" in r.json()


# --- WhatsApp
class TestWhatsApp:
    def test_status(self, api_client):
        r = api_client.get(f"{API}/whatsapp/status")
        assert r.status_code == 200
        assert "is_open" in r.json()

    def test_subscriptions_list(self, api_client):
        r = api_client.get(f"{API}/whatsapp/subscriptions", headers=_auth_headers())
        assert r.status_code == 200
        assert "subscriptions" in r.json()

    def test_admin_all_subscriptions(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp/all")
        assert r.status_code == 200
        assert "subscriptions" in r.json()


# --- Admin WhatsApp tickets generator
class TestWhatsAppTicketsGen:
    def test_all_daily(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp-tickets")
        assert r.status_code == 200

    def test_build_a_bet(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp-tickets/build-a-bet")
        assert r.status_code == 200

    def test_mixed_parlay(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp-tickets/mixed-parlay")
        assert r.status_code == 200

    def test_big_odds(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp-tickets/big-odds")
        assert r.status_code == 200

    def test_mega_odds(self, api_client):
        r = api_client.get(f"{API}/admin/whatsapp-tickets/mega-odds")
        assert r.status_code == 200


# --- Ticket Machine
class TestTicketMachine:
    def test_options(self, api_client):
        r = api_client.get(f"{API}/ticket-machine/options")
        assert r.status_code == 200
        data = r.json()
        assert "odds_ranges" in data and "market_types" in data

    def test_generate(self, api_client):
        r = api_client.post(
            f"{API}/ticket-machine/generate",
            params={"odds_range": "safe", "market_type": "all"},
        )
        assert r.status_code == 200, r.text
        assert r.json().get("success") is True

"""Backend tests for the Results Tracker feature (real per-market tracking + admin analytics).

Covers:
- GET /api/results/recent (3-day public cap)
- GET /api/admin/results/stats  (403 without key)
- GET /api/admin/results/pending (403 without key)
- POST /api/admin/results/simulate (403 without key + grades pending)
- POST /api/admin/results/settle (403 without key + updates picks)
- WhatsApp tickets appear in both public /results/recent and admin /pending
"""
import os
from datetime import datetime, timedelta

import pytest
import requests

BASE_URL = os.environ.get("EXPO_BACKEND_URL", "https://soccer-picks-bot.preview.emergentagent.com").rstrip("/")
ADMIN_KEY = "okamoney_admin_2024"


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _yday():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


# ---------------- PUBLIC /api/results/recent ----------------

class TestPublicRecent:
    def test_default_returns_3_days(self, api):
        r = api.get(f"{BASE_URL}/api/results/recent")
        assert r.status_code == 200
        data = r.json()
        assert "days" in data
        assert data.get("max_days") == 3
        assert len(data["days"]) == 3

    def test_days_10_capped_to_3(self, api):
        r = api.get(f"{BASE_URL}/api/results/recent", params={"days": 10})
        assert r.status_code == 200
        data = r.json()
        assert len(data["days"]) <= 3

    def test_day_shape(self, api):
        data = api.get(f"{BASE_URL}/api/results/recent?days=3").json()
        for day in data["days"]:
            assert "date" in day
            summary = day["summary"]
            for k in ("won", "lost", "pending", "settled"):
                assert k in summary, f"summary missing {k}"
            assert "games" in day and isinstance(day["games"], list)
            assert "whatsapp" in day and isinstance(day["whatsapp"], list)

    def test_tip_has_odds_and_selection(self, api):
        data = api.get(f"{BASE_URL}/api/results/recent?days=3").json()
        # gather every tip across all days/games
        tips = [t for d in data["days"] for g in d["games"] for t in g["tips"]]
        assert tips, "Expected tips to exist in games"
        for t in tips:
            assert t.get("selection") is not None
            assert t.get("odds") is not None
            assert t.get("result") in ("won", "lost", "pending", "void", "half_won", "half_lost")

    def test_whatsapp_tickets_present_with_legs(self, api):
        data = api.get(f"{BASE_URL}/api/results/recent?days=3").json()
        wa_count = sum(len(d["whatsapp"]) for d in data["days"])
        assert wa_count > 0, "Expected at least one WhatsApp ticket in the recent window"
        for d in data["days"]:
            for ticket in d["whatsapp"]:
                assert "name" in ticket
                assert isinstance(ticket.get("legs"), list) and len(ticket["legs"]) > 0
                leg0 = ticket["legs"][0]
                for k in ("home", "away", "selection", "odds", "result"):
                    assert k in leg0, f"leg missing {k}"


# ---------------- ADMIN GATING ----------------

class TestAdminGating:
    def test_stats_wrong_key_403(self, api):
        r = api.get(f"{BASE_URL}/api/admin/results/stats", params={"key": "wrong", "days": 30})
        assert r.status_code == 403

    def test_pending_wrong_key_403(self, api):
        r = api.get(f"{BASE_URL}/api/admin/results/pending", params={"key": "wrong"})
        assert r.status_code == 403

    def test_settle_wrong_key_403(self, api):
        r = api.post(
            f"{BASE_URL}/api/admin/results/settle",
            params={"key": "wrong"},
            json={"date": _yday(), "results": {}},
        )
        assert r.status_code == 403

    def test_simulate_wrong_key_403(self, api):
        r = api.post(f"{BASE_URL}/api/admin/results/simulate", params={"key": "wrong"})
        assert r.status_code == 403


# ---------------- ADMIN STATS ----------------

class TestAdminStats:
    def test_stats_30_days_shape(self, api):
        r = api.get(f"{BASE_URL}/api/admin/results/stats", params={"key": ADMIN_KEY, "days": 30}, timeout=90)
        assert r.status_code == 200
        s = r.json()
        for k in ("hit_rate", "won", "settled", "roi", "total_picks", "by_market"):
            assert k in s, f"stats missing {k}"
        assert isinstance(s["by_market"], dict)

    def test_by_market_entry_shape(self, api):
        s = api.get(
            f"{BASE_URL}/api/admin/results/stats",
            params={"key": ADMIN_KEY, "days": 30}, timeout=90
        ).json()
        # There may be zero settled at start; simulate to guarantee data on yesterday
        # then re-check by_market shape after simulate happens in TestAdminSimulate.
        for _mkt, v in s["by_market"].items():
            for k in ("hit_rate", "won", "total", "avg_odds", "roi"):
                assert k in v, f"by_market entry missing {k}"


# ---------------- ADMIN PENDING ----------------

class TestAdminPending:
    def test_pending_flat_list_shape(self, api):
        r = api.get(
            f"{BASE_URL}/api/admin/results/pending",
            params={"key": ADMIN_KEY, "date": _yday()},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("date") == _yday()
        tips = data.get("tips", [])
        assert isinstance(tips, list) and len(tips) > 0
        t = tips[0]
        for k in ("pick_id", "home", "away", "selection", "odds", "result"):
            assert k in t, f"pending tip missing {k}"

    def test_pending_contains_whatsapp_surface(self, api):
        tips = api.get(
            f"{BASE_URL}/api/admin/results/pending",
            params={"key": ADMIN_KEY, "date": _yday()},
        ).json()["tips"]
        surfaces = {t.get("surface") for t in tips}
        assert "whatsapp" in surfaces, f"Expected whatsapp in surfaces, got {surfaces}"


# ---------------- ADMIN SIMULATE + SETTLE ----------------

class TestSimulateAndSettle:
    """Order-dependent flow: simulate yesterday, then settle a single pick manually."""

    def test_simulate_grades_pending(self, api):
        # Use day-2 so we don't collide with settle test below
        target = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        r = api.post(
            f"{BASE_URL}/api/admin/results/simulate",
            params={"key": ADMIN_KEY, "date": target}, timeout=60,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True
        assert data.get("mode") == "simulated"
        # graded may be 0 on repeat runs (already simulated); accept >=0 but require
        # that the pending list for that day is now empty afterwards.
        pending_after = api.get(
            f"{BASE_URL}/api/admin/results/pending",
            params={"key": ADMIN_KEY, "date": target},
        ).json()["tips"]
        pending_ct = sum(1 for t in pending_after if t["result"] == "pending")
        assert pending_ct == 0, "After simulate, no pending tips should remain for that date"

    def test_stats_reflect_settled(self, api):
        r = api.get(
            f"{BASE_URL}/api/admin/results/stats",
            params={"key": ADMIN_KEY, "days": 7}, timeout=90,
        )
        s = r.json()
        assert s.get("settled", 0) > 0, "After simulate, settled must be > 0 for 7-day window"
        assert s.get("total_picks", 0) > 0

    def test_settle_manual_updates(self, api):
        target = _yday()
        # Get a pending pick on yesterday
        pend = api.get(
            f"{BASE_URL}/api/admin/results/pending",
            params={"key": ADMIN_KEY, "date": target},
        ).json()["tips"]
        # Pick the first tip - regardless of current result - and force it to 'void'
        # (idempotent, no impact on hit_rate; verifies update path works).
        assert pend, "Need at least one tip to settle"
        pid = pend[0]["pick_id"]
        r = api.post(
            f"{BASE_URL}/api/admin/results/settle",
            params={"key": ADMIN_KEY},
            json={"date": target, "results": {pid: "void"}},
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("success") is True
        assert d.get("updated", 0) >= 1

        # Verify persistence via GET /pending
        pend2 = api.get(
            f"{BASE_URL}/api/admin/results/pending",
            params={"key": ADMIN_KEY, "date": target},
        ).json()["tips"]
        updated = next((t for t in pend2 if t["pick_id"] == pid), None)
        assert updated is not None
        assert updated["result"] == "void", f"Expected 'void' after settle, got {updated['result']}"

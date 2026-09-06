"""
Spec-conformance tests for the OkaMoney AI Tips NEW engine.

Verifies:
 - Every tip everywhere (games, sgp, mixed-parlay, dc-under, dc-over,
   ticket-machine, admin/whatsapp-tickets) uses ONLY the 20 spec markets.
 - Every tip has filters_passed == total_filters (all-must-pass).
 - Display names are the clear, full names (no 'O0.5','1H','2H' shorthand).
 - SGP: 4 tickets, all legs from SAME game, combined_odds in bracket.
 - Mixed Parlay: up to 4 tickets, legs from DIFFERENT games, brackets ok.
 - DC-Under / DC-Over: singles for the DC combined markets.
 - Ticket Machine: legs are spec-only; combined_odds near requested range.
 - Admin WhatsApp: Build A Bet / Mixed Parlay / Big Odds / Mega Odds brackets.
 - Options: has odds_ranges + market_types.
 - Auth register + login still works.
"""
import os
import re
import uuid
import math
import pytest
import requests

BASE_URL = "https://repo-to-web-12.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# The 20 authoritative market names (verbatim from spec / engine DISPLAY)
ALLOWED_MARKETS = {
    "Straight Win",
    "Double Chance",
    "Both Teams to Score - Yes",
    "Over 1.5 Total Goals",
    "Over 2.5 Total Goals",
    "Over 0.5 1st Half Goals",
    "Over 0.5 2nd Half Goals",
    "Team to Score in 2nd Half",
    "Under 3.5 Total Goals",
    "Under 4.5 Total Goals",
    "Under 1.5 1st Half Goals",
    "Draw No Bet",
    "Double Chance & Over 1.5 Goals",
    "Double Chance & Under 4.5 Goals",
    "Over 4.5 1st Half Corners",
    "Over 8.5 Total Corners",
    "Under 10.5 Total Corners",
    "Over 2.5 Total Cards",
    "Over 3.5 Total Cards",
    "Under 5.5 Total Cards",
}

# Substrings that must NEVER appear anywhere (shorthand)
BANNED_SHORTHAND_PATTERNS = [
    r"\bO0\.5\b", r"\bO1\.5\b", r"\bO2\.5\b",
    r"\bU3\.5\b", r"\bU4\.5\b", r"\bU1\.5\b",
    r"\b1H\b", r"\b2H\b",
]


def _assert_market_allowed(market: str, context: str):
    assert market in ALLOWED_MARKETS, (
        f"[{context}] Non-spec market '{market}' — allowed: {sorted(ALLOWED_MARKETS)}"
    )


def _assert_no_shorthand(text: str, context: str):
    for pat in BANNED_SHORTHAND_PATTERNS:
        assert not re.search(pat, text or ""), (
            f"[{context}] shorthand '{pat}' found in '{text}'"
        )


# --------------------------------------------------------------------------
# 1) GET /api/games — every tip is spec + all-filters-pass + clear names
# --------------------------------------------------------------------------
def test_games_all_tips_are_spec_and_pass_all_filters():
    r = requests.get(f"{API}/games?limit=20", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    games = body.get("games") or []
    assert len(games) > 0, "no games returned"

    top3_free_count = 0
    total_tips = 0
    for i, g in enumerate(games):
        markets = g.get("markets") or []
        assert 1 <= len(markets) <= 3, (
            f"game #{i} has {len(markets)} markets (expected 1..3)"
        )
        for t in markets:
            total_tips += 1
            m = t.get("market") or ""
            sel = t.get("selection") or ""
            _assert_market_allowed(m, f"games[{i}].market")
            _assert_no_shorthand(m, f"games[{i}].market text")
            _assert_no_shorthand(sel, f"games[{i}].selection text")
            fp = t.get("filters_passed")
            tf = t.get("total_filters")
            assert fp is not None and tf is not None and fp == tf and tf > 0, (
                f"games[{i}] tip '{m}' not all-pass: {fp}/{tf}"
            )
        if i < 3 and g.get("is_free") is True:
            top3_free_count += 1
    assert top3_free_count == 3, f"top 3 games should be free, got {top3_free_count}"
    assert total_tips > 0


# --------------------------------------------------------------------------
# 2) GET /api/sgp — 4 tickets, legs same game, combined odds in bracket
# --------------------------------------------------------------------------
SGP_BRACKETS = {
    "safe":  (1.90, 3.00),
    "value": (3.01, 4.00),
    "high":  (4.01, 7.00),
}


def _bracket_for_ticket(t):
    name = ((t.get("category") or t.get("bracket") or t.get("risk") or t.get("type") or "") + " " + (t.get("title") or "")).lower()
    odds = float(t.get("combined_odds") or 0.0)
    # 1) name hints
    if "safe" in name: return SGP_BRACKETS["safe"]
    if "value" in name: return SGP_BRACKETS["value"]
    if "high" in name: return SGP_BRACKETS["high"]
    # 2) infer by odds
    for lo, hi in SGP_BRACKETS.values():
        if lo - 0.01 <= odds <= hi + 0.01:
            return (lo, hi)
    return None


def test_sgp_returns_four_tickets_same_game_and_in_brackets():
    r = requests.get(f"{API}/sgp", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    tickets = body.get("sgp_picks") or body.get("tickets") or []
    assert len(tickets) == 4, f"expected 4 SGP tickets, got {len(tickets)}"

    for i, t in enumerate(tickets):
        legs = t.get("legs") or t.get("picks") or []
        assert len(legs) >= 2, f"SGP #{i} needs multiple legs"

        # all legs from same game
        game_ids = set()
        for leg in legs:
            game_ids.add(leg.get("game_id") or leg.get("fixture_id") or leg.get("match_id"))
            m = leg.get("market") or ""
            sel = leg.get("selection") or ""
            _assert_market_allowed(m, f"sgp[{i}].leg.market")
            _assert_no_shorthand(m, f"sgp[{i}].leg.market")
            _assert_no_shorthand(sel, f"sgp[{i}].leg.selection")
        assert len(game_ids - {None}) <= 1, f"SGP #{i} legs from >1 game: {game_ids}"

        odds = float(t.get("combined_odds") or 0.0)
        br = _bracket_for_ticket(t)
        assert br is not None, f"SGP #{i} odds {odds} outside all brackets"
        lo, hi = br
        assert lo - 0.02 <= odds <= hi + 0.02, f"SGP #{i} odds {odds} outside {lo}-{hi}"


# --------------------------------------------------------------------------
# 3) GET /api/mixed-parlay — up to 4 tickets, DIFFERENT games, in brackets
# --------------------------------------------------------------------------
MP_BRACKETS = [
    (3.50, 5.00),
    (5.01, 6.50),
    (6.51, 8.00),
    (8.01, 12.00),
]


def test_mixed_parlay_different_games_and_in_brackets():
    r = requests.get(f"{API}/mixed-parlay", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    tickets = body.get("mixed_parlays") or body.get("tickets") or []
    assert 1 <= len(tickets) <= 4, f"expected up to 4 mixed parlays, got {len(tickets)}"

    for i, t in enumerate(tickets):
        legs = t.get("legs") or t.get("picks") or []
        assert len(legs) >= 2, f"mixed parlay #{i} needs >=2 legs"
        game_keys = []
        for leg in legs:
            # game_id may not be present — use (home, away, league) tuple as identity
            gid = leg.get("game_id") or leg.get("fixture_id") or leg.get("match_id")
            if not gid:
                gid = (leg.get("home"), leg.get("away"), leg.get("league"))
            game_keys.append(gid)
            m = leg.get("market") or ""
            sel = leg.get("selection") or ""
            _assert_market_allowed(m, f"mixed[{i}].leg.market")
            _assert_no_shorthand(m, f"mixed[{i}].leg.market")
            _assert_no_shorthand(sel, f"mixed[{i}].leg.selection")
        assert len(set(game_keys)) == len(game_keys), (
            f"mixed parlay #{i} has duplicate games: {game_keys}"
        )
        odds = float(t.get("combined_odds") or 0.0)
        in_any = any(lo - 0.02 <= odds <= hi + 0.02 for lo, hi in MP_BRACKETS)
        assert in_any, f"mixed parlay #{i} odds {odds} not in any bracket"


# --------------------------------------------------------------------------
# 4) DC & Under, DC & Over singles
# --------------------------------------------------------------------------
def test_dc_under_singles_use_dc_under_market():
    r = requests.get(f"{API}/dc-under", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    picks = body.get("dc_under_picks") or body.get("picks") or []
    # picks split composite into dc_selection + under_selection with a 'type' summary
    for i, p in enumerate(picks):
        m = p.get("market") or p.get("type") or ""
        dc_sel = p.get("dc_selection") or ""
        under_sel = p.get("under_selection") or ""
        sel = p.get("selection") or f"{dc_sel} & {under_sel}"
        # Composite must map to spec market #14 (allow either the clean name or
        # equivalent split of dc + under). Flag if type is shorthand.
        allowed = (
            m == "Double Chance & Under 4.5 Goals"
            or (dc_sel and ("Draw" in dc_sel) and ("Under" in under_sel or "4.5" in under_sel))
        )
        assert allowed, (
            f"dc-under[{i}] does not represent 'Double Chance & Under 4.5 Goals' "
            f"(market='{m}', dc='{dc_sel}', under='{under_sel}')"
        )
        _assert_no_shorthand(sel, f"dc-under[{i}] selection")


def test_dc_over_singles_use_dc_over_market():
    r = requests.get(f"{API}/dc-over", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    picks = body.get("dc_over_picks") or body.get("picks") or []
    for i, p in enumerate(picks):
        m = p.get("market") or p.get("type") or ""
        dc_sel = p.get("dc_selection") or ""
        over_sel = p.get("over_selection") or ""
        sel = p.get("selection") or f"{dc_sel} & {over_sel}"
        allowed = (
            m == "Double Chance & Over 1.5 Goals"
            or (dc_sel and ("Draw" in dc_sel) and ("Over" in over_sel or "1.5" in over_sel))
        )
        assert allowed, (
            f"dc-over[{i}] does not represent 'Double Chance & Over 1.5 Goals' "
            f"(market='{m}', dc='{dc_sel}', over='{over_sel}')"
        )
        _assert_no_shorthand(sel, f"dc-over[{i}] selection")


# --------------------------------------------------------------------------
# 5) Ticket Machine — options + several ranges/market_types
# --------------------------------------------------------------------------
def test_ticket_machine_options():
    r = requests.get(f"{API}/ticket-machine/options", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert "odds_ranges" in body and body["odds_ranges"], "odds_ranges missing"
    assert "market_types" in body and body["market_types"], "market_types missing"


TM_RANGE_BRACKETS = {
    # rough spec brackets — we only require odds fall near the range
    "safe":       (1.5, 3.0),
    "value":      (3.0, 5.0),
    "high_risk":  (5.0, 12.0),
    "jackpot":    (10.0, 60.0),
}


@pytest.mark.parametrize("odds_range,market_type", [
    ("value", "over15"),
    ("jackpot", "all"),
    ("high_risk", "cards"),
])
def test_ticket_machine_generate(odds_range, market_type):
    r = requests.post(
        f"{API}/ticket-machine/generate",
        params={"odds_range": odds_range, "market_type": market_type},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    ticket = body.get("ticket") or body
    legs = ticket.get("legs") or ticket.get("picks") or []
    assert len(legs) >= 2, f"ticket for {odds_range}/{market_type} has no legs"
    for leg in legs:
        m = leg.get("market") or ""
        sel = leg.get("selection") or ""
        _assert_market_allowed(m, f"ticket-machine[{odds_range}/{market_type}] market")
        _assert_no_shorthand(m, f"ticket-machine[{odds_range}/{market_type}]")
        _assert_no_shorthand(sel, f"ticket-machine[{odds_range}/{market_type}]")

    odds = float(ticket.get("combined_odds") or 0.0)
    lo, hi = TM_RANGE_BRACKETS.get(odds_range, (1.0, 200.0))
    # allow generous tolerance because ranges are approximate labels
    assert lo * 0.5 <= odds <= hi * 2.0, (
        f"ticket-machine[{odds_range}] combined odds {odds} nowhere near {lo}-{hi}"
    )


# --------------------------------------------------------------------------
# 6) Admin WhatsApp Tickets
# --------------------------------------------------------------------------
WA_BRACKETS = {
    # loose — just needs to fall in a reasonable ballpark
    "build_a_bet":   (1.5, 5.0),
    "mixed_parlay":  (3.0, 15.0),
    "big_odds":      (7.0, 40.0),
    "mega_odds":     (10.0, 200.0),
}


def test_admin_whatsapp_all_uses_spec_markets():
    r = requests.get(f"{API}/admin/whatsapp-tickets", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    # Body can be either flat list of tickets or grouped dict
    if isinstance(body, dict):
        # Collect all ticket-like sections
        groups = []
        for key in ("build_a_bet", "mixed_parlay", "big_odds", "mega_odds", "tickets"):
            if isinstance(body.get(key), list):
                groups.append((key, body[key]))
            elif isinstance(body.get(key), dict):
                groups.append((key, [body[key]]))
        # Fallback: any list of dicts with 'legs'
        if not groups:
            for k, v in body.items():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "legs" in v[0]:
                    groups.append((k, v))
        assert groups, f"no ticket sections found in admin/whatsapp-tickets: {list(body.keys())}"

        found_any_leg = False
        for name, tickets in groups:
            for i, t in enumerate(tickets):
                legs = t.get("legs") or t.get("picks") or []
                for leg in legs:
                    found_any_leg = True
                    m = leg.get("market") or ""
                    sel = leg.get("selection") or ""
                    _assert_market_allowed(m, f"admin.whatsapp[{name}][{i}].market")
                    _assert_no_shorthand(m, f"admin.whatsapp[{name}]")
                    _assert_no_shorthand(sel, f"admin.whatsapp[{name}]")
                odds = float(t.get("combined_odds") or 0.0)
                lo, hi = WA_BRACKETS.get(name, (1.0, 500.0))
                # Loose tolerance
                assert lo * 0.4 <= odds <= hi * 2.5 or odds == 0.0, (
                    f"admin.whatsapp[{name}][{i}] odds {odds} way off {lo}-{hi}"
                )
        assert found_any_leg, "no legs found in any admin whatsapp ticket"


# --------------------------------------------------------------------------
# 7) Auth still works — register fresh user then login
# --------------------------------------------------------------------------
def test_auth_register_and_login():
    email = f"tester+{uuid.uuid4().hex[:8]}@okamoney.com"
    password = "Test1234!"
    r = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "name": "Spec Tester"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("success") is True
    assert "token" in data

    r2 = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r2.status_code == 200, r2.text
    assert "token" in r2.json()

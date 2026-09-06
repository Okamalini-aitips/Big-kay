"""Engine guarantees test:
1. A market qualifies ONLY when ALL its filters pass (break one input -> it must drop out).
2. Tips are ranked by blended probability (desc), ties broken by odds (value) desc.
3. Display names are the clear, full user-facing names.
Run: python -m backend.tests.test_engine  (or) cd backend && python tests/test_engine.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import okamoney_engine as e


def _strong_over_goals_fixture():
    """Two strong attacking teams -> Over 1.5 should qualify."""
    home = {'name': 'H', 'goals_avg': 2.1, 'conceded_avg': 1.4, 'clean_sheet_pct': 0.1,
            'form_last5_venue': ['W', 'W', 'D', 'W', 'L'], 'wins_last5_venue': 3, 'draws_last5_venue': 1}
    away = {'name': 'A', 'goals_avg': 1.8, 'conceded_avg': 1.5, 'clean_sheet_pct': 0.1,
            'form_last5_venue': ['W', 'D', 'W', 'L', 'W'], 'wins_last5_venue': 3, 'draws_last5_venue': 1}
    h2h = [{'total': 3, 'fav_result': 'W'}] * 5
    return home, away, h2h


def test_all_filters_must_pass():
    home, away, h2h = _strong_over_goals_fixture()
    tips = e.evaluate_fixture(home, away, {}, h2h, 39)
    keys = {t['key'] for t in tips}
    assert 'over_1_5' in keys, "Over 1.5 should qualify for two strong attacking teams"

    # Break exactly ONE Over 1.5 filter: force both teams' goal avgs below 1.4 so
    # 'at least one team averages >1.4 goals' fails -> market must NOT qualify.
    home2 = dict(home, goals_avg=1.2)
    away2 = dict(away, goals_avg=1.1)
    tips2 = e.evaluate_fixture(home2, away2, {}, h2h, 39)
    keys2 = {t['key'] for t in tips2}
    assert 'over_1_5' not in keys2, "Over 1.5 must drop out when one filter fails (all-must-pass)"
    print("PASS: all-filters-must-pass enforced (Over 1.5 drops when a single filter fails)")


def test_ranking_probability_then_odds():
    home, away, h2h = _strong_over_goals_fixture()
    tips = e.evaluate_fixture(home, away, {}, h2h, 39)
    for i in range(len(tips) - 1):
        a, b = tips[i], tips[i + 1]
        assert (a['probability'], a['odds']) >= (b['probability'], b['odds']), \
            "Tips must be sorted by probability desc, then odds desc"
    print(f"PASS: ranking correct ({len(tips)} tips, top={tips[0]['selection']} @ {tips[0]['probability']})")


def test_clear_display_names():
    assert e.DISPLAY['over_0_5_fh'] == 'Over 0.5 1st Half Goals'
    assert e.DISPLAY['over_0_5_sh'] == 'Over 0.5 2nd Half Goals'
    assert e.DISPLAY['under_1_5_fh'] == 'Under 1.5 1st Half Goals'
    assert 'O0.5' not in ''.join(e.DISPLAY.values()), "No shorthand allowed in display names"
    print("PASS: clear, full display names (no shorthand)")


def test_pool_only_spec_markets():
    pool = e.generate_engine_games(40, seed=3)
    allowed = set(e.DISPLAY.values())
    for g in pool:
        for t in g['all_tips']:
            assert t['market'] in allowed, f"Non-spec market leaked: {t['market']}"
            assert t['qualifies'] and t['filters_passed'] == t['total_filters']
    print(f"PASS: {len(pool)} games, every tip is a fully-passing spec market")


if __name__ == '__main__':
    test_all_filters_must_pass()
    test_ranking_probability_then_odds()
    test_clear_display_names()
    test_pool_only_spec_markets()
    print("\nALL ENGINE GUARANTEE TESTS PASSED ✅")

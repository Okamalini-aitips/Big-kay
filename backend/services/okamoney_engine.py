"""
OkaMoney Betting Engine — SINGLE SOURCE OF TRUTH for tip selection.

Implements the USER's 20 markets with their EXACT filters. A market qualifies as a
tip for a game ONLY when ALL of its filters pass (no partial passes, no scoring
shortcuts). When multiple markets qualify for one game, they are ranked by a BLENDED
probability = league hit-rate combined with how strongly the filters passed.
Probability always overrides value; ties are broken by the most valuable (highest odds).

⛔⛔⛔  DO NOT ALTER ANY THRESHOLD, FILTER, OR RULE WITHOUT THE USER'S EXPLICIT CONSENT.
The authoritative spec is /app/OKAMONEY_MARKET_SPEC_USER.md — if code and that file ever
disagree, the file wins and the code is the bug. Every numeric threshold lives in the
THRESHOLDS (`TH`) block below so it can be audited at a glance.
"""
import math
import random
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# ⛔ PROTECTED THRESHOLDS  (DO NOT ALTER WITHOUT USER CONSENT)
# Each constant maps 1:1 to a filter in OKAMONEY_MARKET_SPEC_USER.md
# ============================================================================
class TH:
    # --- 1. Straight Win ---
    SW_FAV_ODDS_MAX = 2.20            # favourite odds below 2.20
    SW_ODDS_GAP_MIN = 0.80            # odds gap over 0.80
    SW_FAV_PPG_MIN = 1.60            # favourite PPG over 1.60 (venue)
    SW_MATCH_XG_MIN = 1.8            # match xG over 1.8
    SW_FAV_XG_MIN = 1.5            # favourite xG over 1.5
    SW_FAV_WINS_L5_MIN = 3            # favourite won over 2 (=>3) of last 5 (venue)
    SW_DOG_LOSSES_L5_MIN = 2            # underdog lost over 1 (=>2) of last 5 (venue)

    # --- 2. Double Chance ---
    DC_FAV_UNBEATEN_L5_MIN = 3            # unbeaten in at least 3 of last 5
    DC_FAV_H2H_WINS_MIN = 2            # won at least 2 of last 5 H2H
    DC_FAV_PPG_MIN = 1.30            # favourite PPG over 1.3 (venue)
    DC_DOG_WINS_L5_MAX = 1            # underdog won no more than 1 in last 5

    # --- 3. Both Teams To Score ---
    BTTS_HOME_SCORE_PCT_MIN = 0.60            # home scored in >60% home games
    BTTS_AWAY_SCORE_PCT_MIN = 0.60            # away scored in >60% away games
    BTTS_BOTH_CONCEDE_OF5_MIN = 4            # both conceded >=1 goal in 4 of last 5
    BTTS_MATCH_XG_MIN = 2.5            # match xG over 2.5
    BTTS_H2H_BTTS_MIN = 3            # Both Teams To Score in at least 3 of last 5 H2H (approved swap)
    BTTS_H2H_GAMES = 5

    # --- 4. Over 1.5 Total Goals ---
    O15_MATCH_XG_MIN = 2.5
    O15_ONE_TEAM_GOALS_MIN = 1.4            # at least one team avg >1.4
    O15_ONE_TEAM_CS_PCT_MAX = 0.30            # at least one team <30% clean sheets (L10)
    O15_BOTH_OVER15_OF5_MIN = 4            # both in games producing >1.5 goals in 4 of L5

    # --- 5. Over 2.5 Total Goals ---
    O25_COMBINED_GOALS_MIN = 2.8
    O25_ONE_TEAM_GOALS_MIN = 1.3
    O25_ONE_TEAM_CS_PCT_MAX = 0.30
    O25_BOTH_SCORED_OF10_MIN = 7            # both scored >=1 in 7 of last 10

    # --- 6. Over 0.5 First Half Goals ---
    O05FH_COMBINED_FH_MIN = 1.0
    O05FH_ONE_SCORED_FH_OF5_MIN = 3            # one team scored FH goal in 3 of L5
    O05FH_ONE_CONCEDED_FH_OF5_MIN = 3            # one team conceded FH goal in 3 of L5
    O05FH_BOTH_SCORED_FH_OF10_MIN = 4            # both scored FH in 4 of L10
    O05FH_MATCH_XG_MIN = 2.5

    # --- 7. Over 0.5 Second Half Goals ---
    O05SH_COMBINED_SH_MIN = 1.1
    O05SH_ONE_TEAM_SH_MIN = 0.6            # one team scores >0.6 SH goals
    O05SH_ONE_SCORED_SH_OF5_MIN = 4            # one team scored SH goal in 4 of L5
    O05SH_MATCH_XG_MIN = 2.5

    # --- 8. Team To Score Over 0.5 Second Half Goals ---
    T2H_PPG_MIN = 1.30
    T2H_MATCH_XG_MIN = 1.7            # backed team xG over 1.7 for the whole match
    T2H_SH_GOALS_MIN = 0.7            # backed team avg >0.7 SH goals
    T2H_SCORED_SH_OF5_MIN = 4            # backed team scored SH goal in 4 of L5

    # --- 9. Under 3.5 Total Goals ---
    U35_MATCH_XG_MAX = 3.5
    U35_BOTH_U25_OF10_MIN = 4            # both had <2.5 total in 4 of L10
    U35_H2H_U25_OF5_MIN = 2            # <2.5 total in 2 of last 5 H2H
    U35_CS_HIGH_MIN = 0.20            # one team >20% CS (L10)
    U35_CS_LOW_MIN = 0.10            # other team >10% CS (L10)
    U35_BOTH_CONCEDE_MAX = 1.3            # both concede <1.3 avg

    # --- 10. Under 4.5 Total Goals ---
    U45_MATCH_XG_MAX = 3.8
    U45_ONE_CONCEDE_MAX = 1.1            # one team concedes <1.1 avg
    U45_H2H_U35_OF5_MIN = 3            # <3.5 total in 3 of last 5 H2H
    U45_CS_HIGH_MIN = 0.20
    U45_CS_LOW_MIN = 0.10

    # --- 11. Under 1.5 First Half Goals ---
    U15FH_BOTH_U15_PCT_MIN = 0.50            # both <1.5 FH in 50% of L10
    U15FH_BOTH_FTS_FH_OF5_MIN = 2            # both failed to score FH in 2 of L5
    U15FH_ONE_FH_CS_PCT_MIN = 0.30            # one team 30% FH clean sheet
    U15FH_BOTH_OVERALL_HITRATE_MIN = 0.40            # both overall <1.5 FH hit rate >40% (L10)

    # --- 12. Draw No Bet ---
    DNB_FAV_ODDS_MAX = 2.50
    DNB_FAV_PPG_MIN = 1.2
    DNB_FAV_H2H_NOT_LOST_LAST = 3            # not lost in last 3 H2H
    DNB_FAV_WINS_L5_MIN = 2            # won at least 2 of last 5 (venue)
    DNB_DOG_LOSSES_L5_MIN = 1            # underdog lost at least 1 of last 5 (venue)

    # --- 13. Double Chance & Over 1.5 Goals ---
    DCO15_FAV_ODDS_MAX = 2.20
    DCO15_FAV_PPG_MIN = 1.5
    DCO15_MATCH_XG_MIN = 2.5
    DCO15_ONE_TEAM_GOALS_MIN = 1.2
    DCO15_FAV_UNBEATEN_L5_MIN = 2            # not lost in 2 of last 5 (=> unbeaten >=2)

    # --- 14. Double Chance & Under 4.5 Goals ---
    DCU45_FAV_ODDS_MAX = 2.20
    DCU45_FAV_PPG_MIN = 1.5
    DCU45_FAV_UNBEATEN_L5_MIN = 3
    DCU45_MATCH_XG_MAX = 3.5
    DCU45_BOTH_GOALS_MAX = 1.3

    # --- 15. Over 4.5 First Half Corners ---
    O45FHC_ONE_FH_POSS_MIN = 55.0            # one team >55% FH possession (L5)
    O45FHC_ONE_FH_SHOTS_MIN = 6.0            # one team avg >6 total FH shots
    O45FHC_ONE_WON_35_OF10_MIN = 5            # one won >3.5 FH corners in 5 of L10
    O45FHC_ONE_CONCEDED_25_OF5_MIN = 3            # one conceded >2.5 FH corners in 3 of L5

    # --- 16. Over 8.5 Total Corners ---
    O85C_ONE_POSS_MIN = 55.0
    O85C_ONE_SHOTS_MIN = 12.0
    O85C_ONE_WON_65_OF10_MIN = 5            # one won >6.5 total corners in 5 of L10
    O85C_ONE_CONCEDED_55_OF5_MIN = 3            # one conceded >5.5 total corners in 3 of L5

    # --- 17. Under 10.5 Total Corners ---
    U105C_BOTH_POSS_MAX = 52.0
    U105C_COMBINED_SHOTS_MAX = 23.0
    U105C_ONE_U105_OF10_MIN = 6            # one in games <10.5 total corners in 6 of L10
    U105C_BOTH_CORNERS_FOR_MAX = 5.0            # both average <5.0 total corners won per game (approved swap)

    # --- 18. Over 2.5 Total Cards ---
    O25CD_ONE_FOULS_MIN = 16.0
    O25CD_COMBINED_FOULS_MIN = 23.0
    O25CD_ONE_CARDS_MIN = 1.8
    O25CD_ONE_TACKLES_MIN = 15.0

    # --- 19. Over 3.5 Total Cards ---
    O35CD_BOTH_TACKLES_MIN = 13.0
    O35CD_COMBINED_FOULS_MIN = 26.0
    O35CD_BOTH_CARDS_MIN = 1.7
    O35CD_BOTH_TACKLES_MIN2 = 12.0

    # --- 20. Under 5.5 Total Cards ---
    U55CD_ONE_FOULS_MAX = 15.0
    U55CD_COMBINED_FOULS_MAX = 23.0
    U55CD_ONE_CARDS_MAX = 2.0
    U55CD_COMBINED_TACKLES_MAX = 28.0


# Blended-probability weights (probability overrides value; ties -> highest odds)
FILTER_SWING = 18.0        # how much filter strength (0..1) nudges around the league base
PROB_FLOOR, PROB_CEIL = 45.0, 95.0

# Clear, user-facing display names (no shorthand)
DISPLAY = {
    'straight_win': 'Straight Win',
    'double_chance': 'Double Chance',
    'btts': 'Both Teams to Score - Yes',
    'over_1_5': 'Over 1.5 Total Goals',
    'over_2_5': 'Over 2.5 Total Goals',
    'over_0_5_fh': 'Over 0.5 1st Half Goals',
    'over_0_5_sh': 'Over 0.5 2nd Half Goals',
    'team_2h': 'Team to Score in 2nd Half',
    'under_3_5': 'Under 3.5 Total Goals',
    'under_4_5': 'Under 4.5 Total Goals',
    'under_1_5_fh': 'Under 1.5 1st Half Goals',
    'dnb': 'Draw No Bet',
    'dc_over_1_5': 'Double Chance & Over 1.5 Goals',
    'dc_under_4_5': 'Double Chance & Under 4.5 Goals',
    'over_4_5_fh_corners': 'Over 4.5 1st Half Corners',
    'over_8_5_corners': 'Over 8.5 Total Corners',
    'under_10_5_corners': 'Under 10.5 Total Corners',
    'over_2_5_cards': 'Over 2.5 Total Cards',
    'over_3_5_cards': 'Over 3.5 Total Cards',
    'under_5_5_cards': 'Under 5.5 Total Cards',
}

# League base hit-rate per market (%) — the "league/competition probability" input to the
# blend. A neutral, documented baseline; adjusted lightly by league goal index below.
LEAGUE_BASE = {
    'straight_win': 60, 'double_chance': 74, 'btts': 58, 'over_1_5': 78, 'over_2_5': 60,
    'over_0_5_fh': 74, 'over_0_5_sh': 80, 'team_2h': 70, 'under_3_5': 68, 'under_4_5': 80,
    'under_1_5_fh': 66, 'dnb': 66, 'dc_over_1_5': 70, 'dc_under_4_5': 72,
    'over_4_5_fh_corners': 58, 'over_8_5_corners': 62, 'under_10_5_corners': 62,
    'over_2_5_cards': 60, 'over_3_5_cards': 55, 'under_5_5_cards': 66,
}

# Default fair odds per market (for value tie-break and ticket odds). Straight-win / DNB /
# DC variants override with the real favourite odds when available.
BASE_ODDS = {
    'straight_win': 1.75, 'double_chance': 1.25, 'btts': 1.75, 'over_1_5': 1.28,
    'over_2_5': 1.80, 'over_0_5_fh': 1.20, 'over_0_5_sh': 1.22, 'team_2h': 1.45,
    'under_3_5': 1.45, 'under_4_5': 1.20, 'under_1_5_fh': 1.45, 'dnb': 1.45,
    'dc_over_1_5': 1.50, 'dc_under_4_5': 1.42, 'over_4_5_fh_corners': 1.90,
    'over_8_5_corners': 1.75, 'under_10_5_corners': 1.72, 'over_2_5_cards': 1.72,
    'over_3_5_cards': 2.00, 'under_5_5_cards': 1.30,
}

# Which markets are corner/card markets (only meaningful where such data exists)
CORNER_CARD_KEYS = {'over_4_5_fh_corners', 'over_8_5_corners', 'under_10_5_corners',
                    'over_2_5_cards', 'over_3_5_cards', 'under_5_5_cards'}

# Light per-league goal index (avg goals) to nudge the league base. Default 2.6.
LEAGUE_GOAL_INDEX = {
    39: 2.8, 140: 2.5, 135: 2.7, 78: 3.1, 61: 2.6, 88: 3.2, 94: 2.5, 144: 2.9,
    40: 2.5, 79: 3.0, 141: 2.3, 179: 2.7, 203: 2.8, 2: 2.9, 3: 2.8, 848: 2.7,
}

FH_SHARE = 0.45  # documented: first half accounts for ~45% of a team's goals for/against


# ---------------------------------------------------------------------------
# Poisson helpers (documented estimation basis)
# ---------------------------------------------------------------------------
def _pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _p_at_least_one(lam: float) -> float:
    return 1.0 - math.exp(-max(lam, 0.0))


def _p_ge(k: int, lam: float) -> float:
    # P(X >= k)
    return max(0.0, 1.0 - sum(_pmf(i, lam) for i in range(0, k)))


def _p_le(k: int, lam: float) -> float:
    # P(X <= k)
    return min(1.0, sum(_pmf(i, lam) for i in range(0, k + 1)))


def _count_of(rate: float, n: int) -> int:
    return int(math.floor(max(0.0, min(1.0, rate)) * n + 0.5))


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Team normalization / estimation layer
# ---------------------------------------------------------------------------
def normalize_team(raw: Dict, venue: str) -> Dict:
    """Turn a raw stats dict (sparse real data OR rich synthetic) into a full team view.
    Missing stats are ESTIMATED with a documented, consistent method — thresholds are
    never touched. `venue` is 'home' or 'away'."""
    g = float(raw.get('goals_avg', 1.3) or 1.3)
    c = float(raw.get('conceded_avg', 1.2) or 1.2)
    played = max(int(raw.get('played', 10) or 10), 1)

    # Venue-specific goals (home boost / away reduction if splits absent)
    gf = float(raw.get('home_goals_avg' if venue == 'home' else 'away_goals_avg',
                        g * (1.10 if venue == 'home' else 0.90)))
    ga = float(raw.get('home_conceded_avg' if venue == 'home' else 'away_conceded_avg',
                        c * (0.90 if venue == 'home' else 1.10)))

    # Points per game (venue-specific). Prefer explicit, else derive from record.
    ppg = raw.get('ppg_home' if venue == 'home' else 'ppg_away')
    if ppg is None:
        w = raw.get('wins_last5_venue'); d = raw.get('draws_last5_venue')
        if w is not None and d is not None:
            ppg = (w * 3 + d) / 5.0
        else:
            base_ppg = (int(raw.get('wins', 4)) * 3 + int(raw.get('draws', 3))) / played
            ppg = base_ppg * (1.05 if venue == 'home' else 0.95)
    ppg = _clamp(float(ppg), 0.0, 3.0)

    # Venue form (last 5): explicit arrays preferred, else derive from ppg
    results = raw.get('form_last5_venue') or raw.get('form_last5')
    if not results:
        # derive a plausible W/D/L split from ppg
        wins = _clamp(int(round((ppg / 3.0) * 5)), 0, 5)
        draws = _clamp(int(round((1 - abs(ppg - 1.5) / 1.5) * (5 - wins))), 0, 5 - wins)
        losses = 5 - wins - draws
        results = ['W'] * wins + ['D'] * draws + ['L'] * losses
    wins_l5 = results[:5].count('W')
    draws_l5 = results[:5].count('D')
    losses_l5 = results[:5].count('L')

    # First/second half goals
    fh_for = float(raw.get('first_half_goals_avg', g * FH_SHARE))
    fh_against = float(raw.get('first_half_conceded_avg', c * FH_SHARE))
    sh_for = float(raw.get('second_half_goals_avg', g * (1 - FH_SHARE)))
    sh_against = float(raw.get('second_half_conceded_avg', c * (1 - FH_SHARE)))

    # Clean sheets (last 10) as a percentage
    cs_pct = raw.get('clean_sheet_pct')
    if cs_pct is None:
        cs = float(raw.get('clean_sheets', 3))
        cs_pct = _clamp(cs / min(played, 10), 0.0, 1.0)
    else:
        cs_pct = _clamp(float(cs_pct), 0.0, 1.0)
    fh_cs_pct = _clamp(float(raw.get('fh_clean_sheet_pct', math.exp(-fh_against))), 0.0, 1.0)

    # xG (team, whole match)
    xg = float(raw.get('xg_for', gf * 1.05))

    # Possession / shots (estimated from attacking strength if missing)
    poss = float(raw.get('possession_avg', _clamp(45 + (g - 1.2) * 8, 35, 65)))
    fh_poss = float(raw.get('fh_possession_avg', poss))
    shots = float(raw.get('shots_avg', _clamp(8 + (g - 1.2) * 4, 5, 20)))
    fh_shots = float(raw.get('fh_shots_avg', shots * FH_SHARE))

    # Corners for/against (estimated from strength if missing)
    corners_for = float(raw.get('corners_for_avg', _clamp(4.5 + (g - 1.2) * 1.5, 2.5, 8.5)))
    corners_against = float(raw.get('corners_against_avg', _clamp(4.5 + (c - 1.2) * 1.0, 2.5, 8.5)))
    fh_corners_for = float(raw.get('fh_corners_for_avg', corners_for * FH_SHARE))
    fh_corners_against = float(raw.get('fh_corners_against_avg', corners_against * FH_SHARE))

    # Discipline
    fouls = float(raw.get('fouls_avg', 12.0))
    cards = float(raw.get('cards_avg', 1.8))
    tackles = float(raw.get('tackles_avg', 14.0))

    total_for_game = g + c  # team's own scored + conceded per game

    return {
        'gf': g, 'ga': c, 'venue': venue,
        'goals_venue_for': gf, 'goals_venue_against': ga, 'ppg': ppg,
        'wins_l5': wins_l5, 'draws_l5': draws_l5, 'losses_l5': losses_l5,
        'unbeaten_l5': wins_l5 + draws_l5,
        'fh_for': fh_for, 'fh_against': fh_against, 'sh_for': sh_for, 'sh_against': sh_against,
        'cs_pct': cs_pct, 'fh_cs_pct': fh_cs_pct, 'xg': xg,
        'poss': poss, 'fh_poss': fh_poss, 'shots': shots, 'fh_shots': fh_shots,
        'corners_for': corners_for, 'corners_against': corners_against,
        'fh_corners_for': fh_corners_for, 'fh_corners_against': fh_corners_against,
        'fouls': fouls, 'cards': cards, 'tackles': tackles,
        # Estimated history counts
        'scored_pct_venue': _clamp(_p_at_least_one(gf), 0, 1),
        'conceded_of5': _count_of(_p_at_least_one(ga), 5),
        'scored_fh_of5': _count_of(_p_at_least_one(fh_for), 5),
        'conceded_fh_of5': _count_of(_p_at_least_one(fh_against), 5),
        'scored_fh_of10': _count_of(_p_at_least_one(fh_for), 10),
        'scored_sh_of5': _count_of(_p_at_least_one(sh_for), 5),
        'scored_of10': _count_of(_p_at_least_one(g), 10),
        'over15_of5': _count_of(_p_ge(2, total_for_game), 5),
        'u25_of10': _count_of(_p_le(2, total_for_game), 10),
        'fts_fh_of5': _count_of(math.exp(-fh_for), 5),
        'u15fh_rate': _clamp(_p_le(1, fh_for + fh_against), 0, 1),
        'won_35fhc_of10': _count_of(_p_ge(4, fh_corners_for), 10),
        'conceded_25fhc_of5': _count_of(_p_ge(3, fh_corners_against), 5),
        'won_65c_of10': _count_of(_p_ge(7, corners_for), 10),
        'conceded_55c_of5': _count_of(_p_ge(6, corners_against), 5),
        'u105c_of10': _count_of(_p_le(10, corners_for + corners_against), 10),
        'not_o35fhc_of10': _count_of(_p_le(3, fh_corners_for + fh_corners_against), 10),
    }


def build_match_context(home_raw: Dict, away_raw: Dict, odds: Dict, h2h: List[Dict],
                        league_id: Optional[int]) -> Dict:
    """Build the shared match context: normalized teams, combined xG, favourite/underdog
    resolution from odds (or strength), and parsed H2H (totals + favourite results)."""
    home = normalize_team(home_raw, 'home')
    away = normalize_team(away_raw, 'away')

    combined_xg = round(home['xg'] + away['xg'], 2)

    home_odds = float((odds or {}).get('home_win', odds.get('Home', 0) if odds else 0) or 0)
    away_odds = float((odds or {}).get('away_win', odds.get('Away', 0) if odds else 0) or 0)

    # If odds missing, synthesize from venue PPG so favourite/underdog can be resolved.
    if home_odds <= 0 or away_odds <= 0:
        hp, ap = home['ppg'] + 0.3, away['ppg']  # small home edge
        total = hp + ap + 1.0
        p_home = hp / total
        p_away = ap / total
        home_odds = round(_clamp(1 / max(p_home, 0.05), 1.05, 15), 2)
        away_odds = round(_clamp(1 / max(p_away, 0.05), 1.05, 15), 2)

    if home_odds <= away_odds:
        fav, dog = 'home', 'away'
        fav_odds, dog_odds = home_odds, away_odds
        fav_team, dog_team = home, away
    else:
        fav, dog = 'away', 'home'
        fav_odds, dog_odds = away_odds, home_odds
        fav_team, dog_team = away, home

    # Parse H2H: list of {'total': int, 'fav_result': 'W'/'D'/'L'}; also count Both-Teams-To-Score meetings
    h2h_totals, h2h_fav_results = [], []
    h2h_btts_count = 0
    for m in (h2h or [])[:5]:
        if 'total' in m and 'fav_result' in m:  # already synthetic-parsed
            h2h_totals.append(int(m['total']))
            h2h_fav_results.append(m['fav_result'])
            if m.get('btts'):
                h2h_btts_count += 1
            continue
        try:
            hg = int(m.get('goals', {}).get('home') or 0)
            ag = int(m.get('goals', {}).get('away') or 0)
            h2h_totals.append(hg + ag)
            if hg >= 1 and ag >= 1:
                h2h_btts_count += 1
            home_is_fav = (fav == 'home')
            fg, og = (hg, ag) if home_is_fav else (ag, hg)
            h2h_fav_results.append('W' if fg > og else ('D' if fg == og else 'L'))
        except Exception:
            continue

    return {
        'home': home, 'away': away,
        'combined_xg': combined_xg,
        'fav': fav, 'dog': dog,
        'fav_odds': fav_odds, 'dog_odds': dog_odds,
        'odds_gap': round(dog_odds - fav_odds, 2),
        'fav_team': fav_team, 'dog_team': dog_team,
        'league_id': league_id,
        'h2h_totals': h2h_totals, 'h2h_fav_results': h2h_fav_results,
        'h2h_btts_count': h2h_btts_count,
        'home_name': home_raw.get('name', 'Home'), 'away_name': away_raw.get('name', 'Away'),
    }


# ---------------------------------------------------------------------------
# Filter helpers: record pass/fail + a 0..1 "strength" (how far it cleared).
# ---------------------------------------------------------------------------
def _ge(value, target, scale):
    passed = value > target
    strength = _clamp((value - target) / scale, 0.0, 1.0) if passed else 0.0
    return passed, strength


def _le(value, target, scale):
    passed = value < target
    strength = _clamp((target - value) / scale, 0.0, 1.0) if passed else 0.0
    return passed, strength


def _count_ge(count, target, n):
    passed = count >= target
    strength = _clamp((count - target) / max(n - target, 1), 0.0, 1.0) if passed else 0.0
    return passed, strength


def _count_le(count, target):
    passed = count <= target
    strength = _clamp((target - count + 1) / (target + 1), 0.0, 1.0) if passed else 0.0
    return passed, strength


def _result(passes: List, key: str, selection: str, ctx: Dict, odds: Optional[float] = None) -> Dict:
    """passes: list of (bool, strength). Market qualifies only when ALL are True."""
    all_pass = all(p for p, _ in passes)
    strengths = [s for p, s in passes if p]
    strength = sum(strengths) / len(passes) if passes else 0.0
    league_base = _league_base(key, ctx.get('league_id'))
    blended = round(_clamp(league_base + (strength - 0.5) * FILTER_SWING, PROB_FLOOR, PROB_CEIL), 1)
    fair_odds = odds if odds is not None else BASE_ODDS[key]
    return {
        'key': key,
        'market': DISPLAY[key],
        'selection': selection,
        'qualifies': all_pass,
        'filters_passed': sum(1 for p, _ in passes if p),
        'total_filters': len(passes),
        'strength': round(strength, 3),
        'probability': blended,
        'odds': round(float(fair_odds), 2),
        'confidence': _confidence(blended),
    }


def _league_base(key: str, league_id: Optional[int]) -> float:
    base = LEAGUE_BASE[key]
    gi = LEAGUE_GOAL_INDEX.get(league_id, 2.6)
    # Nudge goal-driven markets by league scoring environment (documented, +-6 max)
    if key in ('over_1_5', 'over_2_5', 'btts', 'over_0_5_fh', 'over_0_5_sh', 'dc_over_1_5'):
        base += _clamp((gi - 2.6) * 6, -6, 6)
    elif key in ('under_3_5', 'under_4_5', 'under_1_5_fh', 'dc_under_4_5'):
        base += _clamp((2.6 - gi) * 6, -6, 6)
    return _clamp(base, PROB_FLOOR, PROB_CEIL)


def _confidence(p: float) -> str:
    if p >= 82:
        return 'Very High'
    if p >= 72:
        return 'High'
    if p >= 62:
        return 'Medium'
    return 'Low'


def _team_name(ctx, side):
    return ctx['home_name'] if side == 'home' else ctx['away_name']


def _dc_selection(ctx):
    fav = _team_name(ctx, ctx['fav'])
    return f"{fav} or Draw"


# ---------------------------------------------------------------------------
# THE 20 MARKET EVALUATORS  (a market qualifies only if ALL filters pass)
# ---------------------------------------------------------------------------
def m_straight_win(ctx):
    f, d = ctx['fav_team'], ctx['dog_team']
    passes = [
        _ge(TH.SW_FAV_ODDS_MAX, ctx['fav_odds'], 0.4) if False else (ctx['fav_odds'] < TH.SW_FAV_ODDS_MAX, _clamp((TH.SW_FAV_ODDS_MAX - ctx['fav_odds']) / 0.5, 0, 1)),
        _ge(ctx['odds_gap'], TH.SW_ODDS_GAP_MIN, 0.6),
        _ge(f['ppg'], TH.SW_FAV_PPG_MIN, 0.6),
        _ge(ctx['combined_xg'], TH.SW_MATCH_XG_MIN, 1.0),
        _ge(f['xg'], TH.SW_FAV_XG_MIN, 0.6),
        _count_ge(f['wins_l5'], TH.SW_FAV_WINS_L5_MIN, 5),
        _count_ge(d['losses_l5'], TH.SW_DOG_LOSSES_L5_MIN, 5),
    ]
    return _result(passes, 'straight_win', f"{_team_name(ctx, ctx['fav'])} to Win", ctx, ctx['fav_odds'])


def m_double_chance(ctx):
    f, d = ctx['fav_team'], ctx['dog_team']
    h2h_wins = ctx['h2h_fav_results'].count('W')
    passes = [
        _count_ge(f['unbeaten_l5'], TH.DC_FAV_UNBEATEN_L5_MIN, 5),
        _count_ge(h2h_wins, TH.DC_FAV_H2H_WINS_MIN, 5),
        _ge(f['ppg'], TH.DC_FAV_PPG_MIN, 0.7),
        _count_le(d['wins_l5'], TH.DC_DOG_WINS_L5_MAX),
    ]
    return _result(passes, 'double_chance', _dc_selection(ctx), ctx, round(_clamp(ctx['fav_odds'] * 0.6, 1.1, 1.5), 2))


def m_btts(ctx):
    h, a = ctx['home'], ctx['away']
    h2h_btts = ctx.get('h2h_btts_count', 0)
    passes = [
        _ge(h['scored_pct_venue'], TH.BTTS_HOME_SCORE_PCT_MIN, 0.25),
        _ge(a['scored_pct_venue'], TH.BTTS_AWAY_SCORE_PCT_MIN, 0.25),
        _count_ge(min(h['conceded_of5'], a['conceded_of5']), TH.BTTS_BOTH_CONCEDE_OF5_MIN, 5),
        _ge(ctx['combined_xg'], TH.BTTS_MATCH_XG_MIN, 1.0),
        _count_ge(h2h_btts, TH.BTTS_H2H_BTTS_MIN, TH.BTTS_H2H_GAMES),
    ]
    return _result(passes, 'btts', DISPLAY['btts'], ctx)


def m_over_1_5(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(ctx['combined_xg'], TH.O15_MATCH_XG_MIN, 1.0),
        _ge(max(h['gf'], a['gf']), TH.O15_ONE_TEAM_GOALS_MIN, 0.6),
        _le(min(h['cs_pct'], a['cs_pct']), TH.O15_ONE_TEAM_CS_PCT_MAX, 0.2),
        _count_ge(min(h['over15_of5'], a['over15_of5']), TH.O15_BOTH_OVER15_OF5_MIN, 5),
    ]
    return _result(passes, 'over_1_5', DISPLAY['over_1_5'], ctx)


def m_over_2_5(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(h['gf'] + a['gf'], TH.O25_COMBINED_GOALS_MIN, 1.0),
        _ge(max(h['gf'], a['gf']), TH.O25_ONE_TEAM_GOALS_MIN, 0.6),
        _le(min(h['cs_pct'], a['cs_pct']), TH.O25_ONE_TEAM_CS_PCT_MAX, 0.2),
        _count_ge(min(h['scored_of10'], a['scored_of10']), TH.O25_BOTH_SCORED_OF10_MIN, 10),
    ]
    return _result(passes, 'over_2_5', DISPLAY['over_2_5'], ctx)


def m_over_0_5_fh(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(h['fh_for'] + a['fh_for'], TH.O05FH_COMBINED_FH_MIN, 0.6),
        _count_ge(max(h['scored_fh_of5'], a['scored_fh_of5']), TH.O05FH_ONE_SCORED_FH_OF5_MIN, 5),
        _count_ge(max(h['conceded_fh_of5'], a['conceded_fh_of5']), TH.O05FH_ONE_CONCEDED_FH_OF5_MIN, 5),
        _count_ge(min(h['scored_fh_of10'], a['scored_fh_of10']), TH.O05FH_BOTH_SCORED_FH_OF10_MIN, 10),
        _ge(ctx['combined_xg'], TH.O05FH_MATCH_XG_MIN, 1.0),
    ]
    return _result(passes, 'over_0_5_fh', DISPLAY['over_0_5_fh'], ctx)


def m_over_0_5_sh(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(h['sh_for'] + a['sh_for'], TH.O05SH_COMBINED_SH_MIN, 0.6),
        _ge(max(h['sh_for'], a['sh_for']), TH.O05SH_ONE_TEAM_SH_MIN, 0.4),
        _count_ge(max(h['scored_sh_of5'], a['scored_sh_of5']), TH.O05SH_ONE_SCORED_SH_OF5_MIN, 5),
        _ge(ctx['combined_xg'], TH.O05SH_MATCH_XG_MIN, 1.0),
    ]
    return _result(passes, 'over_0_5_sh', DISPLAY['over_0_5_sh'], ctx)


def m_team_2h(ctx):
    """Evaluate BOTH teams; back whichever passes all 4. If both pass, higher blended prob."""
    best = None
    for side in ('home', 'away'):
        t = ctx['home'] if side == 'home' else ctx['away']
        passes = [
            _ge(t['ppg'], TH.T2H_PPG_MIN, 0.7),
            _ge(t['xg'], TH.T2H_MATCH_XG_MIN, 0.6),
            _ge(t['sh_for'], TH.T2H_SH_GOALS_MIN, 0.4),
            _count_ge(t['scored_sh_of5'], TH.T2H_SCORED_SH_OF5_MIN, 5),
        ]
        res = _result(passes, 'team_2h', f"{_team_name(ctx, side)} to Score in 2nd Half", ctx)
        if res['qualifies'] and (best is None or res['probability'] > best['probability']):
            best = res
    if best:
        return best
    # none qualified — return a non-qualifying stub for transparency
    return {'key': 'team_2h', 'market': DISPLAY['team_2h'], 'selection': DISPLAY['team_2h'],
            'qualifies': False, 'filters_passed': 0, 'total_filters': 4, 'strength': 0.0,
            'probability': PROB_FLOOR, 'odds': BASE_ODDS['team_2h'], 'confidence': 'Low'}


def m_under_3_5(ctx):
    h, a = ctx['home'], ctx['away']
    h2h_u25 = sum(1 for t in ctx['h2h_totals'][:5] if t < 2.5)
    cs_hi, cs_lo = max(h['cs_pct'], a['cs_pct']), min(h['cs_pct'], a['cs_pct'])
    passes = [
        _le(ctx['combined_xg'], TH.U35_MATCH_XG_MAX, 1.0),
        _count_ge(min(h['u25_of10'], a['u25_of10']), TH.U35_BOTH_U25_OF10_MIN, 10),
        _count_ge(h2h_u25, TH.U35_H2H_U25_OF5_MIN, 5),
        (cs_hi > TH.U35_CS_HIGH_MIN and cs_lo > TH.U35_CS_LOW_MIN,
         _clamp(((cs_hi - TH.U35_CS_HIGH_MIN) + (cs_lo - TH.U35_CS_LOW_MIN)) / 0.4, 0, 1)
         if (cs_hi > TH.U35_CS_HIGH_MIN and cs_lo > TH.U35_CS_LOW_MIN) else 0.0),
        (h['ga'] < TH.U35_BOTH_CONCEDE_MAX and a['ga'] < TH.U35_BOTH_CONCEDE_MAX,
         _clamp((TH.U35_BOTH_CONCEDE_MAX - max(h['ga'], a['ga'])) / 0.6, 0, 1)
         if (h['ga'] < TH.U35_BOTH_CONCEDE_MAX and a['ga'] < TH.U35_BOTH_CONCEDE_MAX) else 0.0),
    ]
    return _result(passes, 'under_3_5', DISPLAY['under_3_5'], ctx)


def m_under_4_5(ctx):
    h, a = ctx['home'], ctx['away']
    h2h_u35 = sum(1 for t in ctx['h2h_totals'][:5] if t < 3.5)
    cs_hi, cs_lo = max(h['cs_pct'], a['cs_pct']), min(h['cs_pct'], a['cs_pct'])
    passes = [
        _le(ctx['combined_xg'], TH.U45_MATCH_XG_MAX, 1.0),
        _le(min(h['ga'], a['ga']), TH.U45_ONE_CONCEDE_MAX, 0.5),
        _count_ge(h2h_u35, TH.U45_H2H_U35_OF5_MIN, 5),
        (cs_hi > TH.U45_CS_HIGH_MIN and cs_lo > TH.U45_CS_LOW_MIN,
         _clamp(((cs_hi - TH.U45_CS_HIGH_MIN) + (cs_lo - TH.U45_CS_LOW_MIN)) / 0.4, 0, 1)
         if (cs_hi > TH.U45_CS_HIGH_MIN and cs_lo > TH.U45_CS_LOW_MIN) else 0.0),
    ]
    return _result(passes, 'under_4_5', DISPLAY['under_4_5'], ctx)


def m_under_1_5_fh(ctx):
    h, a = ctx['home'], ctx['away']
    both_u15_pct = min(h['u15fh_rate'], a['u15fh_rate'])
    passes = [
        _ge(both_u15_pct, TH.U15FH_BOTH_U15_PCT_MIN, 0.25),
        _count_ge(min(h['fts_fh_of5'], a['fts_fh_of5']), TH.U15FH_BOTH_FTS_FH_OF5_MIN, 5),
        _ge(max(h['fh_cs_pct'], a['fh_cs_pct']), TH.U15FH_ONE_FH_CS_PCT_MIN, 0.2),
        _ge(min(h['u15fh_rate'], a['u15fh_rate']), TH.U15FH_BOTH_OVERALL_HITRATE_MIN, 0.3),
    ]
    return _result(passes, 'under_1_5_fh', DISPLAY['under_1_5_fh'], ctx)


def m_dnb(ctx):
    f, d = ctx['fav_team'], ctx['dog_team']
    not_lost_h2h = 'L' not in ctx['h2h_fav_results'][:3]
    passes = [
        (ctx['fav_odds'] < TH.DNB_FAV_ODDS_MAX, _clamp((TH.DNB_FAV_ODDS_MAX - ctx['fav_odds']) / 0.7, 0, 1) if ctx['fav_odds'] < TH.DNB_FAV_ODDS_MAX else 0.0),
        _ge(f['ppg'], TH.DNB_FAV_PPG_MIN, 0.7),
        (not_lost_h2h and len(ctx['h2h_fav_results']) >= 1, 0.6 if not_lost_h2h and len(ctx['h2h_fav_results']) >= 1 else 0.0),
        _count_ge(f['wins_l5'], TH.DNB_FAV_WINS_L5_MIN, 5),
        _count_ge(d['losses_l5'], TH.DNB_DOG_LOSSES_L5_MIN, 5),
    ]
    return _result(passes, 'dnb', f"{_team_name(ctx, ctx['fav'])} Draw No Bet", ctx, round(_clamp(ctx['fav_odds'] * 0.8, 1.2, 2.0), 2))


def m_dc_over_1_5(ctx):
    f = ctx['fav_team']
    h, a = ctx['home'], ctx['away']
    passes = [
        (ctx['fav_odds'] < TH.DCO15_FAV_ODDS_MAX, _clamp((TH.DCO15_FAV_ODDS_MAX - ctx['fav_odds']) / 0.5, 0, 1) if ctx['fav_odds'] < TH.DCO15_FAV_ODDS_MAX else 0.0),
        _ge(f['ppg'], TH.DCO15_FAV_PPG_MIN, 0.6),
        _ge(ctx['combined_xg'], TH.DCO15_MATCH_XG_MIN, 1.0),
        _ge(max(h['gf'], a['gf']), TH.DCO15_ONE_TEAM_GOALS_MIN, 0.6),
        _count_ge(f['unbeaten_l5'], TH.DCO15_FAV_UNBEATEN_L5_MIN, 5),
    ]
    return _result(passes, 'dc_over_1_5', f"{_team_name(ctx, ctx['fav'])} or Draw & Over 1.5 Goals", ctx)


def m_dc_under_4_5(ctx):
    f = ctx['fav_team']
    h, a = ctx['home'], ctx['away']
    passes = [
        (ctx['fav_odds'] < TH.DCU45_FAV_ODDS_MAX, _clamp((TH.DCU45_FAV_ODDS_MAX - ctx['fav_odds']) / 0.5, 0, 1) if ctx['fav_odds'] < TH.DCU45_FAV_ODDS_MAX else 0.0),
        _ge(f['ppg'], TH.DCU45_FAV_PPG_MIN, 0.6),
        _count_ge(f['unbeaten_l5'], TH.DCU45_FAV_UNBEATEN_L5_MIN, 5),
        _le(ctx['combined_xg'], TH.DCU45_MATCH_XG_MAX, 1.0),
        (h['gf'] < TH.DCU45_BOTH_GOALS_MAX and a['gf'] < TH.DCU45_BOTH_GOALS_MAX,
         _clamp((TH.DCU45_BOTH_GOALS_MAX - max(h['gf'], a['gf'])) / 0.5, 0, 1)
         if (h['gf'] < TH.DCU45_BOTH_GOALS_MAX and a['gf'] < TH.DCU45_BOTH_GOALS_MAX) else 0.0),
    ]
    return _result(passes, 'dc_under_4_5', f"{_team_name(ctx, ctx['fav'])} or Draw & Under 4.5 Goals", ctx)


def m_over_4_5_fh_corners(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(max(h['fh_poss'], a['fh_poss']), TH.O45FHC_ONE_FH_POSS_MIN, 8),
        _ge(max(h['fh_shots'], a['fh_shots']), TH.O45FHC_ONE_FH_SHOTS_MIN, 3),
        _count_ge(max(h['won_35fhc_of10'], a['won_35fhc_of10']), TH.O45FHC_ONE_WON_35_OF10_MIN, 10),
        _count_ge(max(h['conceded_25fhc_of5'], a['conceded_25fhc_of5']), TH.O45FHC_ONE_CONCEDED_25_OF5_MIN, 5),
    ]
    return _result(passes, 'over_4_5_fh_corners', DISPLAY['over_4_5_fh_corners'], ctx)


def m_over_8_5_corners(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(max(h['poss'], a['poss']), TH.O85C_ONE_POSS_MIN, 8),
        _ge(max(h['shots'], a['shots']), TH.O85C_ONE_SHOTS_MIN, 4),
        _count_ge(max(h['won_65c_of10'], a['won_65c_of10']), TH.O85C_ONE_WON_65_OF10_MIN, 10),
        _count_ge(max(h['conceded_55c_of5'], a['conceded_55c_of5']), TH.O85C_ONE_CONCEDED_55_OF5_MIN, 5),
    ]
    return _result(passes, 'over_8_5_corners', DISPLAY['over_8_5_corners'], ctx)


def m_under_10_5_corners(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        (h['poss'] < TH.U105C_BOTH_POSS_MAX and a['poss'] < TH.U105C_BOTH_POSS_MAX,
         _clamp((TH.U105C_BOTH_POSS_MAX - max(h['poss'], a['poss'])) / 8, 0, 1)
         if (h['poss'] < TH.U105C_BOTH_POSS_MAX and a['poss'] < TH.U105C_BOTH_POSS_MAX) else 0.0),
        _le(h['shots'] + a['shots'], TH.U105C_COMBINED_SHOTS_MAX, 5),
        _count_ge(max(h['u105c_of10'], a['u105c_of10']), TH.U105C_ONE_U105_OF10_MIN, 10),
        (h['corners_for'] < TH.U105C_BOTH_CORNERS_FOR_MAX and a['corners_for'] < TH.U105C_BOTH_CORNERS_FOR_MAX,
         _clamp((TH.U105C_BOTH_CORNERS_FOR_MAX - max(h['corners_for'], a['corners_for'])) / 2.0, 0, 1)
         if (h['corners_for'] < TH.U105C_BOTH_CORNERS_FOR_MAX and a['corners_for'] < TH.U105C_BOTH_CORNERS_FOR_MAX) else 0.0),
    ]
    return _result(passes, 'under_10_5_corners', DISPLAY['under_10_5_corners'], ctx)


def m_over_2_5_cards(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(max(h['fouls'], a['fouls']), TH.O25CD_ONE_FOULS_MIN, 5),
        _ge(h['fouls'] + a['fouls'], TH.O25CD_COMBINED_FOULS_MIN, 8),
        _ge(max(h['cards'], a['cards']), TH.O25CD_ONE_CARDS_MIN, 0.8),
        _ge(max(h['tackles'], a['tackles']), TH.O25CD_ONE_TACKLES_MIN, 5),
    ]
    return _result(passes, 'over_2_5_cards', DISPLAY['over_2_5_cards'], ctx)


def m_over_3_5_cards(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _ge(min(h['tackles'], a['tackles']), TH.O35CD_BOTH_TACKLES_MIN, 5),
        _ge(h['fouls'] + a['fouls'], TH.O35CD_COMBINED_FOULS_MIN, 8),
        _ge(min(h['cards'], a['cards']), TH.O35CD_BOTH_CARDS_MIN, 0.8),
        _ge(min(h['tackles'], a['tackles']), TH.O35CD_BOTH_TACKLES_MIN2, 5),
    ]
    return _result(passes, 'over_3_5_cards', DISPLAY['over_3_5_cards'], ctx)


def m_under_5_5_cards(ctx):
    h, a = ctx['home'], ctx['away']
    passes = [
        _le(min(h['fouls'], a['fouls']), TH.U55CD_ONE_FOULS_MAX, 5),
        _le(h['fouls'] + a['fouls'], TH.U55CD_COMBINED_FOULS_MAX, 6),
        _le(min(h['cards'], a['cards']), TH.U55CD_ONE_CARDS_MAX, 0.8),
        _le(h['tackles'] + a['tackles'], TH.U55CD_COMBINED_TACKLES_MAX, 6),
    ]
    return _result(passes, 'under_5_5_cards', DISPLAY['under_5_5_cards'], ctx)


GOAL_RESULT_MARKETS = [
    m_straight_win, m_double_chance, m_btts, m_over_1_5, m_over_2_5, m_over_0_5_fh,
    m_over_0_5_sh, m_team_2h, m_under_3_5, m_under_4_5, m_under_1_5_fh, m_dnb,
    m_dc_over_1_5, m_dc_under_4_5,
]
CORNER_CARD_MARKETS = [
    m_over_4_5_fh_corners, m_over_8_5_corners, m_under_10_5_corners,
    m_over_2_5_cards, m_over_3_5_cards, m_under_5_5_cards,
]


def evaluate_fixture(home_raw: Dict, away_raw: Dict, odds: Dict = None,
                     h2h: List[Dict] = None, league_id: int = None,
                     include_corner_card: bool = True) -> List[Dict]:
    """Run ALL 20 markets. Return the list of QUALIFYING tips (all-filters-pass),
    ranked by blended probability (desc), ties broken by odds/value (desc)."""
    ctx = build_match_context(home_raw, away_raw, odds or {}, h2h or [], league_id)
    evaluators = list(GOAL_RESULT_MARKETS)
    if include_corner_card:
        evaluators += CORNER_CARD_MARKETS
    tips = []
    for ev in evaluators:
        try:
            res = ev(ctx)
            if res.get('qualifies'):
                tips.append(res)
        except Exception as e:
            logger.error(f"engine market error {ev.__name__}: {e}")
    # Probability overrides value; ties -> highest odds
    tips.sort(key=lambda t: (t['probability'], t['odds']), reverse=True)
    return tips


# ---------------------------------------------------------------------------
# Synthetic (realistic) fixture pool — used while live data (API-Sports) is off.
# Generates internally-consistent team stats + odds + H2H, then runs the REAL
# engine so the tips users see are produced by the real filters (not random).
# ---------------------------------------------------------------------------
_LEAGUE_TEAMS = {
    (39, "Premier League"): ["Liverpool", "Arsenal", "Man City", "Chelsea", "Tottenham",
                              "Man United", "Newcastle", "Aston Villa", "West Ham", "Brighton",
                              "Everton", "Fulham", "Crystal Palace", "Brentford"],
    (140, "La Liga"): ["Barcelona", "Real Madrid", "Atletico Madrid", "Sevilla", "Real Sociedad",
                        "Athletic Bilbao", "Valencia", "Villarreal", "Real Betis", "Getafe"],
    (135, "Serie A"): ["Inter Milan", "AC Milan", "Juventus", "Napoli", "Roma", "Lazio",
                        "Fiorentina", "Atalanta", "Bologna", "Torino"],
    (78, "Bundesliga"): ["Bayern Munich", "Dortmund", "RB Leipzig", "Leverkusen", "Frankfurt",
                          "Wolfsburg", "Freiburg", "Stuttgart", "Hoffenheim", "Mainz"],
    (61, "Ligue 1"): ["PSG", "Marseille", "Monaco", "Lyon", "Lille", "Nice", "Rennes",
                       "Lens", "Reims", "Toulouse"],
    (88, "Eredivisie"): ["Ajax", "PSV", "Feyenoord", "AZ Alkmaar", "Twente", "Utrecht"],
    (94, "Primeira Liga"): ["Benfica", "Porto", "Sporting CP", "Braga", "Vitoria", "Boavista"],
    (144, "Belgian Pro League"): ["Club Brugge", "Anderlecht", "Genk", "Gent", "Antwerp", "Union SG"],
    (40, "Championship"): ["Leeds", "Southampton", "Leicester", "Ipswich", "Norwich", "Watford"],
    (179, "Scottish Premiership"): ["Celtic", "Rangers", "Hearts", "Hibernian", "Aberdeen", "Motherwell"],
    (203, "Süper Lig"): ["Galatasaray", "Fenerbahce", "Besiktas", "Trabzonspor", "Basaksehir", "Adana"],
}


def _unique_fixtures(rng, n):
    """Build up to `n` DISTINCT (home, away, league, league_id) matchups (no repeated pair)."""
    fixtures, seen = [], set()
    combos = []
    for (lid, lname), teams in _LEAGUE_TEAMS.items():
        for i in range(len(teams)):
            for j in range(len(teams)):
                if i != j:
                    combos.append((teams[i], teams[j], lname, lid))
    rng.shuffle(combos)
    for home, away, lname, lid in combos:
        key = (home, away, lname)
        if key in seen:
            continue
        seen.add(key)
        fixtures.append((home, away, lname, lid))
        if len(fixtures) >= n:
            break
    return fixtures


def _rand_team(rng, strength, style='balanced'):
    """Create a realistic, internally-consistent raw team stats dict.
    `style` (attacking/defensive/balanced) decouples scoring from strength so the pool
    contains strong-but-low-scoring defensive sides, corner-heavy sides, etc. Thresholds are
    never touched — only the realism of the synthetic inputs the filters run against."""
    if style == 'attacking':
        gf = 1.4 + strength * 1.0
        ga = 1.0 + (1 - strength) * 0.8
        poss_base, corners_for_base, shots_base = 50, 6.0, 12
    elif style == 'defensive':
        gf = 0.7 + strength * 0.55           # strong defensive sides still score little
        ga = 0.45 + (1 - strength) * 0.6
        poss_base, corners_for_base, shots_base = 46, 3.5, 8
    else:
        gf = 1.0 + strength * 0.9
        ga = 0.8 + (1 - strength) * 0.7
        poss_base, corners_for_base, shots_base = 48, 4.8, 10
    gf = round(gf + rng.uniform(-0.12, 0.12), 2)
    ga = round(ga + rng.uniform(-0.12, 0.12), 2)

    wins = _clamp(int(round(strength * 5 + rng.uniform(-0.6, 0.6))), 0, 5)
    losses = _clamp(int(round((1 - strength) * 4 + rng.uniform(-0.6, 0.6))), 0, 5 - wins)
    draws = 5 - wins - losses
    form = ['W'] * wins + ['D'] * draws + ['L'] * losses
    rng.shuffle(form)

    cs_pct = round(_clamp((0.10 if style == 'attacking' else 0.20) + strength * 0.35
                          + rng.uniform(-0.05, 0.05), 0.0, 0.65), 2)
    aggressive = rng.random() < 0.5   # roughly half the teams are card-prone
    return {
        'goals_avg': max(gf, 0.35), 'conceded_avg': max(ga, 0.3),
        'played': 10, 'wins': wins * 2, 'draws': draws * 2,
        'form_last5_venue': form, 'wins_last5_venue': wins, 'draws_last5_venue': draws,
        'clean_sheet_pct': cs_pct,
        'possession_avg': round(_clamp(poss_base + strength * 16 + rng.uniform(-4, 4), 33, 68), 1),
        'shots_avg': round(_clamp(shots_base + strength * 7 + rng.uniform(-2, 2), 4, 22), 1),
        'corners_for_avg': round(_clamp(corners_for_base + strength * 2.5 + rng.uniform(-0.8, 0.8), 2.0, 9.5), 2),
        'corners_against_avg': round(_clamp(6.0 - strength * 2.0 + rng.uniform(-0.8, 0.8), 2.0, 9.5), 2),
        'fouls_avg': round(rng.uniform(15, 20) if aggressive else rng.uniform(8, 14), 1),
        'cards_avg': round(rng.uniform(1.9, 3.0) if aggressive else rng.uniform(1.0, 1.9), 2),
        'tackles_avg': round(rng.uniform(15, 21) if aggressive else rng.uniform(10, 15), 1),
    }


def _rand_h2h(rng, home_raw, away_raw):
    out = []
    for _ in range(5):
        hg = max(0, int(round(rng.gauss(home_raw['goals_avg'], 1.0))))
        ag = max(0, int(round(rng.gauss(away_raw['goals_avg'], 1.0))))
        r = rng.random()
        fav_result = 'W' if r < 0.5 else ('D' if r < 0.75 else 'L')
        out.append({'total': hg + ag, 'fav_result': fav_result, 'btts': hg >= 1 and ag >= 1})
    return out


def generate_engine_games(count: int = 60, seed: Optional[int] = None,
                          max_tips_per_game: int = 3) -> List[Dict]:
    """Build a pool of games (each with up to `max_tips_per_game` qualifying tips) using
    the REAL engine on realistic synthetic data. Only games with >=1 qualifying tip are kept."""
    import uuid
    from datetime import datetime
    rng = random.Random(seed if seed is not None else datetime.now().strftime('%Y%m%d'))
    fixtures = _unique_fixtures(rng, count * 3)
    games = []
    fi = 0
    while len(games) < count and fi < len(fixtures):
        home_name, away_name, league, league_id = fixtures[fi]
        fi += 1
        hs = rng.uniform(0.25, 0.95)
        as_ = rng.uniform(0.15, 0.9)
        hstyle = rng.choice(['attacking', 'attacking', 'balanced', 'defensive'])
        astyle = rng.choice(['attacking', 'balanced', 'defensive', 'defensive'])
        home_raw = _rand_team(rng, hs, hstyle); home_raw['name'] = home_name
        away_raw = _rand_team(rng, as_, astyle); away_raw['name'] = away_name
        h2h = _rand_h2h(rng, home_raw, away_raw)
        tips = evaluate_fixture(home_raw, away_raw, {}, h2h, league_id, include_corner_card=True)
        if not tips:
            continue
        best = tips[:max_tips_per_game]
        combined = round(sum(t['probability'] for t in best) / len(best), 1)
        hw = sum(1 for m in h2h if m['fav_result'] == 'W')
        hd = sum(1 for m in h2h if m['fav_result'] == 'D')
        hl = sum(1 for m in h2h if m['fav_result'] == 'L')
        games.append({
            'id': str(uuid.uuid4()),
            'fixture_id': 900000 + len(games),
            'home': home_name, 'away': away_name, 'league': league, 'league_id': league_id,
            'date': datetime.now().isoformat(),
            'tips': best,
            'all_tips': tips,
            'combined_probability': combined,
            'home_form': ''.join(home_raw['form_last5_venue']),
            'away_form': ''.join(away_raw['form_last5_venue']),
            'h2h': {'home_wins': hw, 'draws': hd, 'away_wins': hl},
        })
    games.sort(key=lambda g: g['combined_probability'], reverse=True)
    return games


# ---------------------------------------------------------------------------
# Shared daily pool + ticket combiners (used by ALL surfaces so every tip in
# the app comes from the same 20-market engine).
# ---------------------------------------------------------------------------
_POOL_CACHE = {}


def get_daily_pool(count: int = 120):
    """Cached per-day pool of engine games (same tips across all surfaces for the day)."""
    from datetime import datetime
    key = datetime.now().strftime('%Y-%m-%d')
    if key not in _POOL_CACHE:
        _POOL_CACHE.clear()
        _POOL_CACHE[key] = generate_engine_games(count, seed=int(datetime.now().strftime('%Y%m%d')))
    return _POOL_CACHE[key]


def best_tip(game, market_keys=None):
    for t in game['all_tips']:
        if market_keys is None or t['key'] in market_keys:
            return t
    return None


# Same-game correlation rules: these market pairs are STRICTLY PROHIBITED from appearing
# together in the SAME same-game betslip (Build A Bet / SGP). They may still each appear in
# daily tips (where the user picks one). Cross-game tickets are unaffected (different matches).
PROHIBITED_SAME_GAME_PAIRS = [
    # DC & Under 4.5 vs Under 4.5 / Under 3.5
    frozenset({'dc_under_4_5', 'under_4_5'}),
    frozenset({'dc_under_4_5', 'under_3_5'}),
    # DC & Over 1.5 vs Over 1.5 / Over 2.5
    frozenset({'dc_over_1_5', 'over_1_5'}),
    frozenset({'dc_over_1_5', 'over_2_5'}),
    # DC & Goals variants vs Double Chance / Draw No Bet
    frozenset({'dc_under_4_5', 'double_chance'}),
    frozenset({'dc_under_4_5', 'dnb'}),
    frozenset({'dc_over_1_5', 'double_chance'}),
    frozenset({'dc_over_1_5', 'dnb'}),
    # Total-goals overs vs half overs
    frozenset({'over_1_5', 'over_0_5_fh'}),
    frozenset({'over_1_5', 'over_0_5_sh'}),
    frozenset({'over_2_5', 'over_0_5_fh'}),
    frozenset({'over_2_5', 'over_0_5_sh'}),
    # Total-goals unders vs 1st-half under
    frozenset({'under_3_5', 'under_1_5_fh'}),
    frozenset({'under_4_5', 'under_1_5_fh'}),
    # Corner overs
    frozenset({'over_4_5_fh_corners', 'over_8_5_corners'}),
]


def _combo_ok(sel):
    """True if a same-game combo contains NO prohibited (correlated) market pair."""
    keys = [it['key'] for it in sel]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if frozenset({keys[i], keys[j]}) in PROHIBITED_SAME_GAME_PAIRS:
                return False
    return True


def _find_combo(items, min_odds, max_odds, legs_range, tries=400, valid_fn=None):
    """Find a subset of `items` (each with 'odds' & 'probability') whose product of odds is
    within [min_odds, max_odds]. Prefer highest average probability (probability overrides value).
    If `valid_fn` is given, only subsets for which valid_fn(subset) is True are accepted."""
    n = len(items)
    min_l, max_l = legs_range
    for num in range(min_l, min(max_l, n) + 1):
        best, best_prob = None, -1
        for s in range(tries):
            rng = random.Random(1000 + s)
            sel = rng.sample(items, num)
            if valid_fn is not None and not valid_fn(sel):
                continue
            odds = 1.0
            for it in sel:
                odds *= it['odds']
            if min_odds <= odds <= max_odds:
                ap = sum(it['probability'] for it in sel) / num
                if ap > best_prob:
                    best_prob, best = ap, (sel, round(odds, 2))
        if best:
            return best
    return None


def _find_combo_distinct(items, min_odds, max_odds, legs_range, tries=600):
    """Like _find_combo but every chosen item must come from a DIFFERENT game
    (items carry 'fixture_id'). Lets higher-odds tickets pick higher-odds tips per game."""
    min_l, max_l = legs_range
    n_games = len({it['fixture_id'] for it in items})
    for num in range(min_l, min(max_l, n_games) + 1):
        best, best_prob = None, -1
        for s in range(tries):
            rng = random.Random(2000 + s)
            pool = items[:]
            rng.shuffle(pool)
            sel, used = [], set()
            for it in pool:
                if it['fixture_id'] in used:
                    continue
                sel.append(it); used.add(it['fixture_id'])
                if len(sel) == num:
                    break
            if len(sel) < num:
                continue
            odds = 1.0
            for it in sel:
                odds *= it['odds']
            if min_odds <= odds <= max_odds:
                ap = sum(it['probability'] for it in sel) / num
                if ap > best_prob:
                    best_prob, best = ap, (sel, round(odds, 2))
        if best:
            return best
    return None


def build_cross_game_ticket(pool, min_odds, max_odds, legs_range, used_ids, market_keys=None):
    """Legs from DIFFERENT games (Mixed Parlay style). Each game may contribute any ONE of its
    qualifying tips, so higher-odds targets can pick higher-odds tips."""
    items = []
    for g in pool:
        if g['fixture_id'] in used_ids:
            continue
        for t in g['all_tips']:
            if market_keys is not None and t['key'] not in market_keys:
                continue
            items.append({'game': g, 'tip': t, 'odds': t['odds'],
                          'probability': t['probability'], 'fixture_id': g['fixture_id']})
    combo = _find_combo_distinct(items, min_odds, max_odds, legs_range)
    if not combo:
        return None
    sel, odds = combo
    return sel, odds


def build_same_game_ticket(pool, min_odds, max_odds, legs_range, used_ids):
    """Multiple qualifying tips from the SAME game (Same Game Parlay / Build A Bet style)."""
    for g in pool:
        if g['fixture_id'] in used_ids:
            continue
        tips = g['all_tips']
        if len(tips) < legs_range[0]:
            continue
        combo = _find_combo(tips, min_odds, max_odds, legs_range, valid_fn=_combo_ok)
        if combo:
            sel, odds = combo
            return g, sel, odds
    return None

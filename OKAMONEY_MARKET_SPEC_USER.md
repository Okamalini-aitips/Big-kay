# ⛔ OkaMoney — USER-AUTHORITATIVE MARKET & FILTER SPEC (SOURCE OF TRUTH)

DO NOT ALTER ANY MARKET, FILTER, THRESHOLD, OR SELECTION RULE IN THIS FILE OR IN CODE
WITHOUT THE USER'S EXPLICIT WRITTEN CONSENT. This file is the single source of truth for
the betting engine. If code and this file ever disagree, this file wins and the code is the bug.

Status: IN PROGRESS — user is supplying 20 markets. 3 of 20 received so far (markets 4–20 pending).
Implementation is DEFERRED until ALL 20 markets are received (user's instruction: one clean pass).

--------------------------------------------------------------------------------
## GLOBAL RULES (confirmed by user)

1. REPLACE ENTIRELY: These 20 markets (with these exact filters) become the ONLY markets the
   app ever tips. All previously-existing markets/analyzers are retired from tip selection.

2. ALL FILTERS MUST PASS: A market qualifies as a tip for a game ONLY if EVERY one of its
   filters passes. No partial-pass, no scoring shortcuts. Never compromise on selection.

3. SELECTION WHEN MULTIPLE MARKETS QUALIFY IN THE SAME GAME:
   - Compute each qualifying market's probability as a BLEND of:
     (a) that league/competition's historical hit-rate for that market, and
     (b) how strongly the game's stats passed that market's filters.
   - PROBABILITY ALWAYS OVERRIDES VALUE. Pick the market with the higher chance of hitting.
   - TIE-BREAKER: only when probabilities are equal on all accounts, pick the MOST VALUABLE
     tip (highest odds).

4. PROTECTION: Thresholds live as clearly named constants under a "DO NOT ALTER" header.
   Testing must prove each market qualifies ONLY when all its filters pass.

--------------------------------------------------------------------------------
## SHARED DEFINITIONS (confirmed by user)

- ODDS GAP = underdog_odds − favourite_odds. Example: favourite 1.00, underdog 1.81 → gap 0.81.
- VENUE SPECIFIC = home/away CONTEXT (home team judged on home form, away team on away form).
  It does NOT refer to a physical stadium/ground.
- "Last 5" = the team's last 5 relevant games (venue-specific where the filter says so).
- Head-to-Head = previous meetings between the two teams.

--------------------------------------------------------------------------------
## MARKETS RECEIVED (3 of 20)

### 1. Straight Win — ALL 5 filters must pass
1. Favourite odds below 2.20 AND odds gap over 0.80.
2. Favourite Points Per Game over 1.60 (venue specific).
3. Match Expected Goals over 1.8 AND favourite Expected Goals over 1.5.
4. Favourite won over 2 games of the last 5 (i.e. 3+) (venue specific).
5. Underdog lost over 1 game of the last 5 (i.e. 2+) (venue specific).

### 2. Double Chance — ALL 4 filters must pass
1. Favourite UNBEATEN (won or drew) in at least 3 of its last 5 games. [clarified]
2. Favourite won at least 2 of the last 5 head-to-head games.
3. Favourite Points Per Game over 1.3 (venue specific).
4. Underdog has NOT won more than 1 game in its last 5 (underdog wins ≤ 1).

### 3. Both Teams To Score — ALL 5 filters must pass
1. Home team scored in over 60% of its home games.
2. Away team scored in over 60% of its away games.
3. Both teams conceded at least one goal in 4 of their last 5 games.
4. Match Expected Goals over 2.5.
5. Both Teams To Score occurred in at least 3 of the last 5 head-to-head meetings. [APPROVED SWAP — replaced "each of last 5 H2H over 1.5 goals"]

### 4. Over 1.5 Total Goals — ALL 4 filters must pass
1. Game (combined) Expected Goals over 2.5.
2. At least one team averages over 1.4 goals per game.
3. At least one team has under 30% clean sheets in their last 10 games.
4. Both teams have been in games producing over 1.5 total goals in 4 of their last 5 games.

### 5. Over 2.5 Total Goals — ALL 4 filters must pass
1. Combined goals average over 2.8.
2. At least one team scores over 1.3 goals on average.
3. At least one team has a clean-sheet rate under 30% in their last 10 games.
4. Both teams have scored at least 1 goal in 7 of their last 10 games.

### 6. Over 0.5 First Half Goals — ALL 5 filters must pass
1. Combined first-half goals average over 1.0.
2. At least one team scored a first-half goal in 3 of their last 5 games.
3. At least one team conceded a first-half goal in 3 of their last 5 games.
4. Both teams scored in the first half in 4 of their last 10 games.
5. Game (combined) Expected Goals over 2.5.

### 7. Over 0.5 Second Half Goals — ALL 4 filters must pass
1. Combined second-half goal-scoring average over 1.1.
2. At least one team scores over 0.6 second-half goals on average.
3. At least one team scored a second-half goal in 4 of their last 5 games.
4. Game (combined) Expected Goals over 2.5.

### 8. Team To Score Over 0.5 Second Half Goals — ALL 4 filters must pass
Backed-team selection: [PENDING CLARIFICATION — Q1]
1. Backed team Points Per Game over 1.3.
2. Backed team Expected Goals over 1.7 for the whole match.
3. Backed team averages over 0.7 second-half goals.
4. Backed team scored a second-half goal in 4 of the last 5 games.

### 9. Under 3.5 Total Goals — ALL 5 filters must pass
1. Game (combined) Expected Goals under 3.5.
2. Both teams had games ending under 2.5 total goals in 4 of their last 10 games.
3. Under 2.5 total goals in 2 of their last 5 head-to-head games.
4. One team has over 20% clean sheets (last 10) AND the other over 10% clean sheets (last 10).
5. Both teams concede under 1.3 goals per game on average.

### 10. Under 4.5 Total Goals — ALL 4 filters must pass
1. Game (combined) Expected Goals under 3.8.
2. At least one team concedes under 1.1 goals per game on average.
3. Under 3.5 total goals in 3 of their last 5 head-to-head games.
4. One team has over 20% clean sheets (last 10) AND the other over 10% clean sheets (last 10).

### 11. Under 1.5 First Half Goals — ALL 4 filters must pass
1. Both teams achieve under 1.5 first-half goals in 50% of their games. [window PENDING — Q3]
2. Both teams failed to score in the first half in 2 of their last 5 games.
3. At least one team has a 30% first-half clean-sheet rate.
4. Both teams' overall under-1.5-first-half-goals hit rate is over 40%. [window PENDING — Q3]

### 12. Draw No Bet — ALL 5 filters must pass
1. Favourite odds under 2.50.
2. Favourite Points Per Game over 1.2.
3. Favourite has not lost in their last 3 head-to-head games.
4. Favourite won 2 games in their last 5 (venue specific). ["won 2" = at least 2 — Q2]
5. Underdog lost 1 game in their last 5 (venue specific). ["lost 1" = at least 1 — Q2]

### 13. Double Chance & Over 1.5 Goals — ALL 5 filters must pass
1. Favourite odds under 2.20.
2. Favourite Points Per Game over 1.5.
3. Game (combined) Expected Goals over 2.5.
4. At least one team averages over 1.2 goals per game.
5. Favourite unbeaten (won or drew) in at least 2 of the last 5 games (venue specific).

### 14. Double Chance & Under 4.5 Goals — ALL 5 filters must pass
1. Favourite odds under 2.20.
2. Favourite Points Per Game over 1.5.
3. Favourite unbeaten (won or drew) in at least 3 of their last 5 games (venue specific).
4. Game (combined) Expected Goals under 3.5.
5. Both teams average under 1.3 goals per game.

### 15. Over 4.5 First Half Corners — ALL 4 filters must pass
1. At least one team has over 55% first-half ball possession in the last 5 games.
2. At least one team averages over 6 total first-half shots.
3. At least one team won over 3.5 first-half corners in 5 of their last 10 games.
4. At least one team conceded over 2.5 first-half corners in 3 of their last 5 games.

### 16. Over 8.5 Total Corners — ALL 4 filters must pass
1. At least one team has over 55% ball possession in their last 5 games.
2. At least one team averages over 12 total shots per game.
3. At least one team won over 6.5 total corners in 5 of their last 10 games.
4. At least one team conceded over 5.5 total corners in 3 of their last 5 games.

### 17. Under 10.5 Total Corners — ALL 4 filters must pass
1. Both teams average under 52% ball possession in their last 5 games.
2. Combined total shots average under 23.
3. At least one team was in games producing under 10.5 total corners in 6 of their last 10 games.
4. Both teams average under 5.0 total corners won per game (last 10). [APPROVED SWAP — replaced "both teams not over 3.5 first-half corners in 6 of last 10"]

### 18. Over 2.5 Total Cards — ALL 4 filters must pass
1. At least one team averages over 16 fouls per game.
2. Combined fouls average over 23.
3. At least one team averages over 1.8 cards per game.
4. At least one team averages over 15 tackles per game.

### 19. Over 3.5 Total Cards — ALL 4 filters must pass
1. Both teams average over 13 tackles per game.
2. Combined fouls average per game over 26.
3. Both teams average over 1.7 cards per game.
4. Both teams average over 12 tackles per game.

### 20. Under 5.5 Total Cards — ALL 4 filters must pass
1. At least one team averages under 15 fouls per game.
2. Combined fouls average per game under 23.
3. At least one team averages under 2.0 cards per game.
4. Combined tackles per game average under 28.

--------------------------------------------------------------------------------
## GLOBAL INTERPRETATION (confirmed with user)
- "not lost in N of last 5" = UNBEATEN (won or drew) in at least N of last 5. [markets 2, 13, 14]
- "won N games" / "lost N games" = AT LEAST N.
- Market 8 backed team = evaluate BOTH teams; back whichever passes all 4; if both, higher blended probability.
- Market 11 windows: both filter 1 and filter 4 use the last 10 games.
- Missing feed stats are ESTIMATED (documented, Poisson-based) without changing thresholds.

## ✅ IMPLEMENTATION STATUS — DONE (single clean pass)
- Engine: /app/backend/services/okamoney_engine.py (all 20 markets, exact filters, all-must-pass,
  blended-probability selection, protected THRESHOLDS block). This spec SUPERSEDES the earlier
  OKAMONEY_FILTERS_REPORT.md (which described the old market set).
- Every surface sources tips ONLY from these 20 markets via the engine: games feed (/games),
  SGP (/sgp), Mixed Parlay (/mixed-parlay), DC singles (/dc-under, /dc-over),
  Ticket Machine (/ticket-machine/generate), Admin WhatsApp tickets (/admin/whatsapp-tickets).
- Guarantee test: /app/backend/tests/test_engine.py (all-filters-must-pass, ranking, clear names).


--------------------------------------------------------------------------------
## FILTER CHANGE LOG (user-approved)
- 2026-08 — Market 3 (Both Teams To Score), filter 5:
    OLD: "each of the last 5 head-to-head meetings individually had over 1.5 goals"
    NEW: "Both Teams To Score in at least 3 of the last 5 head-to-head meetings"
    Rationale: the old filter was voided by a single dull past meeting and ">1.5 goals" does not
    even imply both teams scored (a 2-0 passes it). The new filter measures the actual BTTS outcome
    head-to-head — more predictive of this market and less brittle.
    Effect: modest lift (simulated 36->47 per 300 games; daily pool 10->17 per 120), still selective.
- 2026-08 — Market 17 (Under 10.5 Total Corners), filter 4:
    OLD: "both teams did NOT have over 3.5 first-half corners in 6 of their last 10 games"
    NEW: "both teams average under 5.0 total corners won per game (last 10)"
    Rationale: ~4.5 first-half corners is normal, so "6 of 10 under 3.5" was essentially unreachable
    (0/400 in testing). The new filter targets genuinely low-corner teams, keeping the market strict
    alongside the possession/shots/history filters.
    Effect: from never-hitting to occasionally hitting (simulated 0->4 per 400; deliberately still rare).

# OkaMoney AI Tips — Complete Betting Markets & Filters Report

This document lists every betting market in the engine (`backend/services/stats_analyzer.py`)
and every filter it applies, in full, with exact thresholds. Nothing is omitted.

Legend of terms (written in full below, no shorthand):
- First Half = the first 45 minutes. Second Half = the last 45 minutes.
- Average = the team's per-game average over recent matches (typically last 10).
- Head-to-Head = previous meetings between these two teams.
- Failed To Score = a game in which the team scored zero goals.
- Clean Sheet = a game in which the team conceded zero goals.
- Shots on Target = shots that would have gone into the goal if not saved/blocked on the line.
- Expected Goals = a statistical estimate of goal quality of chances created.
- Points Per Game = average league points earned per match (win = 3, draw = 1, loss = 0).
- Possession = percentage of the match a team has the ball.

---

## 1. Over 2.5 Total Goals — ALL 5 filters must pass
1. Combined goals average of both teams is greater than or equal to 2.8.
2. Both the home team and the away team score at least 1.0 goal on average each.
3. At least one team concedes 1.3 or more goals on average (a leaky defense).
4. Both teams scored in 6 or more of their last 10 games.
5. Combined Shots on Target of both teams is 10 or more.

## 2. Under 3.5 Total Goals — ALL 5 filters must pass
1. Both teams stayed Under 2.5 total goals in 4 or more of their last 10 games.
2. Clean-sheet records: at least one team has more than 2 clean sheets and the other more than 1 (last 10).
3. Both teams concede fewer than 1.3 goals on average (last 10).
4. Both teams average Under 4.5 Shots on Target (last 10).
5. Combined Expected Goals of both teams is below 3.0.

## 3. Over 1.5 Total Goals — ALL 6 filters must pass
1. Combined Expected Goals is greater than 2.2.
2. At least one team has Expected Goals greater than 1.2.
3. Combined Shots on Target is greater than 7.0.
4. Both teams have a clean-sheet rate below 30 percent.
5. Combined goals average is greater than 2.0.
6. At least one team averages more than 1.4 goals.

## 4. Over 0.5 First Half Goals — ALL 4 filters must pass
1. Combined First Half goals average of both teams is greater than or equal to 0.9.
2. At least one team scores 0.5 or more First Half goals on average.
3. Both teams scored a First Half goal in 5 or more of their last 10 games.
4. There is a clear favorite OR the combined First Half goals average is high.

## 5. Over 0.5 Second Half Goals — ALL 4 filters must pass
1. Combined Second Half goals average of both teams is greater than or equal to 1.1.
2. At least one team scores 0.6 or more Second Half goals on average.
3. Both teams scored a Second Half goal in 6 or more of their last 10 games.
4. Combined total goals average of both teams is greater than or equal to 2.5 (an attacking match).

## 6. Under 1.5 First Half Goals — ALL 4 filters must pass
1. At least one team had a 0-0 half-time score in 2 or more of their last 10 games.
2. Both teams have an Under 1.5 First Half hit rate above 40 percent (last 10).
3. Combined First Half average goals is below 1.3.
4. Both teams Failed To Score in the First Half in more than 40 percent of their last 10 games.

## 7. Both Teams To Score — Yes (standard) — ALL 5 filters must pass
1. Home team scores in 60 percent or more of its home games.
2. Away team scores in 55 percent or more of its away games.
3. Home team concedes in 50 percent or more of its home games.
4. Away team concedes in 50 percent or more of its away games.
5. Combined goals average of both teams is greater than or equal to 2.2.

## 8. Both Teams To Score — Yes (enhanced 11-filter version, scored model) — 11 filters
1. Home team scores regularly: home goals average greater than or equal to 1.3.
2. Away team scores regularly: away goals average greater than or equal to 1.2.
3. Home team concedes (lets the away team score): 1.0 or more conceded on average.
4. Away team concedes (lets the home team score): 1.2 or more conceded on average.
5. Low Failed-To-Score rate: home team 15 percent or lower, away team 20 percent or lower.
6. Head-to-Head Both Teams To Score rate is 60 percent or higher.
7. Recent-form Both Teams To Score involvement is 50 percent or higher.
8. Home team's HOME goals average is 1.5 or higher.
9. Away team's AWAY goals average is 1.0 or higher.
10. League Both Teams To Score context (league tends to produce both-teams-scoring games).
11. Form momentum (recent scoring/conceding trend is positive).

## 9. Over 8.5 Total Corners (and the Team First-Half Corner model) — 8 filters, needs 6/8 for "Very High"
Qualification tiers: 6+ filters and score ≥ 60 = Very High; 5+ and ≥ 50 = High; 4+ and ≥ 40 = Medium; 3+ and ≥ 30 = Low.
1. First Half corner estimate is calculated (First Half is 44–47 percent of total corners, plus a 12 percent home-advantage boost).
2. Matchup style analysis: an attacking team versus a defensive team is rated "excellent"; both attacking is a "split"; both defensive is penalized.
3. League corner context: high-corner league (10.5 or more corners per match average) passes; below 9.5 is penalized.
4. Head-to-Head corner history: average of 11 or more corners in past meetings passes strongly; 10 or more passes; below 9 is penalized.
5. Team corner average (tightened): home team 6.0 or more corners per game (excellent) / 5.5 or more (good); away team 5.5 or more (good); below 4.5 fails.
6. Attacking intensity: home team goals average 1.8 or more (or away 1.6 or more) boosts the estimate.
7. Opponent defensive style ("park the bus"): if a team concedes 0.9 or fewer goals, the opponent earns more corners.
8. First Half corner threshold (tightened): estimated home First Half corners 4.5 or more (strong) / 4.0 or more (good); away 4.2 or more (strong) / 3.8 or more (good).

## 10. Over 4.5 First Half Corners — ALL 4 filters must pass
1. At least one team averages over 58 percent possession in the First Half (last 5 games).
2. At least one team averages over 9 total First Half shots.
3. Both teams have Over 4.5 First Half corners in 60 percent of their last 10 matches.
4. At least one team has Over 3.5 First Half corners in 6 of 10 games.

## 11. Under 10.5 Total Corners — ALL 4 filters must pass
1. Both teams average below 53 percent possession.
2. Both teams average under 15 shots each AND their combined shots are under 23.
3. Both teams stayed Under 10.5 corners in 6 of 10 games.
4. Both teams did NOT hit Over 3.5 First Half corners in 6 of 10 games.

## 12. Over 2.5 Total Cards — ALL 5 filters must pass
1. At least one team averages more than 16 fouls per game.
2. Combined fouls per game of both teams is more than 24.
3. At least one team averages more than 1.8 cards per game.
4. Combined cards per game of both teams is more than 3.5.
5. At least one team averages more than 15 tackles per game.

## 13. Over 3.5 Total Cards — ALL 5 filters must pass
1. Both teams average more than 14 tackles per game.
2. Combined fouls per game of both teams is more than 26.
3. Both teams average more than 1.8 cards per game.
4. Combined cards per game of both teams is more than 4.2.
5. Both teams average more than 12 tackles per game (minimum threshold).

## 14. Under 4.5 Total Cards — ALL 5 filters must pass
1. At least one team averages fewer than 15 fouls per game.
2. Combined fouls per game of both teams is fewer than 23.
3. At least one team averages fewer than 1.8 cards per game.
4. Combined cards per game of both teams is fewer than 3.5.
5. At least one team averages fewer than 14 tackles per game.

## 15. Straight Win (1X2) — ALL 5 filters must pass
1. Odds: the favorite's win odds are 1.80 or lower AND the odds gap to the opponent is 0.80 or greater.
2. Points Per Game: the favorite's Points Per Game is 1.60 or higher (venue-specific — home form at home, away form away).
3. Expected Goals: combined Expected Goals greater than 2.5 AND the favorite's Expected Goals greater than 1.8.
4. Favorite's form: won 3 or more of its last 5 (venue-specific).
5. Underdog's form: lost 2 or more of its last 5 (venue-specific).

## 16. Draw No Bet — ALL 6 filters must pass
1. The backed team won 3 or more of its last 5 games.
2. Head-to-Head dominance over the opponent.
3. The backed team concedes fewer than 1.3 goals on average.
4. The opponent has 2 or more losses in recent games.
5. The backed team has fewer draws (cleaner win/lose profile).
6. The backed team has an attacking advantage over the opponent.

## 17. Double Chance + Under 3.5 Goals — ALL 5 filters must pass (odds-based favorite selection)
1. Betting-odds favorite: the selected team's win odds are 2.50 or lower (implied 40 percent-plus chance).
2. Clear odds gap: the favorite's odds are at least 0.50 lower than the opponent's.
3. Under 3.5 hit rate is above 50 percent for at least one team.
4. The favorite has NOT lost to the opponent in the last 3 Head-to-Head meetings.
5. Combined goals average of both teams is below 3.2.

## 18. Double Chance + Under 4.5 Goals — ALL 8 filters must pass
Straight-Win component (selects which Double Chance side, "Home or Draw" / "Away or Draw"):
1. The favorite won 3 or more of its last 5 games.
2. Head-to-Head is positive (at least one win, or unbeaten, in the last 3 meetings).
3. The favorite concedes fewer than 1.3 goals on average.
4. The opponent has 2 or more losses in its last 5 games.
Under 4.5 Goals component:
5. Combined goals average of both teams is below 3.5.
6. At least one team concedes fewer than 1.2 goals on average.
7. Combined Expected Goals is below 3.8.
8. At least one team has a clean-sheet rate above 20 percent.

## 19. Double Chance + Over 1.5 Goals — ALL 10 filters must pass
Straight-Win component (selects which Double Chance side):
1. The favorite won 3 or more of its last 5 games.
2. Head-to-Head is positive (at least one win in the last 3 meetings).
3. The favorite concedes fewer than 1.3 goals on average.
4. The opponent has 2 or more losses in its last 5 games.
Over 1.5 Goals component:
5. Combined Expected Goals is greater than 2.2.
6. At least one team has Expected Goals greater than 1.2.
7. Combined Shots on Target is greater than 7.0.
8. Both teams have a clean-sheet rate below 30 percent.
9. Combined goals average is greater than 2.0.
10. At least one team averages more than 1.4 goals.

## 20. Double Chance + Over 1.5 Goals (legacy simple version) — needs 2 of 3 checks
1. Home team goals average is 1.2 or higher.
2. Away team goals average is 1.0 or higher.
3. Combined goals average is 2.5 or higher.
(Qualifies with 2 of 3; "High" confidence when all 3 pass.)

---

## Summary of markets (20 total)
Goals: Over 2.5, Under 3.5, Over 1.5, Over 0.5 First Half, Over 0.5 Second Half,
Under 1.5 First Half, Both Teams To Score (standard + 11-filter enhanced), Team Over 0.5 Second Half.
Corners: Over 8.5 Total, Over 4.5 First Half, Under 10.5 Total.
Cards: Over 2.5 Total, Over 3.5 Total, Under 4.5 Total.
Result-based: Straight Win (1X2), Draw No Bet, Double Chance + Under 3.5,
Double Chance + Under 4.5, Double Chance + Over 1.5.

Note: Live match statistics feeding these filters are currently MOCKED (synthetic) because the
API-Sports data subscription is inactive. The filter logic itself is fully live and runs exactly as listed above.

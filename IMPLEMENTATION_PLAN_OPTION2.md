# Option 2 Implementation Plan: Odds + Basic Stats Filter

## Overview
This document outlines the implementation strategy for filtering soccer betting picks using odds ranges + basic statistical analysis.

---

## Data Requirements from API-Football

### Essential Endpoints Needed:
1. **Fixtures** - `/fixtures` - Get upcoming matches
2. **Odds** - `/odds` - Get betting odds for each market
3. **Statistics** - `/fixtures/statistics` - Get match statistics
4. **H2H** - `/fixtures/headtohead` - Head-to-head history
5. **Teams Statistics** - `/teams/statistics` - Season performance data

---

## Market-Specific Filtering Rules

### 1. DC + U/4.5 (Double Chance & Under 4.5 Goals)
**Odds Range:** 1.24 - 1.48

**Basic Stats Filters:**
```
✅ QUALIFIES IF:
- Odds in range: 1.24-1.48
- Home team last 5 games average: ≤ 2.3 goals per game
- Away team last 5 games average: ≤ 2.3 goals per game
- H2H last 3 meetings: < 4 goals per match average
- At least one team defensive ranking: Top 60% in league
- Neither team scored 4+ goals in last 5 games
```

**Confidence Levels:**
- **High**: All conditions met + both teams in top 50% defensive rankings
- **Medium**: 4-5 conditions met
- **Low**: 3 conditions met (minimum to show)

---

### 2. DC + O/1.5 (Double Chance & Over 1.5 Goals)
**Odds Range:** 1.22 - 1.34

**Basic Stats Filters:**
```
✅ QUALIFIES IF:
- Odds in range: 1.22-1.34
- Home team last 5 games: Scored in 4+ matches
- Away team last 5 games: Scored in 4+ matches
- H2H last 3 meetings: Over 1.5 goals in 2+ matches
- Combined team goal average: ≥ 2.5 goals per game
- Less than 10% chance of 0-0 (based on team stats)
```

**Confidence Levels:**
- **High**: Both teams scored in all last 5 games
- **Medium**: Both teams scored in 4/5 last games
- **Low**: 3/5 games minimum

---

### 3. 1H Corners O/3.5 (First Half Corners Over 3.5)
**Odds Range:** 1.22 - 1.38
**Leagues:** Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira Liga, Belgian Pro League, Championship, Bundesliga 2, La Liga 2, Serie B, Ligue 2

**Basic Stats Filters:**
```
✅ QUALIFIES IF:
- Odds in range: 1.22-1.38
- League is in allowed list
- Home team 1H corners average: ≥ 3.0
- Away team 1H corners conceded: ≥ 2.5
- Combined 1H corners average: ≥ 4.5
- Last 3 H2H: Over 3.5 1H corners in 2+ matches
- Both teams play high-pressing style (if data available)
```

**Confidence Levels:**
- **High**: Combined average ≥ 5.5 corners + H2H confirms trend
- **Medium**: Combined average 4.5-5.4 corners
- **Low**: Meets minimum criteria

**Note:** Corner data is crucial - if API doesn't provide 1H corner stats, use full match corners and estimate (typically 45-50% occur in 1H)

---

### 4. 1H Corners U/5.5 (First Half Corners Under 5.5)
**Odds Range:** 1.22 - 1.42
**Leagues:** Same as above

**Basic Stats Filters:**
```
✅ QUALIFIES IF:
- Odds in range: 1.22-1.42
- League is in allowed list
- Home team 1H corners average: ≤ 3.5
- Away team 1H corners conceded: ≤ 3.0
- Combined 1H corners average: ≤ 5.0
- Last 3 H2H: Under 5.5 1H corners in 2+ matches
- Teams prefer possession-based play (lower corner counts)
```

**Confidence Levels:**
- **High**: Combined average ≤ 4.0 corners
- **Medium**: Combined average 4.1-5.0 corners
- **Low**: Meets minimum criteria

---

### 5. Over/Under 2.5 Goals
**Odds Range:** Any (but track value)

**Basic Stats Filters:**

#### For OVER 2.5:
```
✅ QUALIFIES IF:
- Combined goals average (last 5): ≥ 3.0 goals
- Home team scoring average: ≥ 1.5 goals
- Away team scoring average: ≥ 1.0 goals
- H2H last 3: Over 2.5 in 2+ matches
- Both teams in top 60% for offensive stats
- Neither team has strong defensive record
```

#### For UNDER 2.5:
```
✅ QUALIFIES IF:
- Combined goals average (last 5): ≤ 2.3 goals
- At least one team defensive ranking: Top 40%
- H2H last 3: Under 2.5 in 2+ matches
- Low-scoring league or stage of season
- Weather conditions favorable for defense (if available)
```

**Confidence Levels:**
- **High**: Strong statistical trend (80%+ hit rate in sample)
- **Medium**: Moderate trend (65-79% hit rate)
- **Low**: Meets criteria but mixed signals

---

### 6. Straight Win (Match Winner)
**Odds Range:** Any (but focus on value)

**Basic Stats Filters:**
```
✅ QUALIFIES IF:
- Form difference: Winner won 3+ of last 5, opponent 2 or fewer
- Home advantage: Home team significantly stronger at home
- League position difference: ≥ 5 positions apart
- H2H record: Favorite won 2+ of last 3 meetings
- Goal difference: Favorite's GD significantly better
- No key injuries to favorite (if data available)
- Not a derby/rivalry match (unpredictable)
```

**Confidence Levels:**
- **High**: All factors align + odds value detected
- **Medium**: 5-6 factors positive
- **Low**: 4 factors positive (minimum)

---

## Implementation Steps

### Phase 1: Data Collection (When API is integrated)
1. Set up API-Football account and get API key
2. Create data fetching functions for all required endpoints
3. Implement caching to avoid API rate limits (cache for 1-6 hours)
4. Build data transformation layer to normalize API responses

### Phase 2: Statistical Engine
1. Create statistical calculator functions:
   - `calculateGoalAverages(team, last_n_games)`
   - `calculateCornerAverages(team, last_n_games, half)`
   - `calculateFormScore(team, last_n_games)`
   - `analyzeH2H(team1, team2, last_n_meetings)`
   - `getDefensiveRanking(team, league)`

2. Create filter validators:
   - `validateDC_U45(match, odds, stats)`
   - `validateDC_O15(match, odds, stats)`
   - `validate1H_CornersOver35(match, odds, stats)`
   - `validate1H_CornersUnder55(match, odds, stats)`
   - `validateOU25(match, odds, stats, direction)`
   - `validateStraightWin(match, odds, stats)`

3. Confidence calculator:
   - `calculateConfidenceLevel(match, stats, market_type)`

### Phase 3: Backend Integration
1. Update `/api/picks` endpoint to:
   - Fetch live data from API-Football
   - Run through statistical filters
   - Apply odds range checks
   - Calculate confidence levels
   - Sort by confidence + odds value

2. Add new endpoint `/api/picks/analysis/{pick_id}`:
   - Return detailed breakdown of why pick qualified
   - Show all stats that influenced decision
   - Display which filters passed/failed

3. Update MongoDB schema to store:
   - Pick generation timestamp
   - Stats used for decision
   - Actual results (for tracking accuracy)

### Phase 4: Frontend Updates
1. Add "Why This Pick?" section showing:
   - Key stats that qualified the match
   - Visual indicators (✅ passed, ⚠️ marginal)
   - Confidence breakdown

2. Add stats visualization:
   - Form charts (last 5 games)
   - Goals/corners averages
   - H2H timeline

3. Add results tracking (optional):
   - Mark picks as won/lost
   - Display accuracy rate per market
   - Show ROI calculations

---

## Example Pick Output

```json
{
  "id": "abc123",
  "match": {
    "home": "Arsenal",
    "away": "Chelsea",
    "league": "Premier League",
    "date": "2025-07-20T15:00:00Z"
  },
  "market": {
    "type": "DC_U4.5",
    "selection": "1X & Under 4.5",
    "odds": 1.35
  },
  "confidence": "High",
  "analysis": "Arsenal's solid defense (1.2 goals conceded avg) combined with Chelsea's low-scoring away form (1.3 goals avg) makes this an excellent under 4.5 pick. Home advantage adds safety to the double chance.",
  "reasoning": "Arsenal unbeaten in last 8 home games, averaging 2.1 total goals. Chelsea's last 5 away games averaged 2.0 goals. H2H last 3 meetings: 1-0, 2-1, 0-0.",
  "stats": {
    "home_form": "W-W-D-W-W",
    "away_form": "W-L-D-L-D",
    "home_goals_avg_last5": 1.4,
    "away_goals_avg_last5": 0.8,
    "combined_avg": 2.2,
    "h2h_avg_goals": 1.3,
    "home_defensive_rank": "3rd/20",
    "filters_passed": [
      "✅ Odds in range (1.35)",
      "✅ Home goals avg ≤ 2.3 (1.4)",
      "✅ Away goals avg ≤ 2.3 (0.8)",
      "✅ H2H avg < 4 (1.3)",
      "✅ Top defensive team (3rd)",
      "✅ No high-scoring games recently"
    ]
  }
}
```

---

## API Rate Limit Strategy

**API-Football Free Tier:** ~100 calls/day
**Our Usage Plan:**
- Fetch fixtures once every 6 hours: 4 calls/day
- Fetch odds for top matches: 20 calls/day
- Fetch stats as needed: 40 calls/day
- Cache everything: 6-hour TTL
- **Total:** ~64 calls/day (within limits)

**Paid Tier:** If needed, upgrade for unlimited calls

---

## Testing Strategy

### Before Going Live:
1. **Backtest on Historical Data**
   - Run filters on last 30 days of matches
   - Calculate hit rate for each market
   - Adjust thresholds if needed

2. **Paper Trading Period**
   - Track picks for 2 weeks without betting
   - Measure accuracy vs confidence levels
   - Fine-tune filters based on results

3. **A/B Testing**
   - Option A: Pure odds (your original ranges)
   - Option B: Odds + stats filters
   - Compare performance over 20 matches

### Success Metrics:
- **Target Hit Rate:** 65%+ overall
- **High Confidence:** 75%+ accuracy
- **Medium Confidence:** 60-70% accuracy
- **ROI:** Positive over 50+ picks

---

## Future Enhancements (Post-Launch)

1. **Machine Learning Model**
   - Train on historical data
   - Predict outcomes with probability
   - Auto-adjust filter thresholds

2. **Advanced Factors**
   - Weather impact on corners
   - Referee statistics
   - Player injuries/suspensions
   - Motivation factors (title race, relegation)

3. **Bankroll Management**
   - Suggest stake sizes based on confidence
   - Kelly Criterion calculator
   - ROI tracking per market

4. **Live Updates**
   - In-play odds changes
   - Live stats during matches
   - Cash-out recommendations

---

## Next Steps

1. ✅ Agree on Option 2 approach
2. ⏳ Choose API provider (API-Football recommended)
3. ⏳ Get API key and test endpoints
4. ⏳ Implement statistical engine
5. ⏳ Backtest on historical data
6. ⏳ Go live with real picks

**Ready to proceed when you get your API key!** 🚀

# API Decision Log

## Current Setup: Smart API "Free API Live Football Data"

### User Subscribed To:
- **API:** Free API Live Football Data by Creativesdev/Smart API
- **Platform:** RapidAPI
- **Key:** fcbe7b349fmshb8cfb14052f3073p1d7f7djsn0ff35555411a
- **Host:** free-api-live-football-data.p.rapidapi.com
- **Cost:** FREE
- **Coverage:** 2,100+ leagues
- **Features:** Fixtures, Odds, Statistics, Livescores, H2H

### Alternative Considered:
- **API:** API-Football by API-SPORTS  
- **Platform:** api-football.com (standalone)
- **Cost:** Free (100/day) or Pro ($19/month for 7,500/day)
- **Coverage:** 1,200+ leagues
- **Status:** Not subscribed yet

## Decision:

**START WITH SMART API (FREE)**
- Test for 2 weeks
- Verify corner statistics availability
- If works well: Stay free!
- If issues: Switch to API-SPORTS Pro

## Next Steps:
1. Adapt integration for Smart API endpoints
2. Test fixtures, odds, statistics
3. Build pick generator
4. Evaluate after 2 weeks

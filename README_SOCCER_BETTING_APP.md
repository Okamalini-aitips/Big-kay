# ⚽ Soccer Betting Bot App

A mobile soccer betting app that provides daily curated picks based on statistical analysis and specific betting markets.

## 📱 Features

### Core Functionality
- **Daily Picks Feed**: View curated betting picks with analysis
- **Market Filters**: Filter by betting market type (DC + U4.5, DC + O1.5, Corners, etc.)
- **Pick Details**: Detailed analysis, reasoning, statistics, and confidence levels
- **Push Notifications**: Daily notifications for new picks
- **User Preferences**: Save preferred markets and notification settings

### Supported Betting Markets

1. **DC + U/4.5** (Double Chance + Under 4.5 goals)
   - Odds range: 1.24 - 1.48

2. **DC + O/1.5** (Double Chance + Over 1.5 goals)
   - Odds range: 1.22 - 1.34

3. **1H Corners O/3.5** (First Half Corners Over 3.5)
   - Odds range: 1.22 - 1.38
   - Restricted to: Top 8 European leagues + Championship, Bundesliga 2, La Liga 2, Serie B, Ligue 2

4. **1H Corners U/5.5** (First Half Corners Under 5.5)
   - Odds range: 1.22 - 1.42
   - Same league restrictions as above

5. **Over/Under 2.5 Goals**
   - Any odds with detailed analysis

6. **Straight Wins**
   - Any odds with detailed analysis

## 🏗️ Architecture

### Frontend (Expo/React Native)
- **Navigation**: Bottom tabs (Picks, Settings) + Stack navigation for details
- **State Management**: React hooks + AsyncStorage
- **Notifications**: expo-notifications
- **UI**: Custom dark theme with glassmorphism design
- **Date Handling**: date-fns

### Backend (FastAPI)
- **Framework**: FastAPI with async support
- **Database**: MongoDB for user preferences
- **Mock Data**: Generated picks with realistic statistics
- **Caching**: 1-hour cache for consistent pick IDs
- **API Endpoints**:
  - `GET /api/picks` - Get all picks with optional filters
  - `GET /api/picks/{id}` - Get specific pick details
  - `GET /api/preferences` - Get user preferences
  - `POST /api/preferences` - Update user preferences
  - `GET /api/markets` - Get available betting markets

### Database
- **MongoDB**: Stores user preferences and notification settings

## 🚀 Running the App

### Backend
```bash
cd /app/backend
python server.py
# Runs on http://0.0.0.0:8001
```

### Frontend
```bash
cd /app/frontend
yarn start
# Opens Expo dev tools
```

### Testing Backend
```bash
# Get all picks
curl http://localhost:8001/api/picks

# Get picks filtered by market
curl http://localhost:8001/api/picks?market_type=DC_U4.5

# Get picks filtered by league
curl http://localhost:8001/api/picks?league=Premier%20League

# Get picks filtered by odds range
curl http://localhost:8001/api/picks?min_odds=1.3&max_odds=1.4
```

## 📊 API Documentation

### GET /api/picks
Query Parameters:
- `market_type` (optional): Filter by market type (DC_U4.5, DC_O1.5, etc.)
- `league` (optional): Filter by league name
- `min_odds` (optional): Minimum odds filter
- `max_odds` (optional): Maximum odds filter

Response: Array of Pick objects

### Pick Object Structure
```json
{
  "id": "uuid",
  "match": {
    "home": "Arsenal",
    "away": "Chelsea",
    "league": "Premier League",
    "date": "2025-07-15T20:00:00Z"
  },
  "market": {
    "type": "DC_U4.5",
    "selection": "1X & Under 4.5",
    "odds": 1.35
  },
  "analysis": "Detailed analysis text...",
  "reasoning": "Reasoning behind the pick...",
  "confidence": "High",
  "stats": {
    "home_form": "W-W-D-W-W",
    "away_form": "W-L-D-W-L",
    "h2h_last_5": "2-1, 1-1, 3-0, 0-2, 1-1"
  }
}
```

## 🎨 Design System

### Colors
- **Background**: `#0f0f1e` (Dark)
- **Cards**: `#1a1a2e` (Dark Gray)
- **Accent**: `#00d4ff` (Cyan Blue)
- **Success**: `#00ff88` (Green)
- **Warning**: `#ffb800` (Orange)
- **Error**: `#ff6b6b` (Red)
- **Text Primary**: `#fff` (White)
- **Text Secondary**: `#7f8c9d` (Gray)

### Typography
- **Headers**: 700 weight, 20-28px
- **Body**: 400-600 weight, 14-16px
- **Captions**: 11-13px

## 🔮 Future Enhancements (API Integration)

When you're ready to integrate real data, consider:

1. **API-Football (RapidAPI)**
   - Comprehensive soccer data
   - Live odds and statistics
   - Fixtures and results
   - Cost: Varies by plan

2. **The Odds API**
   - Real-time betting odds
   - Multiple bookmakers
   - Historical odds data
   - Cost: Free tier available

3. **Implementation Steps**:
   - Get API key from provider
   - Update `server.py` to replace `generate_mock_picks()`
   - Add API calls to fetch live matches and odds
   - Implement data transformation to match current models
   - Add error handling for API failures
   - Set up cron job for daily data updates

## 📱 Notifications

The app supports push notifications for daily picks:

1. **Setup**: User enables notifications in Settings
2. **Permissions**: App requests notification permissions on first enable
3. **Timing**: Configurable notification time (default: 09:00)
4. **Content**: "⚽ Daily Picks Ready! X new picks available for today"

## 🔒 Important Notes

- Currently using **mock data** for demonstration
- All picks are randomly generated with realistic parameters
- Data is cached for 1 hour to maintain consistency
- Ready for API integration when you choose a provider

## 📄 License

This is a personal betting app prototype. Remember: **Betting involves risk. Please gamble responsibly and only bet what you can afford to lose.**

"""
Backend API Test for OkaMoney AI Tips - 20 Markets Verification

Tests the GET /api/games?limit=100 endpoint to verify all 20 betting markets are working.
"""
import requests
import json
from collections import Counter

# Expected 20 markets
EXPECTED_MARKETS = [
    "Both Teams To Score",
    "Double Chance",
    "Double Chance & Over 1.5 Goals",
    "Double Chance & Under 4.5 Goals",
    "Draw No Bet",
    "Over 0.5 First Half Goals",
    "Over 0.5 Second Half Goals",
    "Over 1.5 Total Goals",
    "Over 2.5 Total Cards",
    "Over 2.5 Total Goals",
    "Over 3.5 Total Cards",
    "Over 4.5 First Half Corners",
    "Over 8.5 Total Corners",
    "Straight Win",
    "Team Over 0.5 2H Goals",
    "Under 1.5 First Half Goals",
    "Under 10.5 Total Corners",
    "Under 3.5 Total Goals",
    "Under 4.5 Total Cards",
    "Under 4.5 Total Goals",
]

def test_games_api():
    """Test the /api/games endpoint for all 20 markets."""
    
    print("=" * 80)
    print("🧪 TESTING: GET /api/games?limit=100")
    print("=" * 80)
    print()
    
    # Test 1: Call the API
    print("📡 Test 1: Calling API endpoint...")
    try:
        response = requests.get("http://localhost:8001/api/games?limit=100", timeout=10)
        response.raise_for_status()
        print("✅ API call successful (Status 200)")
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False
    
    print()
    
    # Test 2: Verify response is valid JSON
    print("📋 Test 2: Verifying JSON response...")
    try:
        data = response.json()
        print("✅ Valid JSON response received")
    except Exception as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    
    print()
    
    # Test 3: Verify response structure
    print("🔍 Test 3: Verifying response structure...")
    if 'games' not in data:
        print("❌ Missing 'games' key in response")
        return False
    
    games = data['games']
    total_games = len(games)
    print(f"✅ Found {total_games} games in response")
    
    if total_games != 100:
        print(f"⚠️  Warning: Expected 100 games, got {total_games}")
    
    print()
    
    # Test 4: Extract all unique market names
    print("📊 Test 4: Extracting unique markets from games...")
    all_markets = []
    
    for game in games:
        if 'markets' in game:
            for market in game['markets']:
                if 'market' in market:
                    all_markets.append(market['market'])
    
    unique_markets = sorted(set(all_markets))
    market_counts = Counter(all_markets)
    
    print(f"✅ Extracted {len(all_markets)} total market entries")
    print(f"✅ Found {len(unique_markets)} unique markets")
    print()
    
    # Test 5: Verify exactly 20 unique markets
    print("🎯 Test 5: Verifying 20 unique markets...")
    if len(unique_markets) == 20:
        print("✅ PASS: Exactly 20 unique markets found")
    else:
        print(f"❌ FAIL: Expected 20 markets, found {len(unique_markets)}")
    
    print()
    
    # Test 6: Verify "Team Over 0.5 2H Goals" exists (bug fix verification)
    print("🐛 Test 6: Verifying 'Team Over 0.5 2H Goals' market exists (bug fix)...")
    if "Team Over 0.5 2H Goals" in unique_markets:
        count = market_counts["Team Over 0.5 2H Goals"]
        print(f"✅ PASS: 'Team Over 0.5 2H Goals' market found ({count} occurrences)")
    else:
        print("❌ FAIL: 'Team Over 0.5 2H Goals' market NOT FOUND")
    
    print()
    
    # Test 7: Verify "Both Teams To Score" exists (bug fix verification)
    print("🐛 Test 7: Verifying 'Both Teams To Score' market exists (bug fix)...")
    if "Both Teams To Score" in unique_markets:
        count = market_counts["Both Teams To Score"]
        print(f"✅ PASS: 'Both Teams To Score' market found ({count} occurrences)")
    else:
        print("❌ FAIL: 'Both Teams To Score' market NOT FOUND")
    
    print()
    
    # Test 8: Print complete list of markets found
    print("📋 Test 8: Complete list of markets found:")
    print("-" * 80)
    for i, market in enumerate(unique_markets, 1):
        count = market_counts[market]
        status = "✅" if market in EXPECTED_MARKETS else "⚠️ "
        print(f"{status} {i:2d}. {market:<45} ({count:3d} occurrences)")
    print("-" * 80)
    print()
    
    # Test 9: Check for missing expected markets
    print("🔍 Test 9: Checking for missing expected markets...")
    missing_markets = [m for m in EXPECTED_MARKETS if m not in unique_markets]
    
    if not missing_markets:
        print("✅ PASS: All 20 expected markets are present")
    else:
        print(f"❌ FAIL: {len(missing_markets)} expected markets are missing:")
        for market in missing_markets:
            print(f"   ❌ {market}")
    
    print()
    
    # Test 10: Check for unexpected markets
    print("🔍 Test 10: Checking for unexpected markets...")
    unexpected_markets = [m for m in unique_markets if m not in EXPECTED_MARKETS]
    
    if not unexpected_markets:
        print("✅ PASS: No unexpected markets found")
    else:
        print(f"⚠️  Warning: {len(unexpected_markets)} unexpected markets found:")
        for market in unexpected_markets:
            print(f"   ⚠️  {market}")
    
    print()
    
    # Final Summary
    print("=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"Total Games: {total_games}")
    print(f"Total Market Entries: {len(all_markets)}")
    print(f"Unique Markets Found: {len(unique_markets)}")
    print(f"Expected Markets: {len(EXPECTED_MARKETS)}")
    print(f"Missing Markets: {len(missing_markets)}")
    print(f"Unexpected Markets: {len(unexpected_markets)}")
    print()
    
    # Overall result
    all_tests_passed = (
        len(unique_markets) == 20 and
        "Team Over 0.5 2H Goals" in unique_markets and
        "Both Teams To Score" in unique_markets and
        len(missing_markets) == 0
    )
    
    if all_tests_passed:
        print("✅ ✅ ✅ ALL TESTS PASSED ✅ ✅ ✅")
        print()
        print("🎉 Bug Fix Verified: 'Team Over 0.5 2H Goals' and 'Both Teams To Score' are working!")
        print("🎉 All 20 betting markets are functioning correctly!")
    else:
        print("❌ ❌ ❌ SOME TESTS FAILED ❌ ❌ ❌")
        print()
        print("⚠️  Please review the failed tests above.")
    
    print("=" * 80)
    print()
    
    return all_tests_passed


if __name__ == "__main__":
    success = test_games_api()
    exit(0 if success else 1)

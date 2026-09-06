"""Test API-Football connection"""
from dotenv import load_dotenv
from pathlib import Path
import sys

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Add services to path
sys.path.insert(0, str(ROOT_DIR))

from services.api_football import APIFootballService

def test_connection():
    """Test API connection"""
    print("🔄 Testing API-Football connection...")
    print("=" * 60)
    
    service = APIFootballService()
    
    # Test 1: API Status
    print("\n📡 Test 1: API Status")
    if service.test_connection():
        print("✅ API connection successful!")
    else:
        print("❌ API connection failed!")
        return
    
    # Test 2: Get today's fixtures
    print("\n📅 Test 2: Fetching today's fixtures...")
    from datetime import datetime
    today = datetime.utcnow().strftime('%Y-%m-%d')
    fixtures = service.get_fixtures(date=today)
    
    if fixtures:
        print(f"✅ Found {len(fixtures)} fixtures for {today}")
        if len(fixtures) > 0:
            first_fixture = fixtures[0]
            print(f"\n📋 Sample Fixture:")
            print(f"   {first_fixture['teams']['home']['name']} vs {first_fixture['teams']['away']['name']}")
            print(f"   League: {first_fixture['league']['name']}")
            print(f"   Date: {first_fixture['fixture']['date']}")
    else:
        print("⚠️  No fixtures found (might be off-season or API issue)")
    
    print("\n" + "=" * 60)
    print("✅ API Integration tests complete!")
    print("\n💡 Next steps:")
    print("1. Check if fixtures were found")
    print("2. If no fixtures, try tomorrow's date")
    print("3. Ready to build full pick generator!")

if __name__ == "__main__":
    test_connection()

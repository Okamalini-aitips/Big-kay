"""Explore Smart API endpoints"""
import requests
import os
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

API_KEY = os.getenv('RAPIDAPI_KEY')
API_HOST = os.getenv('RAPIDAPI_HOST')

headers = {
    'X-RapidAPI-Key': API_KEY,
    'X-RapidAPI-Host': API_HOST
}

base_url = f"https://{API_HOST}"

# Common endpoint patterns to test
endpoints_to_test = [
    # Fixtures
    "/football-get-fixtures",
    "/football-get-fixtures-by-date",
    "/fixtures",
    "/fixtures/date",
    
    # Leagues  
    "/football-get-all-leagues",
    "/leagues",
    
    # Odds
    "/football-get-odds",
    "/odds",
    
    # Statistics
    "/football-get-statistics",
    "/statistics",
    "/teams/statistics",
    
    # Teams
    "/football-get-teams",
    "/teams",
]

def test_endpoint(endpoint, params=None):
    """Test an endpoint"""
    try:
        url = f"{base_url}{endpoint}"
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    'success': True,
                    'endpoint': endpoint,
                    'status': 200,
                    'data_preview': str(data)[:200]
                }
            except:
                return {
                    'success': True,
                    'endpoint': endpoint,
                    'status': 200,
                    'data_preview': 'Non-JSON response'
                }
        else:
            return {
                'success': False,
                'endpoint': endpoint,
                'status': response.status_code,
                'error': response.text[:100]
            }
    except Exception as e:
        return {
            'success': False,
            'endpoint': endpoint,
            'error': str(e)
        }

print("🔍 Exploring Smart API endpoints...")
print("=" * 60)

# Test with today's date
today = datetime.utcnow().strftime('%Y-%m-%d')
tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')

params_to_try = [
    {},
    {'date': today},
    {'date': tomorrow},
]

working_endpoints = []

for endpoint in endpoints_to_test:
    print(f"\n📡 Testing: {endpoint}")
    
    for params in params_to_try[:1]:  # Just test without params first
        result = test_endpoint(endpoint, params)
        
        if result['success']:
            print(f"   ✅ SUCCESS (Status: {result['status']})")
            print(f"   Preview: {result['data_preview']}")
            working_endpoints.append(endpoint)
            break  # Found working endpoint
        else:
            if 'status' in result:
                print(f"   ❌ Failed (Status: {result.get('status')})")
            else:
                print(f"   ❌ Error: {result.get('error', 'Unknown')[:50]}")

print("\n" + "=" * 60)
print(f"\n✅ Working endpoints found: {len(working_endpoints)}")
for ep in working_endpoints:
    print(f"   - {ep}")

if not working_endpoints:
    print("\n⚠️  No endpoints found automatically.")
    print("\n💡 Please check RapidAPI playground at:")
    print(f"   https://rapidapi.com/Creativesdev/api/free-api-live-football-data/playground")
    print("\n📋 Look for endpoint names like:")
    print("   - Fixtures endpoints")
    print("   - Odds endpoints")  
    print("   - Statistics endpoints")

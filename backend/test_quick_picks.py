"""Quick test with limited matches"""
from dotenv import load_dotenv
from pathlib import Path
import sys
import logging

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

from services.pick_generator import PickGenerator

print("=" * 80)
print("🎯 QUICK PICK GENERATION TEST (5 matches only)")
print("=" * 80)
print()

generator = PickGenerator()

print("🔄 Generating picks from top 5 matches...")
print("⏰ This will use ~20-30 API calls")
print()

picks = generator.generate_daily_picks(hours_ahead=24, max_matches=5)

print()
print("=" * 80)
print(f"✅ GENERATION COMPLETE! Found {len(picks)} picks")
print("=" * 80)
print()

if picks:
    # Group by confidence
    by_confidence = {'High': [], 'Medium': [], 'Low': []}
    for pick in picks:
        by_confidence[pick['confidence']].append(pick)
    
    print("📊 Picks by Confidence:")
    for conf in ['High', 'Medium', 'Low']:
        print(f"   {conf}: {len(by_confidence[conf])} picks")
    
    print()
    print("🏆 TOP PICKS:")
    print("=" * 80)
    
    # Show high confidence picks first
    top_picks = by_confidence['High'][:3] or picks[:3]
    
    for i, pick in enumerate(top_picks, 1):
        print(f"\n{i}. {pick['match']['home']} vs {pick['match']['away']}")
        print(f"   League: {pick['match']['league']}")
        print(f"   Market: {pick['market']['selection']}")
        print(f"   Odds: {pick['market']['odds']}")
        print(f"   Confidence: {pick['confidence']}")
        print(f"   Analysis: {pick['analysis']}")
else:
    print("⚠️ No picks generated")
    print("Possible reasons:")
    print("- Filters too strict")
    print("- No odds available")
    print("- No statistics for 2024 season")

print()
print("=" * 80)

"""Test the complete pick generation system"""
from dotenv import load_dotenv
from pathlib import Path
import sys
import logging

# Setup
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
sys.path.insert(0, str(ROOT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from services.pick_generator import PickGenerator

def test_pick_generation():
    """Test generating real picks"""
    print("=" * 80)
    print("🎯 SOCCER BETTING BOT - REAL PICK GENERATION TEST")
    print("=" * 80)
    
    generator = PickGenerator()
    
    print("\n🔄 Generating picks for next 24 hours...")
    print("⏰ This will use ~60-80 API calls (out of 100 daily limit)")
    print()
    
    try:
        picks = generator.generate_daily_picks(hours_ahead=24)
        
        print(f"\n✅ GENERATION COMPLETE!")
        print(f"📊 Total Qualified Picks: {len(picks)}")
        print()
        
        if picks:
            # Group by market
            by_market = {}
            for pick in picks:
                market = pick['market']['type']
                if market not in by_market:
                    by_market[market] = []
                by_market[market].append(pick)
                
            print("📋 Picks by Market:")
            for market, market_picks in by_market.items():
                print(f"   {market}: {len(market_picks)} picks")
                
            print("\n" + "=" * 80)
            print("🎯 SAMPLE PICKS (Top 5):")
            print("=" * 80)
            
            for i, pick in enumerate(picks[:5], 1):
                print(f"\n{i}. {pick['match']['home']} vs {pick['match']['away']}")
                print(f"   League: {pick['match']['league']}")
                print(f"   Market: {pick['market']['selection']}")
                print(f"   Odds: {pick['market']['odds']}")
                print(f"   Confidence: {pick['confidence']}")
                print(f"   Analysis: {pick['analysis'][:100]}...")
                
        else:
            print("⚠️  No picks qualified (filters too strict or no suitable matches)")
            print("💡 Tip: Try adjusting Option 2 filter thresholds")
            
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_pick_generation()

import json
from ai_analyzer import analyze_message
import time

# "The Gauntlet" - Test Cases
TEST_CASES = [
    {
        "name": "The Golden Call (Elon)",
        "message": "ELON MUSK JUST TWEETED 'DOGE' OMG BUY NOW!! LINK: https://x.com/elonmusk/status/...",
        "expected_range": (90, 100),
        "desc": "Elon mention + urgency"
    },
    {
        "name": "The Dev Call (WIF)",
        "message": "New deployment from the dev who made $WIF. CA: 8x... Team is based, heavily accumulating.",
        "expected_range": (85, 100),
        "desc": "Proven dev track record"
    },
    {
        "name": "The Gigachad (Insider)",
        "message": "Gigachad wallet 7x... just bought 5% supply. Smart money is loading up heavily before marketing push.",
        "expected_range": (80, 95),
        "desc": "Insider/Smart money signal"
    },
    {
        "name": "The Generic (Shill)",
        "message": "Buy this coin, strictly mooners only! 100x gem 🚀 LFG guys fill your bags now!!",
        "expected_range": (0, 50),
        "desc": "Generic hype, no substance"
    },
    {
        "name": "The Scam (Presale)",
        "message": "Presale live now! Send SOL to this wallet for airdrop. Do not miss out, 1000x potential.",
        "expected_range": (0, 20),
        "desc": "Obvious scam/presale pattern"
    }
]

def run_gauntlet():
    print("🥊 STARTING THE GAUNTLET: AI Validation Test 🥊")
    print("="*60)
    
    passes = 0
    fails = 0
    
    for case in TEST_CASES:
        print(f"\n🧪 Testing: {case['name']}")
        print(f"📝 Message: {case['message'][:60]}...")
        print(f"🎯 Expected Score: {case['expected_range'][0]}-{case['expected_range'][1]}")
        
        try:
            start_time = time.time()
            result = analyze_message(case['message'])
            elapsed = time.time() - start_time
            
            score = result.get('score', 0)
            analysis = result.get('analysis', "No analysis")
            
            # Check if score is within range
            min_s, max_s = case['expected_range']
            passed = min_s <= score <= max_s
            
            status = "✅ PASS" if passed else "❌ FAIL"
            if passed: passes += 1
            else: fails += 1
            
            print(f"{status} | Score: {score} | Time: {elapsed:.2f}s")
            print(f"🧠 Analysis: {analysis}")
            
        except Exception as e:
            print(f"⚠️ ERROR: {e}")
            fails += 1
            
    print("\n" + "="*60)
    print(f"📊 FINAL RESULTS: {passes} Passed, {fails} Failed")
    if fails == 0:
        print("🏆 AI PASSED THE GAUNTLET! Ready for deployment.")
    else:
        print("⚠️ AI NEEDS TUNING. Check failed cases.")

if __name__ == "__main__":
    run_gauntlet()

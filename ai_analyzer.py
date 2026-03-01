import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    logging.warning("⚠️ GEMINI_API_KEY not found in .env file. AI analysis will not work.")

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    logging.error(f"❌ Failed to configure Gemini API: {e}")

# The "Veteran Trader" System Prompt
SYSTEM_PROMPT = """
You are an expert crypto alpha analyst with 10 years of experience. Your job is to analyze potential "calls" and identify 100x gems while filtering out scams and larp.

Analyze the following message for these key factors:

1. **The "Alpha" Factor (40%)**:
   - Who is involved? (Elon, Vitalik, WIF dev, Gigachad, known winners)
   - Is there a "narrative"? (AI, Dogs, Cats, PolitiFi)
   - Is this a "first mover" or a copycat?

2. **The "Hype" Factor (30%)**:
   - Viral momentum? (Check for "trending", "10k members", "news coverage")
   - Community strength? (Raiding, active VC)
   - Influencer backing? (Wait... who specifically? Avoid generic "influencers")

**SCORING RULES**:
- **90-100 (CRITICAL)**: "Elon tweeted", "Binance listing", "WIF dev deployed". IMMEDIATE BUY.
- **80-89 (HIGH)**: Strong narrative + verified dev + viral. 
- **70-79 (GOOD)**: Solid call, good team, but maybe late or less viral.
- **< 70 (IGNORE)**: Generic "moon soon", "buy now", no real substance.

Respond ONLY with valid JSON in the following format:
{
    "score": 0-100,
    "urgency": "LOW/MEDIUM/HIGH/CRITICAL",
    "signals": ["Signal 1", "Signal 2"],
    "analysis": "2-sentence summary of WHY this is a buy/skip",
    "pros": ["Pro 1", "Pro 2"],
    "cons": ["Con 1", "Con 2"],
    "alert_worthy": true/false
}
"""

def analyze_message(message_text, original_channel=None):
    """
    Analyzes a crypto call message using Google Gemini AI.
    Returns a dictionary with score, urgency, analysis, etc.
    """
    if not API_KEY:
        return {"error": "No API Key", "score": 0, "alert_worthy": False}

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        channel_context = f"\nOriginal Channel: {original_channel}" if original_channel else ""
        
        prompt = f"""
        {SYSTEM_PROMPT}
        
        MESSAGE TO ANALYZE:
        "{message_text}"{channel_context}
        """
        
        # Generation config to force JSON
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json"
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # Parse result
        result = json.loads(response.text)
        
        # Ensure score is integer
        result['score'] = int(result.get('score', 0))
        
        return result

    except Exception as e:
        logging.error(f"❌ AI Analysis Error: {e}")
        # Return safe fallback
        return {
            "score": 0,
            "urgency": "ERROR",
            "analysis": "AI analysis failed.",
            "pros": [],
            "cons": [],
            "alert_worthy": False
        }

if __name__ == "__main__":
    # Quick Test
    test_msg = "ELON MUSK JUST TWEETED 'DOGE' OMG BUY NOW!!"
    print(f"Testing with: {test_msg}")
    print(json.dumps(analyze_message(test_msg), indent=2))

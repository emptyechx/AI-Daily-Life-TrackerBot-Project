import logging
import random
from datetime import timedelta
from typing import Optional
import google.generativeai as genai
from config import get_gemini_api_key
from ai.gemini_client import get_model, is_ai_available

logger = logging.getLogger(__name__)

# Configure Gemini
try:
    genai.configure(api_key=get_gemini_api_key())
    model = get_model()
    logger.info("Gemini configured for quick responses")
except Exception as e:
    logger.error(f"Failed to configure Gemini for quick responses: {e}")
    model = None


# ============================================================================
# TEMPLATE RESPONSES (Fallback - No AI Needed)
# ============================================================================

MORNING_TEMPLATES = {
    'high_energy': [
        "Great sleep fuels great days! You're set up for success. 🌟",
        "Well-rested and ready! Your energy shows. Channel it wisely. ⚡",
        "Solid sleep = solid start. Make today count! 💪",
        "You woke up strong! Use this momentum all day. 🚀"
    ],
    'low_sleep': [
        "Rough night? Be gentle with yourself today. Small wins count. 💪",
        "Low sleep noted. Focus on basics: water, short breaks, early night tonight. 🌙",
        "Tired start? That's okay. Your best effort is enough today. 🌱",
        "Rest wasn't ideal, but you showed up. That matters. 💙"
    ],
    'low_mood': [
        "Starting tough? Remember: your mood can shift. One step at a time. 🌱",
        "Low mood mornings happen. Be kind to yourself today. 💙",
        "Tough morning? Even small actions can turn the day around. ✨",
        "You're feeling low, and that's valid. Take it easy today. 🫂"
    ],
    'low_energy': [
        "Low energy morning. Prioritize what truly matters today. 🎯",
        "Energy's low - that's your body talking. Listen to it. 🔋",
        "Sluggish start? Movement and water are your friends. 💧",
        "Not at your peak? Focus on survival mode today. You got this. 💪"
    ],
    'balanced': [
        "Morning check-in complete! Focus on what you can control today. ✨",
        "Solid start! Keep building on this momentum. 🚀",
        "You showed up and tracked. That's already a win. ✅",
        "Balanced morning. Steady wins the race. 🌅"
    ]
}


def get_template_morning_response(
    sleep_quality: int,
    mood: int,
    energy: int
) -> str:
    """Get template-based morning response (no AI, instant)."""
    
    # Prioritize most critical factor
    if sleep_quality <= 2:
        return random.choice(MORNING_TEMPLATES['low_sleep'])
    elif mood <= 2:
        return random.choice(MORNING_TEMPLATES['low_mood'])
    elif energy <= 2:
        return random.choice(MORNING_TEMPLATES['low_energy'])
    elif sleep_quality >= 4 and mood >= 4 and energy >= 4:
        return random.choice(MORNING_TEMPLATES['high_energy'])
    else:
        return random.choice(MORNING_TEMPLATES['balanced'])


# ============================================================================
# AI-POWERED MORNING MOTIVATION
# ============================================================================

async def generate_morning_motivation(
    sleep_quality: int,
    mood: int,
    energy: int,
    use_ai: bool = False
) -> str:
    """
    Generate morning motivation message.
    
    Args:
        sleep_quality: Sleep rating 1-5
        mood: Mood rating 1-5
        energy: Energy rating 1-5
        use_ai: Whether to use AI (True) or templates (False)
    
    Returns:
        Motivational message string
    """
    # Use templates for first few days (faster, free)
    if not use_ai or not model:
        return get_template_morning_response(sleep_quality, mood, energy)
    
    try:
        prompt = f"""Generate ONE motivational sentence (max 15 words) for someone who just rated:
Sleep: {sleep_quality}/5
Mood: {mood}/5  
Energy: {energy}/5

Be encouraging and specific to their state. No generic quotes. Add one emoji at end."""
        
        response = model.generate_content(prompt)
        message = response.text.strip()
        
        # Fallback if too long or empty
        if not message or len(message) > 250:
            return get_template_morning_response(sleep_quality, mood, energy)
        
        return message
        
    except Exception as e:
        logger.error(f"Error generating morning motivation: {e}")
        return get_template_morning_response(sleep_quality, mood, energy)


# ============================================================================
# DAY ACKNOWLEDGMENT (Template-based, no AI)
# ============================================================================

async def generate_day_acknowledgment(
    morning_mood: int,
    current_mood: int,
    energy: int,
    stress: int
) -> str:
    """
    Generate mid-day acknowledgment (template-based, no AI).
    
    Args:
        morning_mood: Morning mood rating
        current_mood: Current mood rating
        energy: Current energy rating
        stress: Current stress rating
    
    Returns:
        Acknowledgment message
    """
    mood_change = current_mood - morning_mood
    
    # Prioritize by significance
    if mood_change >= 2:
        return "Your mood lifted since morning! Keep the momentum going. 🚀"
    elif mood_change <= -2:
        return "Mood dipped from morning - that's normal. Take a moment to breathe. 🌬️"
    elif stress >= 4:
        return "High stress detected. Take 3 deep breaths before continuing. 🧘"
    elif energy <= 2:
        return "Energy low? Quick walk or healthy snack might help. 🔋"
    elif current_mood >= 4 and energy >= 4:
        return "Strong midday energy! You're crushing it today. 💪"
    else:
        return "Halfway through! You're tracking your day like a pro. 📊"


# ============================================================================
# EVENING DAILY SUMMARY (AI-powered, detailed)
# ============================================================================

async def generate_daily_summary(
    morning_entry: dict,
    day_entry: dict,
    evening_entry: dict,
    previous_day: Optional[dict] = None
) -> str:
    """
    Generate end-of-day AI summary with insights and tip.
    
    This is the MAIN AI interaction - runs every evening.
    
    Args:
        morning_entry: Morning check-in data
        day_entry: Day check-in data
        evening_entry: Evening check-in data
        previous_day: Previous day's evening entry (for comparison)
    
    Returns:
        Daily summary with insight and tip (2-3 sentences)
    """
    if not model:
        return _get_fallback_summary(evening_entry)
    
    try:
        # Extract ratings
        sleep = morning_entry.get('sleep_quality', 'N/A')
        morning_mood = morning_entry.get('mood', 'N/A')
        morning_energy = morning_entry.get('energy', 'N/A')
        
        day_mood = day_entry.get('mood', 'N/A')
        day_energy = day_entry.get('energy', 'N/A')
        day_stress = day_entry.get('stress', 'N/A')
        
        evening_mood = evening_entry.get('mood', 'N/A')
        evening_stress = evening_entry.get('stress', 'N/A')
        satisfaction = evening_entry.get('daily_satisfaction', False)
        
        # Get tags (compact representation)
        all_tags = []
        for entry in [morning_entry, day_entry, evening_entry]:
            if entry and entry.get('tags'):
                all_tags.extend(entry['tags'])
        
        # Count tag frequency for today
        from collections import Counter
        tag_counts = Counter(all_tags)
        top_tags = [f"{tag}({count})" for tag, count in tag_counts.most_common(3)]
        tags_str = ", ".join(top_tags) if top_tags else "none"
        
        # Compare to yesterday
        comparison = ""
        if previous_day and evening_mood != 'N/A':
            prev_mood = previous_day.get('mood', 3)
            mood_diff = evening_mood - prev_mood
            if abs(mood_diff) >= 1:
                direction = "up" if mood_diff > 0 else "down"
                comparison = f"Mood {direction} {abs(mood_diff):.1f} vs yesterday. "
        
        # Mood trajectory today
        trajectory = ""
        if all(x != 'N/A' for x in [morning_mood, day_mood, evening_mood]):
            if evening_mood > morning_mood:
                trajectory = "Mood improved throughout day. "
            elif evening_mood < morning_mood:
                trajectory = "Mood declined as day went on. "
        
        # Create compact prompt
        prompt = f"""Analyze this person's day and provide a 2-3 sentence summary with one specific tip:

**Day Progression:**
Morning: sleep {sleep}/5, mood {morning_mood}/5, energy {morning_energy}/5
Midday: mood {day_mood}/5, energy {day_energy}/5, stress {day_stress}/5
Evening: mood {evening_mood}/5, stress {evening_stress}/5, satisfied: {"yes" if satisfaction else "no"}

**Context:**
{trajectory}{comparison}
Themes: {tags_str}

**Task:**
Write 2-3 sentences that:
1. Acknowledge one pattern you notice (how ratings changed OR impact of tags)
2. Give ONE specific, actionable tip for tomorrow based on their data

Be warm and conversational. Use "you/your". Reference their actual numbers or themes."""

        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        # Clean up formatting
        summary = summary.replace('**', '').replace('*', '')
        
        # Ensure reasonable length
        if len(summary) > 800:
            sentences = summary.split('. ')
            summary = '. '.join(sentences[:3]) + '.'
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}", exc_info=True)
        return _get_fallback_summary(evening_entry)


def _get_fallback_summary(evening_entry: dict) -> str:
    """Generate fallback summary when AI fails."""
    satisfaction = evening_entry.get('daily_satisfaction', False)
    mood = evening_entry.get('mood', 3)
    stress = evening_entry.get('stress', 3)
    
    if satisfaction and mood >= 4:
        return "Great day! Your satisfaction and mood show it. Keep doing what's working. 🌟"
    elif not satisfaction and stress >= 4:
        return "Tough day with high stress. That's valid. Tomorrow's a fresh start - rest well tonight. 💙"
    elif mood <= 2:
        return "Challenging day noted. Be gentle with yourself. Small steps tomorrow. 🌱"
    else:
        return "Day complete! You showed up and tracked. That's progress. Rest well. 💤"


# ============================================================================
# CONDITIONAL RESPONSE (For significant events)
# ============================================================================

async def generate_empathetic_response(
    context: str,
    mood: int,
    stress: int,
    tags: list
) -> Optional[str]:
    """
    Generate empathetic response for significant events.
    Only call this when mood drops significantly or stress is very high.
    
    Args:
        context: Brief context (what changed)
        mood: Current mood rating
        stress: Current stress rating
        tags: Extracted tags
    
    Returns:
        Empathetic message or None
    """
    if not model:
        return None
    
    try:
        tags_str = ", ".join(tags[:3]) if tags else "none"
        
        prompt = f"""Someone just checked in with:
Mood: {mood}/5
Stress: {stress}/5
Context: {context}
Themes: {tags_str}

Write ONE empathetic sentence (max 20 words) that:
- Acknowledges their struggle specifically
- Offers gentle, actionable suggestion

Be human and caring. No platitudes."""
        
        response = model.generate_content(prompt)
        message = response.text.strip()
        
        if len(message) > 300:
            return None
        
        return message
        
    except Exception as e:
        logger.error(f"Error generating empathetic response: {e}")
        return None


# ============================================================================
# RESPONSE DECISION LOGIC
# ============================================================================

def should_send_empathetic_response(
    current_mood: int,
    previous_mood: Optional[int],
    stress: int,
    note_length: int
) -> bool:
    """
    Decide if we should send an empathetic AI response during check-in.
    
    Args:
        current_mood: Current mood rating
        previous_mood: Previous mood (from earlier today or yesterday)
        stress: Current stress rating
        note_length: Length of user's note
    
    Returns:
        True if should send response
    """
    # Major mood drop
    if previous_mood and current_mood - previous_mood <= -3:
        return True
    
    # Very high stress with detailed note
    if stress >= 5 and note_length > 50:
        return True
    
    # Consistently low mood with context
    if current_mood <= 2 and note_length > 30:
        return True
    
    return False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_ai_available() -> bool:
    """Check if AI service is available."""
    return model is not None


async def test_quick_responses():
    """Test function for quick responses."""
    print("Testing Quick Responses System...")
    print("=" * 50)
    
    # Test morning motivation
    print("\n1. Morning Motivation (Template):")
    msg = await generate_morning_motivation(4, 4, 4, use_ai=False)
    print(f"   {msg}")
    
    print("\n2. Morning Motivation (AI):")
    msg = await generate_morning_motivation(2, 2, 2, use_ai=True)
    print(f"   {msg}")
    
    # Test day acknowledgment
    print("\n3. Day Acknowledgment:")
    msg = await generate_day_acknowledgment(4, 2, 2, 4)
    print(f"   {msg}")
    
    # Test daily summary
    print("\n4. Daily Summary:")
    morning = {'sleep_quality': 3, 'mood': 4, 'energy': 4, 'tags': ['exercise']}
    day = {'mood': 3, 'energy': 2, 'stress': 4, 'tags': ['work_stress']}
    evening = {'mood': 3, 'stress': 3, 'daily_satisfaction': False, 'tags': []}
    
    summary = await generate_daily_summary(morning, day, evening)
    print(f"   {summary}")
    
    print("\n" + "=" * 50)
    print("✅ Tests complete!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_quick_responses())
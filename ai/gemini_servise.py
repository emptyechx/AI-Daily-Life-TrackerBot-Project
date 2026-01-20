import logging
import google.generativeai as genai
from typing import Optional
from config import get_gemini_api_key
from ai.gemini_client import get_model, is_ai_available
from utils.text_formatter import clean_ai_response, format_ai_insights

logger = logging.getLogger(__name__)

# Configure Gemini
try:
    genai.configure(api_key=get_gemini_api_key())
    model = get_model()
    logger.info("Gemini AI configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Gemini: {e}")
    model = None


async def generate_weekly_insights(
    user_data: dict,
    entries: list[dict]
) -> dict:
    """
    Generate AI insights from weekly data.
    
    Args:
        user_data: User profile information
        entries: List of check-in entries for the week
    
    Returns:
        dict with 'summary' and 'recommendations'
    """
    if not model:
        return {
            "summary": "AI insights unavailable. Keep tracking your progress!",
            "recommendations": "Continue your daily check-ins to build better patterns."
        }
    
    try:
        # Calculate statistics
        moods = [e.get('mood') for e in entries if e.get('mood')]
        energies = [e.get('energy') for e in entries if e.get('energy')]
        stress_levels = [e.get('stress') for e in entries if e.get('stress')]
        sleep_quality = [e.get('sleep_quality') for e in entries if e.get('sleep_quality')]
        
        avg_mood = round(sum(moods) / len(moods), 2) if moods else None
        avg_energy = round(sum(energies) / len(energies), 2) if energies else None
        avg_stress = round(sum(stress_levels) / len(stress_levels), 2) if stress_levels else None
        avg_sleep = round(sum(sleep_quality) / len(sleep_quality), 2) if sleep_quality else None
        
        # Get user notes and reflections
        notes = []
        for entry in entries:
            if entry.get('user_notes'):
                notes.append(entry.get('user_notes'))
            if entry.get('conditional_answer'):
                notes.append(entry.get('conditional_answer'))
            if entry.get('day_reflection'):
                notes.append(entry.get('day_reflection'))
        
        user_notes_text = "\n".join(notes[:20]) if notes else "No notes provided"  # Limit to 5 notes
        
        # Create prompt for Gemini
        prompt = f"""You are a compassionate wellness coach analyzing a user's weekly check-in data. Provide empathetic, actionable insights.

**User Profile:**
- Age: {user_data.get('age', 'N/A')}
- Activity Level: {user_data.get('activity_level', 'N/A')}
- Tracked Habits: {', '.join(user_data.get('habits', [])) if user_data.get('habits') else 'None'}

**This Week's Data:**
- Average Mood: {avg_mood}/5
- Average Energy: {avg_energy}/5
- Average Stress: {avg_stress}/5
- Average Sleep Quality: {avg_sleep}/5
- Completed Check-ins: {len(entries)}

**User's Recent Notes:**
{user_notes_text[:800]}

**Task:**
1. Provide a brief 2-3 sentence summary of their week's patterns
2. Give 3 specific, actionable recommendations to improve their well-being

Keep tone warm, supportive, and practical. Focus on small, achievable changes.

Format your response as:
SUMMARY: [your summary]
RECOMMENDATIONS:
1. [recommendation 1]
2. [recommendation 2]
3. [recommendation 3]"""
        
        # Generate insights
        response = model.generate_content(prompt)
        result_text = response.text
        
        # Parse response
        summary = ""
        recommendations = ""
        
        if "SUMMARY:" in result_text:
            parts = result_text.split("RECOMMENDATIONS:")
            summary = parts[0].replace("SUMMARY:", "").strip()
            if len(parts) > 1:
                recommendations = parts[1].strip()
        else:
            # Fallback if format not followed
            lines = result_text.split('\n')
            summary = ' '.join(lines[:3])
            recommendations = '\n'.join(lines[3:])
        
        summary = clean_ai_response(summary, max_length=1500)
        recommendations = clean_ai_response(recommendations, max_length=2000)
        
        return {
            "summary": summary,  # Limit length
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}", exc_info=True)
        return {
            "summary": "Unable to generate insights this week. Keep tracking!",
            "recommendations": "Continue your daily check-ins to build better patterns."
        }


async def get_motivational_message(mood: int, energy: int) -> str:
    """
    Generate a quick motivational message based on current state.
    
    Args:
        mood: Current mood rating (1-5)
        energy: Current energy rating (1-5)
    
    Returns:
        Motivational message string
    """
    if not model:
        return "Keep going! Every check-in is progress. 💪"
    
    try:
        prompt = f"""Generate a short (1 sentence, max 15 words) motivational message for someone who just rated their:
- Mood: {mood}/5
- Energy: {energy}/5

Be empathetic, encouraging, and practical. No clichés or platitudes."""
        
        response = model.generate_content(prompt)
        message = response.text.strip()
        
        # Ensure it's not too long
        if len(message) > 100:
            message = message[:97] + "..."
        
        return message
    except Exception as e:
        logger.error(f"Error generating motivation: {e}")
        return "Keep going! Every check-in is progress. 💪"


async def analyze_conditional_response(
    question: str,
    answer: str,
    rating_context: dict
) -> Optional[str]:
    """
    Analyze user's response to conditional question.
    
    Args:
        question: The question that was asked
        answer: User's answer
        rating_context: Dict with mood, energy, stress ratings
    
    Returns:
        Brief insight or None
    """
    if not model or not answer or len(answer) < 10:
        return None
    
    try:
        prompt = f"""A user answered a wellness check-in question. Provide a brief (1 sentence) supportive response.

Question: {question}
Their answer: {answer}
Their ratings: Mood {rating_context.get('mood', 'N/A')}/5, Energy {rating_context.get('energy', 'N/A')}/5, Stress {rating_context.get('stress', 'N/A')}/5

Respond with empathy and validation. Be concise."""
        
        response = model.generate_content(prompt)
        return response.text.strip()[:200]  # Limit to 200 chars
    except Exception as e:
        logger.error(f"Error analyzing response: {e}")
        return None


async def suggest_habit_based_on_patterns(
    user_habits: list[str],
    weekly_averages: dict
) -> Optional[str]:
    """
    Suggest a new habit based on user's patterns.
    
    Args:
        user_habits: List of habits user is already tracking
        weekly_averages: Dict with avg mood, energy, stress, sleep
    
    Returns:
        Habit suggestion or None
    """
    if not model:
        return None
    
    try:
        prompt = f"""Based on this wellness data, suggest ONE specific habit to add:

Current habits: {', '.join(user_habits) if user_habits else 'None'}
Average mood: {weekly_averages.get('avg_mood', 'N/A')}/5
Average energy: {weekly_averages.get('avg_energy', 'N/A')}/5
Average stress: {weekly_averages.get('avg_stress', 'N/A')}/5
Average sleep: {weekly_averages.get('avg_sleep_quality', 'N/A')}/5

Suggest ONE new habit they should track. Be specific and actionable (e.g., "Track 15-minute morning walks" not "Exercise more").
Format: Just the habit name, 3-5 words."""
        
        response = model.generate_content(prompt)
        habit = response.text.strip()
        
        # Clean up the response
        habit = habit.replace('"', '').replace("'", '')
        if len(habit) > 50:
            habit = habit[:50]
        
        return habit
    except Exception as e:
        logger.error(f"Error suggesting habit: {e}")
        return None
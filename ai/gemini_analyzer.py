import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter

from utils.constants import TAG_CATEGORIES
from utils.cache import cache_async, weekly_stats_key

logger = logging.getLogger(__name__)


@cache_async(ttl=3600, key_func=lambda user_id, entries: f"patterns:{user_id}:{len(entries)}")
async def analyze_weekly_patterns(
    user_id: int,
    entries: List[dict]
) -> Dict:
    """
    Analyze patterns from a week of entries.
    CACHED for 1 hour (Issue #15)
    
    Args:
        user_id: Telegram user ID
        entries: List of entry dictionaries for the week
    
    Returns:
        Dictionary with pattern analysis results
    """
    if not entries or len(entries) < 3:
        return {
            "tag_frequency": {},
            "correlations": [],
            "trends": {},
            "confidence": 0.0
        }
    
    try:
        # Extract all tags
        all_tags = []
        for entry in entries:
            if entry.get('tags'):
                all_tags.extend(entry['tags'])
        
        # Count tag frequency
        tag_frequency = dict(Counter(all_tags))
        
        # Find correlations
        correlations = find_correlations(entries)
        
        # Detect trends
        trends = detect_trends(entries)
        
        # Calculate confidence (based on data completeness)
        confidence = calculate_confidence(entries)
        
        # Get top themes using centralized categories
        top_stressors = get_top_tags_by_category(tag_frequency, 'stressor')
        top_activities = get_top_tags_by_category(tag_frequency, 'activity')
        
        return {
            "tag_frequency": tag_frequency,
            "correlations": correlations,
            "trends": trends,
            "top_stressors": top_stressors,
            "top_positive_activities": top_activities,
            "confidence": confidence,
            "entries_analyzed": len(entries)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}", exc_info=True)
        return {
            "tag_frequency": {},
            "correlations": [],
            "trends": {},
            "confidence": 0.0
        }


def find_correlations(entries: List[dict]) -> List[Dict]:
    """
    Find correlations between tags and ratings.
    
    For example: When "work_stress" tag appears, sleep_quality drops.
    
    Args:
        entries: List of entries
    
    Returns:
        List of correlation findings
    """
    correlations = []
    
    # Group entries by tag presence
    tag_groups = {}
    
    for entry in entries:
        tags = entry.get('tags', [])
        mood = entry.get('mood')
        energy = entry.get('energy')
        stress = entry.get('stress')
        sleep = entry.get('sleep_quality')
        
        for tag in tags:
            if tag not in tag_groups:
                tag_groups[tag] = {
                    'entries': [],
                    'mood': [],
                    'energy': [],
                    'stress': [],
                    'sleep': []
                }
            
            tag_groups[tag]['entries'].append(entry)
            if mood: tag_groups[tag]['mood'].append(mood)
            if energy: tag_groups[tag]['energy'].append(energy)
            if stress: tag_groups[tag]['stress'].append(stress)
            if sleep: tag_groups[tag]['sleep'].append(sleep)
    
    # Calculate average impact for each tag
    all_mood = [e.get('mood') for e in entries if e.get('mood')]
    all_sleep = [e.get('sleep_quality') for e in entries if e.get('sleep_quality')]
    
    avg_mood = sum(all_mood) / len(all_mood) if all_mood else 3
    avg_sleep = sum(all_sleep) / len(all_sleep) if all_sleep else 3
    
    # Find significant correlations
    for tag, data in tag_groups.items():
        if len(data['entries']) < 2:  # Need at least 2 occurrences
            continue
        
        # Check mood impact
        if data['mood']:
            tag_avg_mood = sum(data['mood']) / len(data['mood'])
            mood_impact = tag_avg_mood - avg_mood
            
            if abs(mood_impact) >= 0.5:  # Significant difference
                correlations.append({
                    'trigger': tag,
                    'impact': 'mood',
                    'effect': round(mood_impact, 2),
                    'description': f"When {tag.replace('_', ' ')}, mood changes by {mood_impact:+.1f}"
                })
        
        # Check sleep impact
        if data['sleep']:
            tag_avg_sleep = sum(data['sleep']) / len(data['sleep'])
            sleep_impact = tag_avg_sleep - avg_sleep
            
            if abs(sleep_impact) >= 0.5:
                correlations.append({
                    'trigger': tag,
                    'impact': 'sleep_quality',
                    'effect': round(sleep_impact, 2),
                    'description': f"When {tag.replace('_', ' ')}, sleep quality changes by {sleep_impact:+.1f}"
                })
    
    # Sort by absolute impact
    correlations.sort(key=lambda x: abs(x['effect']), reverse=True)
    
    return correlations[:10]  # Return top 10 correlations


def detect_trends(entries: List[dict]) -> Dict[str, str]:
    """
    Detect trends in mood, energy, stress over the week.
    
    Args:
        entries: List of entries sorted by date
    
    Returns:
        Dictionary with trend for each metric
    """
    trends = {}
    
    # Sort entries by date
    sorted_entries = sorted(entries, key=lambda x: x.get('entry_date', ''))
    
    # Analyze mood trend
    moods = [e.get('mood') for e in sorted_entries if e.get('mood')]
    if len(moods) >= 3:
        trends['mood'] = calculate_trend(moods)
    
    # Analyze energy trend
    energies = [e.get('energy') for e in sorted_entries if e.get('energy')]
    if len(energies) >= 3:
        trends['energy'] = calculate_trend(energies)
    
    # Analyze stress trend
    stresses = [e.get('stress') for e in sorted_entries if e.get('stress')]
    if len(stresses) >= 3:
        trends['stress'] = calculate_trend(stresses)
    
    return trends


def calculate_trend(values: List[float]) -> str:
    """
    Calculate if values are improving, declining, or stable.
    
    Args:
        values: List of numeric values in chronological order
    
    Returns:
        'improving', 'declining', or 'stable'
    """
    if len(values) < 3:
        return 'insufficient_data'
    
    # Compare first half vs second half
    mid = len(values) // 2
    first_half_avg = sum(values[:mid]) / mid
    second_half_avg = sum(values[mid:]) / (len(values) - mid)
    
    difference = second_half_avg - first_half_avg
    
    if difference >= 0.5:
        return 'improving'
    elif difference <= -0.5:
        return 'declining'
    else:
        return 'stable'


def calculate_confidence(entries: List[dict]) -> float:
    """
    Calculate confidence score based on data completeness.
    
    Args:
        entries: List of entries
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not entries:
        return 0.0
    
    # Factors affecting confidence
    num_entries = len(entries)
    completed_entries = sum(1 for e in entries if e.get('completed_at'))
    has_notes = sum(1 for e in entries if e.get('user_notes') or e.get('conditional_answer'))
    has_tags = sum(1 for e in entries if e.get('tags'))
    
    # Calculate score (0-1)
    completeness = completed_entries / max(num_entries, 1)
    notes_ratio = has_notes / max(num_entries, 1)
    tags_ratio = has_tags / max(num_entries, 1)
    
    # Weighted average
    confidence = (
        completeness * 0.4 +  # 40% weight on completion
        notes_ratio * 0.3 +   # 30% weight on having notes
        tags_ratio * 0.3      # 30% weight on having tags
    )
    
    # Bonus for having enough data points
    if num_entries >= 7:
        confidence = min(confidence * 1.2, 1.0)
    
    return round(confidence, 2)


def get_top_tags_by_category(
    tag_frequency: Dict[str, int],
    category: str
) -> List[str]:
    """
    FIXED Issue #6: Get top tags from a specific category using centralized categories.
    
    Args:
        tag_frequency: Dictionary of tag counts
        category: Category key from TAG_CATEGORIES
    
    Returns:
        List of top tags in that category
    """
    relevant_tags = TAG_CATEGORIES.get(category, [])
    
    # Filter and sort
    filtered = {tag: count for tag, count in tag_frequency.items() if tag in relevant_tags}
    sorted_tags = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    
    return [tag for tag, count in sorted_tags[:3]]  # Top 3


def format_correlation_for_user(correlation: Dict) -> str:
    """
    Format correlation finding for user-friendly display.
    
    Args:
        correlation: Correlation dictionary
    
    Returns:
        Human-readable string
    """
    trigger = correlation['trigger'].replace('_', ' ').title()
    impact = correlation['impact'].replace('_', ' ')
    effect = correlation['effect']
    
    direction = "improves" if effect > 0 else "worsens"
    
    return f"{trigger} {direction} your {impact} by {abs(effect):.1f} points"


def get_pattern_summary(patterns: Dict) -> str:
    """
    Generate a brief text summary of patterns.
    
    Args:
        patterns: Pattern analysis dictionary
    
    Returns:
        Summary string
    """
    if not patterns or patterns.get('confidence', 0) < 0.3:
        return "Not enough data for pattern analysis yet. Keep tracking!"
    
    summary_parts = []
    
    # Top stressor
    if patterns.get('top_stressors'):
        top_stress = patterns['top_stressors'][0].replace('_', ' ')
        summary_parts.append(f"Your main stressor is {top_stress}")
    
    # Trends
    trends = patterns.get('trends', {})
    if trends.get('mood') == 'improving':
        summary_parts.append("your mood is improving")
    elif trends.get('mood') == 'declining':
        summary_parts.append("your mood has declined")
    
    # Correlations
    correlations = patterns.get('correlations', [])
    if correlations:
        top_corr = correlations[0]
        summary_parts.append(format_correlation_for_user(top_corr))
    
    return ". ".join(summary_parts) + "."
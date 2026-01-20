import logging
import asyncio
from datetime import date, timedelta
from typing import Optional, List
from database.supabase_db import get_supabase 

logger = logging.getLogger(__name__)


async def create_weekly_summary(telegram_id: int, summary_data: dict) -> Optional[dict]:
    """Create a new weekly summary."""
    client = get_supabase()
    try:
        response = await asyncio.to_thread(
            lambda: client.table("weekly_summaries")
            .insert({"telegram_id": telegram_id, **summary_data})
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error creating weekly summary: {e}")
        return None


async def get_weekly_summary(
    telegram_id: int, 
    week_start: date
) -> Optional[dict]:
    """Get weekly summary for a specific week."""
    client = get_supabase()
    try:
        response = await asyncio.to_thread(
            lambda: client.table("weekly_summaries")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("week_start_date", week_start.isoformat())
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching weekly summary: {e}")
        return None


async def get_user_summaries(
    telegram_id: int,
    limit: int = 10
) -> List[dict]:
    """Get recent weekly summaries for a user."""
    client = get_supabase()
    try:
        response = await asyncio.to_thread(
            lambda: client.table("weekly_summaries")
            .select("*")
            .eq("telegram_id", telegram_id)
            .order("week_start_date", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching user summaries: {e}")
        return []


async def calculate_weekly_stats(
    telegram_id: int,
    week_start: date
) -> dict:
    """Calculate statistics for a week."""
    client = get_supabase()
    try:
        week_end = week_start + timedelta(days=7)
        
        response = await asyncio.to_thread(
            lambda: client.table("entries")
            .select("*")
            .eq("telegram_id", telegram_id)
            .gte("entry_date", week_start.isoformat())
            .lt("entry_date", week_end.isoformat())
            .execute()
        )
        
        if not response.data:
            return {
                "total_checkins": 0,
                "completed_days": 0,
                "morning_count": 0,
                "day_count": 0,
                "evening_count": 0,
                "avg_mood": None,
                "avg_energy": None,
                "avg_stress": None,
                "avg_sleep_quality": None,
            }
        
        entries = response.data
        morning_count = sum(1 for e in entries if e['entry_type'] == 'morning' and e.get('completed_at'))
        day_count = sum(1 for e in entries if e['entry_type'] == 'day' and e.get('completed_at'))
        evening_count = sum(1 for e in entries if e['entry_type'] == 'evening' and e.get('completed_at'))
        
        days_dict = {}
        for entry in entries:
            if entry.get('completed_at'):
                entry_date = entry['entry_date']
                if entry_date not in days_dict:
                    days_dict[entry_date] = set()
                days_dict[entry_date].add(entry['entry_type'])
        
        completed_days = sum(1 for types in days_dict.values() if len(types) == 3)
        
        mood_values = [e['mood'] for e in entries if e.get('mood') is not None]
        energy_values = [e['energy'] for e in entries if e.get('energy') is not None]
        stress_values = [e['stress'] for e in entries if e.get('stress') is not None]
        sleep_values = [e['sleep_quality'] for e in entries if e.get('sleep_quality') is not None]
        
        return {
            "total_checkins": morning_count + day_count + evening_count,
            "completed_days": completed_days,
            "morning_count": morning_count,
            "day_count": day_count,
            "evening_count": evening_count,
            "avg_mood": round(sum(mood_values) / len(mood_values), 2) if mood_values else None,
            "avg_energy": round(sum(energy_values) / len(energy_values), 2) if energy_values else None,
            "avg_stress": round(sum(stress_values) / len(stress_values), 2) if stress_values else None,
            "avg_sleep_quality": round(sum(sleep_values) / len(sleep_values), 2) if sleep_values else None,
        }
    except Exception as e:
        logger.error(f"Error calculating weekly stats: {e}")
        return {}


async def upsert_weekly_summary(
    telegram_id: int,
    week_start: date,
    summary_data: dict
) -> Optional[dict]:
    """Create or update weekly summary."""
    client = get_supabase()
    try:
        existing = await get_weekly_summary(telegram_id, week_start)
        
        if existing:
            response = await asyncio.to_thread(
                lambda: client.table("weekly_summaries")
                .update(summary_data)
                .eq("id", existing['id'])
                .execute()
            )
        else:
            week_end = week_start + timedelta(days=6)
            full_data = {
                "telegram_id": telegram_id,
                "week_start_date": week_start.isoformat(),
                "week_end_date": week_end.isoformat(),
                **summary_data
            }
            response = await asyncio.to_thread(
                lambda: client.table("weekly_summaries")
                .insert(full_data)
                .execute()
            )
        
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error upserting weekly summary: {e}")
        return None
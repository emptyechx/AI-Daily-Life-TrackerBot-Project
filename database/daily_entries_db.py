import logging
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional, List
from database.supabase_db import get_supabase

logger = logging.getLogger(__name__)

# ============ MAIN ENTRIES (UPSERT PATTERN) ============

async def upsert_entry(
    telegram_id: int,
    entry_date: date,
    entry_type: str,
    data: dict
) -> Optional[dict]:

    try:
        existing = await get_entry_by_date_type(telegram_id, entry_date, entry_type)

        if existing:
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries").update(data).eq("id", existing['id']).execute()
            )
        else:
            entry_data = {
                "telegram_id": telegram_id,
                "entry_date": entry_date.isoformat(),
                "entry_type": entry_type,
                **data
            }
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries").insert(entry_data).execute()
            )

        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error upserting entry: {e}")
        return None

async def get_entry_by_date_type(
    telegram_id: int,
    entry_date: date,
    entry_type: str
) -> Optional[dict]:
    try:
        response = await asyncio.to_thread(
            lambda: get_supabase().table("entries")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("entry_date", entry_date.isoformat())
            .eq("entry_type", entry_type)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching entry: {e}")
        return None

async def get_entry_by_id(entry_id: int) -> Optional[dict]:
    try:
        response = await asyncio.to_thread(
            lambda: get_supabase().table("entries").select("*").eq("id", entry_id).execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching entry {entry_id}: {e}")
        return None

async def mark_entry_completed(entry_id: int) -> bool:
    try:
        response = await asyncio.to_thread(
            lambda: get_supabase().table("entries").update({
                "completed_at": datetime.now().isoformat()
            }).eq("id", entry_id).execute()
        )
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error marking entry complete: {e}")
        return False

# ============ PREVIOUS ENTRY COMPARISON ============

async def get_previous_entry(
    telegram_id: int,
    entry_type: str,
    current_date: date
) -> Optional[dict]:
    try:
        if entry_type == 'day':
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries")
                .select("mood, energy, stress, sleep_quality")
                .eq("telegram_id", telegram_id)
                .eq("entry_date", current_date.isoformat())
                .eq("entry_type", "morning")
                .execute()
            )
        elif entry_type == 'evening':
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries")
                .select("mood, energy, stress, sleep_quality")
                .eq("telegram_id", telegram_id)
                .eq("entry_date", current_date.isoformat())
                .eq("entry_type", "day")
                .execute()
            )
        else:
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries")
                .select("mood, energy, stress, sleep_quality")
                .eq("telegram_id", telegram_id)
                .lt("entry_date", current_date.isoformat())
                .eq("entry_type", "evening")
                .order("entry_date", desc=True)
                .limit(1)
                .execute()
            )

        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error fetching previous entry: {e}")
        return None

def should_ask_conditional(
    current_ratings: dict,
    previous_ratings: Optional[dict],
    entry_type: str
) -> tuple[bool, str]:
    mood = current_ratings.get('mood', 0)
    energy = current_ratings.get('energy', 0)
    stress = current_ratings.get('stress', 0)
    sleep = current_ratings.get('sleep_quality', 0)

    if entry_type == 'morning' and mood == 5 and energy == 5 and sleep == 5:
        return (True, 'all_perfect')
    if entry_type in ['day', 'evening'] and mood == 5 and energy == 5 and stress == 1:
        return (True, 'all_perfect')

    if entry_type == 'morning' and sleep <= 2:
        return (True, 'sleep_low')
    if mood <= 2:
        return (True, 'mood_low')
    if energy <= 2:
        return (True, 'energy_low')
    if stress >= 4:
        return (True, 'stress_high')

    if previous_ratings:
        # previous_ratings may contain explicit None values; use 3 as neutral default
        prev_mood = previous_ratings.get('mood') if previous_ratings.get('mood') is not None else 3
        prev_energy = previous_ratings.get('energy') if previous_ratings.get('energy') is not None else 3
        prev_stress = previous_ratings.get('stress') if previous_ratings.get('stress') is not None else 3

        try:
            if mood - prev_mood <= -2:
                return (True, 'mood_drop')
            if energy - prev_energy <= -2:
                return (True, 'energy_drop')
            if stress - prev_stress >= 2:
                return (True, 'stress_spike')
        except TypeError:
            # In case previous values are of unexpected type, skip conditional
            logger.warning('Unexpected previous_ratings types when checking conditionals')

    return (False, '')
# ============ WEEKLY REPORT ============

async def count_full_days_this_week(telegram_id: int) -> int:
    """Count days with all 3 completed entries this week"""
    try:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        response = await asyncio.to_thread(
            lambda: get_supabase().table("entries")
            .select("entry_date, entry_type")
            .eq("telegram_id", telegram_id)
            .gte("entry_date", week_start.isoformat())
            .lt("entry_date", today.isoformat())
            .not_.is_("completed_at", "null")
            .execute()
        )

        if not response.data:
            return 0

        days_dict = {}
        for entry in response.data:
            entry_date = entry['entry_date']
            if entry_date not in days_dict:
                days_dict[entry_date] = set()
            days_dict[entry_date].add(entry['entry_type'])

        # Count days with all 3 entry types
        full_days = sum(1 for types in days_dict.values() if len(types) == 3)
        return full_days
    except Exception as e:
        logger.error(f"Error counting full days: {e}")
        return 0

async def get_weekly_entries(telegram_id: int, week_start: date) -> List[dict]:
    """Get all entries for a week"""
    try:
        week_end = week_start + timedelta(days=7)
        response = await asyncio.to_thread(
            lambda: get_supabase().table("entries")
            .select("*")
            .eq("telegram_id", telegram_id)
            .gte("entry_date", week_start.isoformat())
            .lt("entry_date", week_end.isoformat())
            .order("entry_date")
            .order("created_at")
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error fetching weekly entries: {e}")
        return []

# ============ REMINDERS ============

async def increment_reminder_count(entry_id: int) -> bool:
    """Increment reminder count"""
    try:
        entry = await get_entry_by_id(entry_id)
        if entry:
            new_count = entry.get('reminder_count', 0) + 1
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries").update({
                    'reminder_count': new_count
                }).eq("id", entry_id).execute()
            )
            return bool(response.data)
        return False
    except Exception as e:
        logger.error(f"Error incrementing reminder count: {e}")
        return False

async def increment_remind_later_count(entry_id: int) -> bool:
    """Increment 'remind me later' count"""
    try:
        entry = await get_entry_by_id(entry_id)
        if entry:
            new_count = entry.get('remind_later_count', 0) + 1
            response = await asyncio.to_thread(
                lambda: get_supabase().table("entries").update({
                    'remind_later_count': new_count
                }).eq("id", entry_id).execute()
            )
            return bool(response.data)
        return False
    except Exception as e:
        logger.error(f"Error incrementing remind_later count: {e}")
        return False
from aiogram.fsm.state import StatesGroup, State
class Registration(StatesGroup):
    
    gender = State()
    age = State()
    height = State()
    weight = State()
    activity_level = State()
    bedtime_usual = State()
    wakeuptime_usual = State()
    timezone = State()
    timezone_manual = State()
    habit_tracking = State()
    notification_setup = State()
    review_profile = State()


class MorningCheckin(StatesGroup):
    
    sleep_quality = State()
    mood = State()
    energy = State()
    wakeup_time = State()
    actual_wakeup_time = State()
    conditional_answer = State()
    notes = State()


class DayCheckin(StatesGroup):
    
    mood = State()
    energy = State()
    stress = State()
    conditional_answer = State()
    notes = State()


class EveningCheckin(StatesGroup):
    
    satisfaction = State()
    mood = State()
    stress = State()
    conditional_answer = State()
    reflection = State()
    notes = State()
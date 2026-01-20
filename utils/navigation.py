from typing import Callable, Union

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State

from utils.constants import BTN_BACK, MSG_USE_BUTTONS

async def handle_back_navigation(message: types.Message, state: FSMContext, previous_state: State, prompt_text: str, keyboard_func: Callable) -> bool:
    """Returns to previous state if "Back" button pressed"""
    if message.text == BTN_BACK:
        await state.set_state(previous_state)
        await message.answer(prompt_text, reply_markup=keyboard_func())
        return True
    return False


async def validate_button_choice( message: types.Message, valid_options: list[str], error_message: str = None) -> Union[str, None]:
    """Ensures user selected a valid button option only."""
    if message.text not in valid_options:
        await message.answer(error_message or MSG_USE_BUTTONS)
        return None
    return message.text
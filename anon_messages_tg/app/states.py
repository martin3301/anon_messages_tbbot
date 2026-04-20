from aiogram.fsm.state import StatesGroup, State

class AnonStates(StatesGroup):
    in_choose = State()
    only_text = State()
    with_media = State()
    anon_c_room = State()
    anon_c_room2 = State()

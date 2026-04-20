import asyncio
import datetime

from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext

from app.functions import generate_full_name, generate_unique_code
from app.keyboard import chooses, to_main_menu
from app.states import AnonStates
from config import mainChannel, commGroup
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, \
    InputMediaVideo, BotCommand

from db.main import create_new_user, check_user, create_new_message, check_message, get_message_group_id, \
    get_and_create_new_random_name

router = Router()



async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
    ]
    await bot.set_my_commands(commands)


@router.message(F.chat.type.in_(["group", "supergroup"]))
async def handle_group_message(message: Message):
    if message.forward_from_chat:
        await create_new_message(message.forward_from_message_id, message.message_id)


async def show_main_menu(message: Message, state: FSMContext):
    await state.set_state(AnonStates.in_choose)

    if await check_user(message.from_user.id):
        await message.answer(
            "Рады видеть вас снова.\nВы можете выбрать что отправить.",
            reply_markup=chooses
        )
    else:
        await create_new_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                              message.from_user.username)
        await message.answer(
            "Выберите что отправить.",
            reply_markup=chooses
        )


@router.message(F.chat.type == "private", CommandStart())
async def start(message: Message, state: FSMContext, bot: Bot):
    await show_main_menu(message, state)
    await get_and_create_new_random_name(message.from_user.id)


@router.message(AnonStates.in_choose)
async def gone_menu(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@router.callback_query(F.data == 'only_text')
async def only_text(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AnonStates.only_text)
    await callback.message.edit_text('Задавйте вопрос.', reply_markup=to_main_menu)


@router.callback_query(F.data == 'not_only_text')
async def with_media(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AnonStates.with_media)
    await state.update_data(media=[], caption="")
    await callback.message.edit_text(
        'Инструкция:\nСначала отправьте фото или видео (не более 10 файлов).\nПосле этого отправьте текст сообщения.\nВ тексте обязательно укажите тег "#end" — в начале или в конце сообщения.',
        reply_markup=to_main_menu)


@router.callback_query(F.data == 'anon_comm')
async def comments_room(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AnonStates.anon_c_room)
    await callback.message.edit_text('Сначало отправьте айди сообщение из канала', reply_markup=to_main_menu)


@router.callback_query(F.data == 'to_menu')
async def send_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_main_menu(callback.message, state)

    text = "Сообщение удаляется..."

    for i in range(len(text), 0, -2):
        await callback.message.edit_text(text[:i])
        await asyncio.sleep(0.08)

    await callback.message.delete()


@router.message(AnonStates.only_text)
async def st_message(message: Message, bot: Bot, state: FSMContext):
    random_name = await generate_full_name()
    sent_m = await bot.send_message(chat_id=mainChannel,
                                    text=f"<blockquote>Анонимный субъект - {random_name}</blockquote>\n\n<blockquote>{message.text}</blockquote>",
                                    parse_mode="HTML")
    await bot.edit_message_text(chat_id=mainChannel, message_id=sent_m.message_id,
                                text=f"<blockquote>Анонимный субъект - {random_name}</blockquote>\n\n<blockquote>{message.text}</blockquote>\nid: <code>{sent_m.message_id}</code>",
                                parse_mode="HTML")
    await message.answer('Отправлено!', reply_markup=to_main_menu)
    await state.set_state(AnonStates.in_choose)


@router.message(AnonStates.with_media)
async def collect_media(message: Message, state: FSMContext):
    random_name = await generate_full_name()
    data = await state.get_data()
    media = data.get("media", [])

    # 📥 Сбор медиа
    if message.photo:
        media.append(("photo", message.photo[-1].file_id))
        await state.update_data(media=media)
        await message.answer("Фото добавлено")
        return

    if message.video:
        media.append(("video", message.video.file_id))
        await state.update_data(media=media)
        await message.answer("Видео добавлено")
        return

    if message.document:
        await message.answer("Пж не отправлять доки")
        return

    # 📤 Завершение
    if message.text and "#end" in message.text:
        mss = message.text.replace("#end", "").strip()

        if not media:
            await message.answer("Вы ничего не отправили")
            return

        media_group = []

        # 📦 Формируем альбом для основного канала
        for i, (type_, file_id) in enumerate(media):
            caption = (
                f"<blockquote>Анонимный субъект - {random_name}</blockquote>\n\n"
                f"<blockquote>{mss}</blockquote>"
                if i == 0 else None
            )

            if type_ == "photo":
                media_group.append(InputMediaPhoto(media=file_id, caption=caption, parse_mode="HTML"))
            elif type_ == "video":
                media_group.append(InputMediaVideo(media=file_id, caption=caption, parse_mode="HTML"))


        sent_m = await message.bot.send_media_group(
            chat_id=mainChannel,
            media=media_group
        )

        await message.bot.edit_message_caption(
            chat_id=mainChannel,
            message_id=sent_m[0].message_id,
            caption=(
                f"<blockquote>Анонимный субъект - {random_name}</blockquote>\n\n"
                f"<blockquote>{mss}</blockquote>\n"
                f"id: <code>{sent_m[0].message_id}</code>"
            ),
            parse_mode="HTML"
        )

        # 🔄 Сброс состояния
        await state.clear()
        await state.set_state(AnonStates.in_choose)

        await message.answer("Пост отправлен", reply_markup=to_main_menu)


@router.message(AnonStates.anon_c_room)
async def send_anon_c_room_id(message: Message, state: FSMContext):
    idi = message.text
    if idi.isdigit():
        if await check_message(int(idi)):
            await message.answer(text='Отправьте комменты', reply_markup=to_main_menu)
            mesgid = await get_message_group_id(int(idi))
            await state.update_data(anon_c_room=[int(mesgid), int(idi)])
            await state.set_state(AnonStates.anon_c_room2)
        else:
            await message.answer(text='Такого сообщение не существует')
    elif idi == '#end':
        await message.answer(text='Ладно', reply_markup=to_main_menu)
        await state.set_state(AnonStates.in_choose)
        return
    else:
        await message.answer(text='Пожалуйста введите айди')


@router.message(AnonStates.anon_c_room2)
async def send_anon_c_room(message: Message, state: FSMContext, bot: Bot):
    uc = await generate_unique_code()
    data = await state.get_data()
    rn = await get_and_create_new_random_name(message.from_user.id)
    if message.text == '#end':
        await message.answer(text='Отправлено!', reply_markup=to_main_menu)
        await state.set_state(AnonStates.in_choose)
        return
    reply_id = data['anon_c_room']
    print(reply_id)
    if message.text:
        await bot.send_message(
            chat_id=commGroup,
            text=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.text}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    elif message.photo:
        await bot.send_photo(
            chat_id=commGroup,
            photo=message.photo[-1].file_id,
            caption=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.caption or ''}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    elif message.video:
        await bot.send_video(
            chat_id=commGroup,
            video=message.video.file_id,
            caption=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.caption or ''}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    elif message.audio:
        await bot.send_audio(
            chat_id=commGroup,
            audio=message.audio.file_id,
            caption=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.caption or ''}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    elif message.voice:
        await bot.send_voice(
            chat_id=commGroup,
            voice=message.voice.file_id,
            caption=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.caption or ''}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    elif message.document:
        await bot.send_document(
            chat_id=commGroup,
            document=message.document.file_id,
            caption=f"<blockquote>{rn} - {uc}</blockquote>\n<blockquote>{message.caption or ''}</blockquote>",
            reply_to_message_id=reply_id[0],
            parse_mode="HTML"
        )
    else:
        await message.answer("Тип сообщения не поддерживается")

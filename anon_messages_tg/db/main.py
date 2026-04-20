import time

import aiosqlite
from aiosqlite import cursor

from app.functions import get_current_period, generate_full_name

DB_NAME = "database.db"


async def init_db():
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    await cursor.execute("""
                         CREATE TABLE IF NOT EXISTS users
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY,
                             user_id
                             INTEGER,
                             user_first_name
                             TEXT,
                             user_last_name
                             TEXT,
                             username
                             TEXT,
                             random_name
                             TEXT,
                             n_period
                             TEXT
                         )

                         """)
    await cursor.execute("""
                         CREATE TABLE IF NOT EXISTS messages
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY,
                             message_id
                             INTEGER,
                             message_id_in_group
                             INTEGER
                         )
                         """)

    await conn.commit()
    await conn.close()


async def create_new_user(user_id, user_first_name, user_last_name, username):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    try:
        await cursor.execute("INSERT INTO users (user_id, user_first_name, user_last_name, username) VALUES (?,?,?,?)",
                             (user_id, user_first_name, user_last_name, username))
        await conn.commit()
    finally:
        await conn.close()
    return user_id


async def check_user(userid):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    await cursor.execute("SELECT * FROM users WHERE user_id = ?", (int(userid),))
    user = await cursor.fetchone()
    await conn.close()
    if user:
        return True
    return False


async def create_new_message(message_id, message_id_in_group):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    try:
        await cursor.execute("INSERT INTO messages (message_id, message_id_in_group) VALUES (?,?)",
                             (message_id, message_id_in_group))
        await conn.commit()
    finally:
        await conn.close()
    return message_id


async def check_message(messageid):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    await cursor.execute("SELECT * FROM messages WHERE message_id = ?", (int(messageid),))
    message = await cursor.fetchone()
    await conn.close()
    if message:
        return True
    return False


async def get_message_group_id(messageid):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    await cursor.execute("SELECT message_id_in_group FROM messages WHERE message_id = ?", (int(messageid),))
    mesgid = await cursor.fetchone()
    await conn.close()
    if mesgid:
        return mesgid[0]
    return False


async def get_and_create_new_random_name(userid):
    conn = await aiosqlite.connect(DB_NAME)
    cursor = await conn.cursor()
    await cursor.execute(
        "SELECT n_period, random_name FROM users WHERE user_id = ?",
        (int(userid),)
    )
    row = await cursor.fetchone()
    c_period = await get_current_period()
    if not row:
        random_name = await generate_full_name()

        await cursor.execute("""
                             INSERT INTO users (user_id, n_period, random_name)
                             VALUES (?, ?, ?)
                             """, (int(userid), c_period, random_name))
        await conn.commit()
        await conn.close()
        return random_name
    n_period, random_name = row
    if not n_period or n_period != c_period:
        new_name = await generate_full_name()
        await cursor.execute("""
                             UPDATE users
                             SET n_period    = ?,
                                 random_name = ?
                             WHERE user_id = ?
                             """, (c_period, new_name, int(userid)))
        await conn.commit()
        await conn.close()
        return new_name
    await conn.close()
    return random_name

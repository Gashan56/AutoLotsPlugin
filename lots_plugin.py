from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cardinal import Cardinal
import FunPayAPI
from FunPayAPI.account import Account
from FunPayAPI import types
from tg_bot import CBT
import telebot
import time
import tg_bot.static_keyboards
from telebot.types import InlineKeyboardMarkup as K, InlineKeyboardButton as B
from logging import getLogger
import colorama
from colorama import Fore, Back, Style
colorama.init(autoreset=True)

NAME = "LotPlugin"
VERSION = "0.0.2"
DESCRIPTION = "Плагин для выполнения действий над лотами через тг-бота"
CREDITS = "@gashan_official"
UUID = "d6250637-8054-40c6-9eba-86d31c32a800"
SETTINGS_PAGE = False

LOGGER_PREFIX = "[LOTS_PLG]"

logger = getLogger("FPC.4eef")
print(f"{Style.RESET_ALL}{Fore.RED}{Style.BRIGHT}  0100010     011010     1001001  0001  0000     00110    00001  100\n"
      " 11110101     001100    01011     1100  0101    111000    111111 001\n"
      "0001         011 0111   11000     0111101011   101  000   1000101000\n"
      "1101   110   110 00010    101000  1100110101   011  001   1001111000\n"
      "0010000011  0111110100     00101  0001  0000  0010111010  0011 00101\n"
      " 001010101 0111   0111  0000011   0000  0111  001    100  1110  1001\n\n"
      "   1001011   0111    1111   0010   10101100  00011100  1011  0110\n"
      "   110  000  0100    1010   0011  11011110     1000    11001 0001\n"
      "   010  101  0111    1011   1101 0111          1111    1110110100\n"
      "   0000111   1111    1101   0110 0101   000    0010    1001110000\n"
      "   010       1101101 00011 00100 1101010001    0010    1101 11000\n"
      f"   001       0100111  001011110   100011111  11001101  1100  1000{Fore.RESET}{Back.RESET}{Style.RESET_ALL}\n")


CBT_lots_things = "lots"
CBT_EDITT_LOT = "CBT_EDITT_LOT"
CBT_EDIT_CATEGORY = "CBT_EDIT_CATEGORY"
CBT_DELETE_LOTS = "CBT_DELETE_LOTS"

def init_commands(cardinal: Cardinal):
    if not cardinal.telegram:
        return
    tg = cardinal.telegram
    bot = tg.bot
    
    original_settings_sections = tg_bot.static_keyboards.SETTINGS_SECTIONS
    
    def modified_settings_sections() -> K:
        original_kb = original_settings_sections()
        
        new_kb = K()
        
        for row in original_kb.keyboard[:-3]:
            new_kb.row(*row)
        
        new_kb.row(B("🛠 Действия над лотами", callback_data=f"{UUID}:lots"))
        
        for row in original_kb.keyboard[-3:]:
            new_kb.row(*row)
        
        return new_kb
    def create_categories_keyboard(cardinal: Cardinal, action):
        """
        Создает клавиатуру с категориями в два столбика
        """
        sorted_lots = types.UserProfile.get_sorted_lots(mode=2, self=cardinal.account.get_user(cardinal.account.id))

        keyboard = K(row_width=2)
        categories = []
        for subcategory, lots in sorted_lots.items():
            if lots:
                categories.append((subcategory.fullname, subcategory.id))

        for i in range(0, len(categories), 2):
            row = []
            if i < len(categories):
                row.append(B(
                    text=categories[i][0],  # Полное имя
                    callback_data=f"{CBT_EDIT_CATEGORY}:{action}:{categories[i][1]}"  # ID подкатегории
                ))
            if i + 1 < len(categories):
                row.append(B(
                    text=categories[i + 1][0],
                    callback_data=f"{CBT_EDIT_CATEGORY}:{action}:{categories[i + 1][1]}"
                ))

            if row:
                keyboard.add(*row)

        keyboard.add(B(
            text="⬅️ Назад",
            callback_data=f"{UUID}:lots"
        ))

        return keyboard
    tg_bot.static_keyboards.SETTINGS_SECTIONS = modified_settings_sections
    def lots_page(call: telebot.types.CallbackQuery):
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        keyboard = K()

        keyboard.row(B("🟢 Активировать категорию", callback_data=f"{CBT_EDITT_LOT}:activate"), B("🔴 Удалить категорию", callback_data=f"{CBT_EDITT_LOT}:delete"))
        keyboard.row(B("🔴 Деактивировать категорию", callback_data=f"{CBT_EDITT_LOT}:deactivate"), B("🗑 Удалить все лоты", callback_data=f"{CBT_DELETE_LOTS}"))

        keyboard.add(B("◀️ Назад", callback_data=f"{CBT.MAIN}"))

        bot.edit_message_text(
            f"⚙ Здесь ты можешь поменять статусы лотов (деактивировать/активировать)", call.message.chat.id, call.message.id, reply_markup=keyboard,
            parse_mode="HTML")

        bot.answer_callback_query(call.id)
    def edit_lot_page(call: telebot.types.CallbackQuery):
        action = call.data.split(':')[1]
        keyboard = K()
        if action == "activate":
            text = "Введите id категории"
            keyboard.add(B(
            text="⬅️ Назад",
            callback_data=f"{UUID}:lots"
        ))
        else:
            text = "Выбери категорию лотов для выполнения действия или введите id"
            keyboard = create_categories_keyboard(cardinal, action)
        msg = bot.edit_message_text(
            text, call.message.chat.id,
            call.message.id, reply_markup=keyboard,
            parse_mode="HTML")
        bot.register_next_step_handler(msg, edit_category_by_text, call.message.id, action)
    def edit_category_by_text(message, original_id, action):
        subcategory = message.text
        my_lots = cardinal.account.get_my_subcategory_lots(int(subcategory))
        msg = bot.edit_message_text("✅ Выполняю...", message.chat.id, original_id)
        # bot.delete_message(message.chat.id, message.id)
        activated = 0
        deactivated = 0
        deleted = 0
        for lot in my_lots:
            id = lot.id
            field = cardinal.account.get_lot_fields(id)
            if action == "activate":
                if field.active == True:
                    continue
                else:
                    field.active = True
                    activated += 1
                cardinal.account.save_lot(field)
            elif action == "deactivate":
                if field.active == False:
                    continue
                else:
                    field.active = False
                    deactivated += 1
                cardinal.account.save_lot(field)
            elif action == "delete":
                cardinal.account.delete_lot(id)
            logger.info(f"{LOGGER_PREFIX} Изменил инфу у лота {id}")
            time.sleep(1)
        result_msg = (
            f"<b>✅ Успешно обработано {len(my_lots)} лотов!</b>\n\n"
            f"🟢 <b>Активировано:</b> <i>{activated}</i>\n"
            f"🔴 <b>Деактивировано:</b> <i>{deactivated}</i>\n"
            f"🗑 <b>Удалено:</b> <i>{deleted}</i>"
            f"\n❤ Мне будет приятно, если вы напишите свой <a href='https://t.me/cardinal_PIugins/28'>отзыв в тг</a> или поставите звезду на <a href='https://github.com/Gashan56/AutoLotsPlugin'>гитхаб</a>)"
        )
        keyboard = K()
        keyboard.add(B(
            text="⬅️ Назад",
            callback_data=f"{UUID}:lots"
        ))

        bot.edit_message_text(result_msg, message.chat.id, msg.id, reply_markup=keyboard, parse_mode="HTML")
        return
    def handle_category_action(call: telebot.types.CallbackQuery):
        try:
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            _, action, subcategory = call.data.split(':')
        
            class FakeMessage:
                def __init__(self):
                    self.text = subcategory
                    self.chat = type('Chat', (), {'id': call.message.chat.id})
                    self.id = call.message.message_id
                
            edit_category_by_text(
                message=FakeMessage(),
                original_id=call.message.message_id,
                action=action
            )
        
        except Exception as e:
            logger.error(f"Error: {e}")
    def delete_lots(call: telebot.types.CallbackQuery):
        deleted = 0
        lots = types.UserProfile.get_sorted_lots(mode=1, self=cardinal.account.get_user(cardinal.account.id))
        for id in lots:
            cardinal.account.delete_lot(id)
            deleted += 1
            time.sleep(1)
        result_msg = (
            f"<b>✅ Успешно обработано {len(lots)} лотов!</b>\n\n"
            f"🗑 <b>Удалено:</b> <i>{deleted}</i>"
        )
        keyboard = K()
        keyboard.add(B(
            text="⬅️ Назад",
            callback_data=f"{UUID}:lots"
        ))

        bot.edit_message_text(result_msg, call.message.chat.id, call.message.id, reply_markup=keyboard, parse_mode="HTML")
        return
        
    tg.cbq_handler(lots_page, lambda c: f"{UUID}:lots" in c.data)
    tg.cbq_handler(edit_lot_page, lambda c: f"{CBT_EDITT_LOT}" in c.data)
    tg.cbq_handler(handle_category_action, lambda c: f"{CBT_EDIT_CATEGORY}" in c.data)
    tg.cbq_handler(delete_lots, lambda c: f"{CBT_DELETE_LOTS}" in c.data)
BIND_TO_PRE_INIT = [init_commands]

BIND_TO_DELETE = []

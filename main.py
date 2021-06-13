import asyncio
from pycoingecko import CoinGeckoAPI
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import TOKEN
import app.keyboard as kb
import logging
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import app.currency as cc
import sqlite3
from aiogram.utils.exceptions import Throttled
from aiogram.types import BotCommand

# инициализация CoinGeckoAPI
cg = CoinGeckoAPI()

# включаем логирование
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger.error("Starting bot")

# инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# функция антифлуда
async def anti_flood(*args, **kwargs):
    m = args[0]
    await m.answer("[Антифлуд] Попробуйте через 3 секунды!")

# функция проверки на число
async def is_number(strout):
    try:
        float(strout)
        return True
    except ValueError:
        return False

# регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/help", description="Информация о боте"),
        BotCommand(command="/cancel", description="Отменить действие")
    ]
    await bot.set_my_commands(commands)

# класс для машины состояний
class CurrencyFixed(StatesGroup):
    waiting_selected_pair_currency = State()
    waiting_get_current_currency_rate = State()
    waiting_enter_min_currency = State()
    waiting_enter_max_currency = State()

# обработка команды start
@dp.message_handler(commands=['start'])
@dp.throttled(anti_flood, rate=3)
async def process_start_command(message: types.Message):
    await set_commands(bot)
    await message.answer('Вас приветствует криптобот от сайта vsepartnerki.com\nВыберите необходимое действие из меню ниже', reply_markup=kb.start_kb, disable_web_page_preview=True)

# функция парсинга
async def parser(cryptoname, fiatname):
    price_value = cg.get_price(ids=cryptoname, vs_currencies=fiatname)
    return price_value[cryptoname][fiatname]

# обработка курса крипты (колбэки crypto_btn)
@dp.callback_query_handler(text="crypto_btn")
@dp.throttled(anti_flood, rate=3)
async def process_crypto_get_price(call: types.CallbackQuery):
    await call.message.answer('🕓 Сбор данных, ожидайте несколько секунд...')
    output_text = ''
    for i in cc.CURRENCY:
        parser_item = await parser(cc.CURRENCY[i], 'usd')
        output_text += f'📈 1 {cc.CURRENCY[i]} = {parser_item} USD\n'
    await call.message.answer('Текущий курс криптовалют\n\n' + output_text + '\nЛучшая биржа криптовалют - https://goo.su/5nXR\nНаш сайт - https://vsepartnerki.com', reply_markup=kb.start_kb, disable_web_page_preview=True)

# Состояние 1. Обработка колбэка fixed_btn
@dp.callback_query_handler(text="fixed_btn", state=None)
@dp.throttled(anti_flood, rate=3)
async def process_fixed_btn(call: types.CallbackQuery):
    await call.message.answer('Шаг 1. Какую связку криптовалюты вы хотите зафиксировать? Выберите из списка ниже', reply_markup=kb.fixed_crypto_kb)
    await CurrencyFixed.waiting_selected_pair_currency.set()

# Состояние 2. Получение текущего курса валют
@dp.callback_query_handler(text="btc_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.callback_query_handler(text="eth_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.callback_query_handler(text="doge_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.callback_query_handler(text="ada_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.callback_query_handler(text="xrp_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.callback_query_handler(text="ltc_usd", state=CurrencyFixed.waiting_selected_pair_currency)
@dp.throttled(anti_flood, rate=3)
async def procces_get_current_rate_currency(call: types.CallbackQuery, state: FSMContext):
    parser_item = await parser(cc.CURRENCY[call.data], 'usd')
    await state.update_data(current_currency_fixed=parser_item)
    min_value_currency = parser_item - parser_item * 1 / 100
    max_value_currency = parser_item + parser_item * 1 / 100
    await state.update_data(min_currency_fixed=min_value_currency)
    await state.update_data(max_currency_fixed=max_value_currency)
    await state.update_data(crypto_pair=call.data)
    save_data = await state.get_data()
    await call.message.answer(f"Шаг 2. Текущий курс {cc.CURRENCY[call.data]} составляет {save_data['current_currency_fixed']} USD. Введите и отправьте минимальный порог для фиксации (не менее 0 USD и не более {save_data['min_currency_fixed']} USD)", reply_markup=kb.cancel_kb)
    await CurrencyFixed.next()

# Состояние 3. Ввод минимального значения
@dp.message_handler(state=CurrencyFixed.waiting_get_current_currency_rate)
@dp.throttled(anti_flood, rate=3)
async def procces_waiting_min_currency(message: types.Message, state: FSMContext):
    if await is_number(message.text) == False:
        await message.answer('Ошибка! Введено не число!')
        return
    save_data = await state.get_data()
    if (float(message.text) >= save_data['min_currency_fixed'] or float(message.text) <= 0):
        await message.answer(f"Ошибка! Введенное число меньше 0 USD или больше {save_data['min_currency_fixed']} USD!")
        return
    await state.update_data(min_fixed=float(message.text))
    await message.answer(f"Шаг 3. Теперь введите и отправьте максимальный порог для фиксации (не менее {save_data['max_currency_fixed']} USD и не более 100000 USD)", reply_markup=kb.cancel_kb)
    await CurrencyFixed.next()

# Состояние 5. Ввод максимального значения
@dp.message_handler(state=CurrencyFixed.waiting_enter_min_currency)
@dp.throttled(anti_flood, rate=3)
async def procces_waiting_max_currency(message: types.Message, state: FSMContext):
    await state.update_data(max_fixed=float(message.text))
    if await is_number(message.text) == False:
        await message.answer('Ошибка! Введено не число!')
        return
    save_data = await state.get_data()
    if (float(message.text) >= 100000 or float(message.text) <= save_data['max_currency_fixed']):
        await message.answer(f"Ошибка! Введенное число меньше {save_data['max_currency_fixed']} USD или больше 100000 USD!")
        return
    await message.answer("Фиксация завершена! Как только курс выйдет за указанные вами пределы вы получите уведомление об этом!", reply_markup=kb.start_kb)

    async def insert_varible_into_table(userid, currency_pair, min_value, max_value, current_value):
        try:
            connection = sqlite3.connect('fixeddb.db')
            cursor = connection.cursor()
            print('Подключение к базе данных выполнено успешно!')
            cursor.execute("""CREATE TABLE IF NOT EXISTS fixed(
            id INTEGER NOT NULL PRIMARY KEY,
            userid INTEGER,
            currency_pair TEXT,
            min_value INTEGER,
            max_value INTEGER,
            current_value INTEGER);
            """)
            print('Таблица успешно создана!')
            sqlite_insert_with_param = """INSERT INTO fixed (userid, currency_pair, min_value, max_value, current_value) VALUES (?, ?, ?, ?, ?);"""
            data_tuple = (userid, currency_pair, min_value, max_value, current_value)
            cursor.execute(sqlite_insert_with_param, data_tuple)
            connection.commit()
            print('Данные в таблицу успешно добавлены!', cursor.rowcount)
            cursor.close()
        except sqlite3.Error as error:
            print("Ошибка подключения к базе данных!", error)
        finally:
            if connection:
                connection.close()
                print("Соединение с базой данных закрыто!")
    
    await insert_varible_into_table(message.from_user.id, save_data['crypto_pair'], save_data['min_fixed'], save_data['max_fixed'], save_data['current_currency_fixed'])
    await state.finish()

# обработка команды help
@dp.message_handler(commands=['help'])
@dp.throttled(anti_flood, rate=3)
async def process_help_command(message: types.Message):
    await message.answer("Пожалуйста, воспользуйтесь кнопками ниже!", reply_markup=kb.start_kb)

# обработка всех текстовых сообщений
@dp.message_handler()
@dp.throttled(anti_flood, rate=3)
async def echo_message(msg: types.Message):
    await bot.send_message(msg.from_user.id, 'Вас приветствует криптобот от сайта vsepartnerki.com\n\nДля запуска бота используйте команду /start. Для получения дополнительной информации отправьте команду /help\n\nЛучшая биржа криптовалют - https://goo.su/5nXR', reply_markup=kb.start_kb, disable_web_page_preview=True)

# сброс состояний
@dp.callback_query_handler(text="cancel", state="*")
@dp.throttled(anti_flood, rate=3)
async def procces_cmd_cancel(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.answer("Действие отменено", reply_markup=kb.start_kb)
@dp.message_handler(text="отмена", state="*")
@dp.message_handler(commands="cancel", state="*")
@dp.throttled(anti_flood, rate=3)
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено", reply_markup=kb.start_kb)

# функция отправки сообщения пользователю
async def gg(userid, usermsg):
    await bot.send_message(userid, usermsg)

# ассинхронная функция постоянного мониторинга курса
async def monitoring_currency_rate():
    while True:
        # подключаемся к базе данных
        try:
            connection = sqlite3.connect('fixeddb.db')
            cursor = connection.cursor()
            print('[Мониторинг] Подключение к базе данных выполнено успешно!')
            count_row = """SELECT * FROM fixed"""
            cursor.execute(count_row)
            records = cursor.fetchall()
            sql_select_id = """SELECT * FROM fixed"""
            cursor.execute(sql_select_id)
            get_records = cursor.fetchmany(len(records))
            if len(records) == 0:
                print('База данных пуста!')
            else:
                for row in get_records:
                    parser_item = await parser(cc.CURRENCY[row[2]], 'usd')
                    if float(parser_item) > float(row[4]):
                        await gg(row[1], f'📈 Внимание! Ваш зафиксированный курс ({cc.CURRENCY[row[2]]}) вырос!\n\n📌 Зафиксированный курс (минимум) - {row[3]} USD\n📌 Зафиксированный курс (максимум) - {row[4]} USD\n📈 Текущий курс - {parser_item} USD')
                        sql_select_query = """DELETE FROM fixed WHERE id = ?"""
                        cursor.execute(sql_select_query, (int(row[0]),))
                        connection.commit()
                        await gg(row[1], 'ℹ️ Ваша фиксация была удалена из базы данных и больше не отслеживается')
                    elif float(parser_item) < float(row[3]):
                        await gg(row[1], f'📉 Внимание! Ваш зафиксированный курс ({cc.CURRENCY[row[2]]}) упал!\n\n📌 Зафиксированный курс (минимум) - {row[3]} USD\n📌 Зафиксированный курс (максимум) - {row[4]} USD\n📈 Текущий курс - {parser_item} USD')
                        sql_select_query = """DELETE FROM fixed WHERE id = ?"""
                        cursor.execute(sql_select_query, (int(row[0]),))
                        connection.commit()
                        await gg(row[1], 'ℹ️ Ваша фиксация была удалена из базы данных и больше не отслеживается')
                    else:
                        print('[Мониторинг] Никаких изменений нет')
                        continue
            cursor.close()
        except sqlite3.Error as error:
            print("[Мониторинг] Ошибка подключения к базе данных!", error)
        finally:
            if connection:
                connection.close()
                print("[Мониторинг] Соединение с базой данных закрыто!")
        await asyncio.sleep(300)
async def on_startup(x):
    asyncio.create_task(monitoring_currency_rate())

# запускаем поллинг
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates = True, on_startup = on_startup)
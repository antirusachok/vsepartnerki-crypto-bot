from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# кнопка команды /start
start_fixed_btn = InlineKeyboardButton('📌 Зафиксировать', callback_data='fixed_btn')
start_crypto_btn = InlineKeyboardButton('💎 Курс крипты', callback_data='crypto_btn')
start_kb = InlineKeyboardMarkup(row_width=2).add(start_crypto_btn, start_fixed_btn)

# кнопки колбэка fixed_btn
fixed_crypto_btn = InlineKeyboardButton('💎 Криптовалюта', callback_data='crypto_fixed')
cancel_btn = InlineKeyboardButton('✖️ Отменить', callback_data='cancel')
fixed_kb = InlineKeyboardMarkup(row_width=2).add(fixed_crypto_btn, cancel_btn)

# кнопки колбэка crypto_fixed
btc_usd_btn = InlineKeyboardButton('BTC-USD', callback_data='btc_usd')
eth_usd_btn = InlineKeyboardButton('ETH-USD', callback_data='eth_usd')
doge_usd_btn = InlineKeyboardButton('DOGE-USD', callback_data='doge_usd')
ada_usd_btn = InlineKeyboardButton('ADA-USD', callback_data='ada_usd')
xrp_usd_btn = InlineKeyboardButton('XRP-USD', callback_data='xrp_usd')
ltc_usd_btn = InlineKeyboardButton('LTC-USD', callback_data='ltc_usd')
cancel_btn = InlineKeyboardButton('✖️ Отменить', callback_data='cancel')
fixed_crypto_kb = InlineKeyboardMarkup(row_width=2).add(btc_usd_btn, eth_usd_btn, doge_usd_btn, ada_usd_btn, xrp_usd_btn, ltc_usd_btn, cancel_btn)

# кнопка отмены
cancel_btn = InlineKeyboardButton('✖️ Отменить', callback_data='cancel')
cancel_kb = InlineKeyboardMarkup(row_width=2).add(cancel_btn)
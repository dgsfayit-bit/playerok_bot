import urllib.request
import urllib.parse
import json
import time
import random
import re
import html

TOKEN = "8935534470:AAFrUCn-9EVhgSm4FUMfy8vUEX3h1FLcIOQ"
ADMIN_USERNAME = "k13_way"
BASE_URL = "https://api.telegram.org/bot" + TOKEN + "/"

PHOTO_URL = "https://i.ibb.co/rKxGVDJr/5218-B427-201-E-4-FAA-A386-A29224-D07-A9-A.png"

# Хранилище данных
users = {}               # user_id -> {balance, deals, username, rating, reviews_count, banned}
states = {}              # user_id -> текущее состояние (awaiting_deal_data, awaiting_payment, etc.)
pending_role = {}        # user_id -> 'buyer' или 'seller'
pending_data = {}        # user_id -> временные данные для сделки (игра, категория, роль, ...)
active_deals = {}        # deal_number -> данные сделки
admins = []              # список username админов (без @)

def escape_html(text):
    return html.escape(str(text))

def api_request(method, params=None, post_data=None):
    url = BASE_URL + method
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    if post_data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(post_data).encode('utf-8')
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read().decode('utf-8')
            if data:
                return json.loads(data)
            else:
                return None
    except Exception as e:
        print("API request error:", e)
        return None

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    return api_request('sendMessage', params)

def send_photo(chat_id, photo, caption=None, reply_markup=None, parse_mode='HTML'):
    params = {'chat_id': chat_id, 'photo': photo, 'parse_mode': parse_mode}
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    return api_request('sendPhoto', params)

def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode='HTML'):
    params = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': parse_mode}
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    return api_request('editMessageText', params)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    params = {'callback_query_id': callback_query_id}
    if text:
        params['text'] = text
        params['show_alert'] = show_alert
    return api_request('answerCallbackQuery', params)

def get_updates(offset=None, timeout=60):
    params = {'timeout': timeout}
    if offset is not None:
        params['offset'] = offset
    response = api_request('getUpdates', params)
    if response and response.get('ok'):
        return response
    return None

# ================== КЛАВИАТУРЫ ==================
def get_main_menu_keyboard():
    return {
        'inline_keyboard': [
            [{'text': 'Создать Сделку', 'callback_data': 'create_deal'}],
            [{'text': 'Кошелек', 'callback_data': 'wallet'}],
            [{'text': 'Безопасность', 'callback_data': 'security'}],
            [{'text': 'Вывод средств', 'callback_data': 'withdraw_menu'}],
            [{'text': 'Канал', 'callback_data': 'channel'}],
            [{'text': 'Поддержка', 'callback_data': 'support'}],
            [{'text': 'Язык', 'callback_data': 'language'}]
        ]
    }

def get_back_keyboard():
    return {
        'inline_keyboard': [
            [{'text': '🔙 Назад в меню', 'callback_data': 'back'}]
        ]
    }

def get_games_keyboard():
    return {
        'inline_keyboard': [
            [{'text': 'Standoff 2', 'callback_data': 'game_standoff'}],
            [{'text': 'PUBG Mobile', 'callback_data': 'game_pubg'}],
            [{'text': 'Roblox', 'callback_data': 'game_roblox'}],
            [{'text': 'Minecraft (Java, PE)', 'callback_data': 'game_minecraft'}],
            [{'text': 'Genshin Impact', 'callback_data': 'game_genshin'}],
            [{'text': 'Brawl Stars', 'callback_data': 'game_brawl'}],
            [{'text': 'FC Mobile', 'callback_data': 'game_fc'}],
            [{'text': 'Clash of Clans', 'callback_data': 'game_coc'}],
            [{'text': 'Clash Royale', 'callback_data': 'game_cr'}],
            [{'text': '🔙 Назад в меню', 'callback_data': 'back'}]
        ]
    }

def get_category_keyboard(game):
    # для каждой игры возвращаем свои категории, но пока везде одинаковые
    return {
        'inline_keyboard': [
            [{'text': 'Купить/Продать Gold ⭐️', 'callback_data': f'cat_{game}_gold'}],
            [{'text': 'Купить/Продать Акции 📈', 'callback_data': f'cat_{game}_akcii'}],
            [{'text': 'Купить/Продать Gold Pass 💵', 'callback_data': f'cat_{game}_goldpass'}],
            [{'text': 'Купить/Продать Аккаунт 🧑‍💻', 'callback_data': f'cat_{game}_account'}],
            [{'text': 'Купить/Продать Скин 🗡️', 'callback_data': f'cat_{game}_skin'}],
            [{'text': '🔙 Назад', 'callback_data': 'back_to_games'}]
        ]
    }

def get_role_keyboard():
    return {
        'inline_keyboard': [
            [{'text': 'Я покупаю 🙋', 'callback_data': 'role_buyer'}],
            [{'text': 'Я продаю 🙋‍♂️', 'callback_data': 'role_seller'}]
        ]
    }

def get_accept_reject_keyboard(deal_number):
    return {
        'inline_keyboard': [
            [
                {'text': '✅ Принять сделку', 'callback_data': f'accept_{deal_number}'},
                {'text': '❌ Отменить сделку', 'callback_data': f'reject_{deal_number}'}
            ]
        ]
    }

def get_pay_keyboard(deal_number):
    return {
        'inline_keyboard': [
            [{'text': '💰 Оплатить', 'callback_data': f'pay_{deal_number}'}]
        ]
    }

def get_transferred_keyboard(deal_number):
    return {
        'inline_keyboard': [
            [{'text': 'Я передал 📦', 'callback_data': f'transfer_{deal_number}'}]
        ]
    }

def get_confirm_keyboard(deal_number):
    return {
        'inline_keyboard': [
            [{'text': 'Подтвердить покупку 🎉', 'callback_data': f'confirm_{deal_number}'}]
        ]
    }

def get_empty_keyboard():
    return {'inline_keyboard': []}

def get_wallet_keyboard():
    return {
        'inline_keyboard': [
            [{'text': 'Пополнить 💰', 'callback_data': 'deposit'}],
            [{'text': 'Вывести 💸', 'callback_data': 'withdraw_funds'}],
            [{'text': '🔙 Назад в меню', 'callback_data': 'back'}]
        ]
    }

def get_withdraw_methods_keyboard():
    return {
        'inline_keyboard': [
            [{'text': 'Telegram Кошелек ✈️', 'callback_data': 'withdraw_tg'}],
            [{'text': 'USDT 💲', 'callback_data': 'withdraw_usdt'}],
            [{'text': 'Сайт playerok.com 🛡️', 'callback_data': 'withdraw_site'}],
            [{'text': 'Карта 💳', 'callback_data': 'withdraw_card'}],
            [{'text': '🔙 Назад', 'callback_data': 'back_to_wallet'}]
        ]
    }

# ================== ПРИВЕТСТВИЕ ==================
def handle_start(chat_id):
    user_count = len(users)
    text = (
        f"<b>Playerok | Гарант-бот</b>\n"
        f"{user_count} пользователей\n\n"
        f"<b>Добро пожаловать 🎉</b>\n\n"
        f"✔ <b>PlayerOk</b> — специализированный сервис по обеспечению безопасности внебиржевых сделок.\n\n"
        f"🎁 Автоматизированный алгоритм исполнения.\n"
        f"🔒 Скорость и автоматизация.\n"
        f"📈 Удобный и быстрый вывод средств.\n\n"
        f"- Комиссия сервиса: 10%\n"
        f"- Режим работы: 24/7\n"
        f"- Поддержка: @playerokevents\n\n"
        f"<i>Выберите нужный раздел ниже:</i>"
    )
    reply_markup = get_main_menu_keyboard()
    try:
        send_photo(chat_id, PHOTO_URL, caption=text, reply_markup=reply_markup)
    except Exception as e:
        print("Ошибка отправки фото:", e)
        send_message(chat_id, text, reply_markup)

# ================== ОБРАБОТКА CALLBACK ==================
def process_callback(callback):
    user_id = callback['from']['id']
    username = callback['from'].get('username')
    if user_id not in users:
        users[user_id] = {'balance': 0, 'deals': 0, 'username': username or '', 'rating': 5.0, 'reviews_count': 0, 'banned': False}
    # Проверка бана
    if users[user_id].get('banned', False):
        answer_callback_query(callback['id'], text="❌ Вы забанены и не можете использовать бота.", show_alert=True)
        return

    data = callback['data']
    chat_id = callback['message']['chat']['id']
    message_id = callback['message']['message_id']
    answer_callback_query(callback['id'])

    print(f"Callback data: {data}")

    # Обработка "Назад в меню"
    if data == 'back':
        handle_start(chat_id)
        return

    # ---------- ГЛАВНОЕ МЕНЮ ----------
    if data == 'create_deal':
        text = "🛡️ <b>Выберите категорию</b>"
        reply_markup = get_games_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'wallet':
        show_wallet(chat_id, message_id, user_id)
        return

    if data == 'security':
        text = (
            "🛡️<b>Безопасность PlayerOK Гарант</b>\n\n"
            "🤖<b>Мы решили попробовать сферу бота Гаранта в Telegram</b>!\n\n"
            "❓<b>Как работает наш бот в Telegram</b>? <b>Стоит ли доверять ему и людям которые вас привели из сайта</b>? <b>Да, определенно стоит, т.к это наш официальный настоящий бот Гарант PlayerOK</b>!\n\n"
            "📦<b>Сделки стали гораздо легче, а комиссия теперь 10%</b>!\n\n"
            "❗️<b>Наш настоящий Гарант бот всего один, не ведитесь на фейки такие как подделывают нашего бота и пытаются вас обмануть, наш единственный и настоящий бот @PlayerokServiceBot_bot</b>\n\n"
            "🔥<b>Наш настоящий, единственный сайт playerok.com</b>\n\n"
            "❤️<b>Удачных вам сделок в нашей новой сфере продвижения, с любовью PlayerOK</b>"
        )
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'withdraw_menu':
        text = "🛡️<b>Выберите категорию вывода</b>:"
        reply_markup = get_withdraw_methods_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'channel':
        text = "📢 <b>Наш канал</b>\n\nПодписывайтесь на наш официальный канал, чтобы быть в курсе всех новостей и акций:\n\n👉 https://t.me/playerok_com"
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'support':
        text = (
            "🛡️<b>Поддержка PlayerOK</b>\n\n"
            "📌<b>В случае спорных моментов во время сделки либо еще других вопросов, обращайтесь в поддержку указанную выше</b>\n\n"
            "❤️<b>С любовью, PlayerOK</b>"
        )
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'language':
        text = "🌐 <b>Выберите язык</b>\n\nРусский — 🇷🇺\nEnglish — 🇬🇧\n\nПока доступен только русский язык."
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    # ---------- ВЫБОР ИГРЫ ----------
    if data.startswith('game_'):
        game = data.split('_')[1]
        pending_data[user_id] = {'game': game}
        text = "✅ <b>Отлично, категория почти выбрана !</b>\n<b>Выберите нужный раздел</b> ✅"
        reply_markup = get_category_keyboard(game)
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'back_to_games':
        text = "🛡️ <b>Выберите категорию</b>"
        reply_markup = get_games_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    # ---------- ВЫБОР КАТЕГОРИИ ----------
    if data.startswith('cat_'):
        # формат: cat_game_category
        parts = data.split('_')
        game = parts[1]
        category = parts[2]
        pending_data[user_id]['category'] = category
        # Сохраняем игру и категорию
        text = "🔥<b>Выберите роль</b>:"
        reply_markup = get_role_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    # ---------- ВЫБОР РОЛИ ----------
    if data == 'role_buyer' or data == 'role_seller':
        role = 'buyer' if data == 'role_buyer' else 'seller'
        pending_data[user_id]['role'] = role
        pending_data[user_id]['step'] = 'awaiting_data'
        if role == 'buyer':
            text = (
                "🔥<b>Отлично, роль выбрана, осталось совсем немного</b>🔥\n\n"
                "✅<b>Напишите в одном предложении @username второго участника, сумму сделки которую вы согласовали, и количество Gold</b>"
            )
        else:
            text = (
                "🔥<b>Отлично, роль выбрана, осталось совсем немного</b>🔥\n\n"
                "✅<b>Напишите в одном предложении @username второго участника, сумму сделки которую вы согласовали, и количество Gold</b>"
            )
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        states[user_id] = 'awaiting_deal_data'
        return

    # ---------- ОБРАБОТКА СДЕЛОК (accept, reject, pay, transfer, confirm) ----------
    if data.startswith('accept_'):
        deal_number = int(data.split('_')[1])
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, "❌ Нет активной сделки.")
            return
        if user_id != deal['seller_id']:
            send_message(chat_id, "❌ Вы не являетесь продавцом в этой сделке.")
            return
        # Продавец принимает сделку
        deal['status'] = 'accepted'
        # Отправляем покупателю кнопку "Оплатить"
        buyer_id = deal['buyer_id']
        buyer_notify = (
            f"🎉<b>Продавец принял сделку</b>!\n\n"
            f"❗️<b>Покупатель</b>: @{deal['buyer_username']}\n"
            f"❗️<b>Продавец</b>: @{deal['seller_username']}\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {deal['amount']} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {deal['item']}\n\n"
            f"✅<b>Ожидайте пока покупатель оплатит товар</b>"
        )
        send_message(buyer_id, buyer_notify, get_pay_keyboard(deal_number))

        seller_notify = (
            f"🎉<b>Продавец принял сделку</b>!\n\n"
            f"❗️<b>Покупатель</b>: @{deal['buyer_username']}\n"
            f"❗️<b>Продавец</b>: @{deal['seller_username']}\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {deal['amount']} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {deal['item']}\n\n"
            f"✅<b>Ожидайте пока покупатель оплатит товар</b>"
        )
        send_message(chat_id, seller_notify, get_empty_keyboard())

        # Обновляем сообщение у продавца (карточка сделки) - теперь она не нужна, мы отправили новое
        edit_message_text(chat_id, message_id, "✅ Сделка принята.", get_empty_keyboard())
        return

    if data.startswith('reject_'):
        deal_number = int(data.split('_')[1])
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, "❌ Нет активной сделки.")
            return
        if user_id != deal['seller_id']:
            send_message(chat_id, "❌ Вы не являетесь продавцом в этой сделке.")
            return
        # Отклоняем сделку
        buyer_id = deal['buyer_id']
        seller_id = deal['seller_id']
        buyer_username = deal['buyer_username']
        seller_username = deal['seller_username']
        amount = deal['amount']
        item = deal['item']
        cancel_text = (
            f"❌<b>Сделка была отклонена продавцом</b>\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {amount} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {item}\n"
            f"❗️<b>Покупатель</b>: @{buyer_username}\n"
            f"❗️<b>Продавец</b>: @{seller_username}"
        )
        send_message(buyer_id, cancel_text, get_empty_keyboard())
        send_message(seller_id, cancel_text, get_empty_keyboard())
        del active_deals[deal_number]
        edit_message_text(chat_id, message_id, "❌ Сделка отклонена.", get_empty_keyboard())
        return

    if data.startswith('pay_'):
        deal_number = int(data.split('_')[1])
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, "❌ Нет активной сделки.")
            return
        if user_id != deal['buyer_id']:
            send_message(chat_id, "❌ Вы не являетесь покупателем в этой сделке.")
            return
        # Проверяем баланс покупателя
        buyer_balance = users[user_id]['balance']
        amount = deal['amount']
        if buyer_balance < amount:
            send_message(chat_id, f"❌ Недостаточно средств. Ваш баланс: {buyer_balance} руб., сумма сделки: {amount} руб.")
            return
        # Списываем деньги
        users[user_id]['balance'] -= amount
        # Меняем статус
        deal['status'] = 'paid'
        # Уведомляем покупателя
        buyer_notify = (
            f"✅<b>Успешно! Вы оплатили сделку</b>:\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {amount} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {deal['item']}\n\n"
            f"📦<b>Ожидайте пока продавец передаст вам товар</b>"
        )
        send_message(chat_id, buyer_notify, get_empty_keyboard())
        # Уведомляем продавца
        seller_id = deal['seller_id']
        seller_notify = (
            f"✅<b>Покупатель оплатил товар</b>!\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {amount} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {deal['item']}\n\n"
            f"❗️<b>Передайте покупателю товар в личные сообщения Telegram с видеозаписью, когда передадите товар и покупатель проверит, нажмите на кнопку \"Я передал\"</b>"
        )
        send_message(seller_id, seller_notify, get_transferred_keyboard(deal_number))
        # Удаляем кнопку оплаты у покупателя
        # Также можно удалить сообщение с кнопкой оплаты, но мы просто отправили новое
        return

    if data.startswith('transfer_'):
        deal_number = int(data.split('_')[1])
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, "❌ Нет активной сделки.")
            return
        if user_id != deal['seller_id']:
            send_message(chat_id, "❌ Вы не являетесь продавцом в этой сделке.")
            return
        # Продавец передал товар
        deal['status'] = 'transferred'
        buyer_id = deal['buyer_id']
        buyer_notify = (
            f"📌<b>Продавец сообщил, что передал товар</b>\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {deal['amount']} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {deal['item']}\n\n"
            f"❗️<b>Проверьте товар и подтвердите покупку</b>"
        )
        send_message(buyer_id, buyer_notify, get_confirm_keyboard(deal_number))
        # Продавцу: кнопка убирается, просто уведомление
        send_message(chat_id, "✅ Вы отметили передачу товара. Ожидайте подтверждения от покупателя.", get_empty_keyboard())
        return

    if data.startswith('confirm_'):
        deal_number = int(data.split('_')[1])
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, "❌ Нет активной сделки.")
            return
        if user_id != deal['buyer_id']:
            send_message(chat_id, "❌ Вы не являетесь покупателем в этой сделке.")
            return
        # Покупатель подтверждает получение
        # Зачисляем продавцу деньги с комиссией 10%
        seller_id = deal['seller_id']
        amount = deal['amount']
        commission = 0.1
        amount_to_seller = amount * (1 - commission)
        amount_to_seller = round(amount_to_seller, 2)
        if seller_id in users:
            users[seller_id]['balance'] += amount_to_seller
        # Увеличиваем счетчик завершённых сделок у покупателя
        if user_id in users:
            users[user_id]['deals'] += 1
        # Удаляем сделку
        del active_deals[deal_number]

        # Уведомление продавцу
        seller_notify = (
            f"🎉<b>Покупатель подтвердил покупку</b>!\n"
            f"<b>Ваши средства были зачислены вам на баланс, вы можете их вывести либо на карту (USDT-кошелек), либо прямо на сайт playerok.com</b>\n"
            f"<b>Ваши средства будут разморожены спустя 48ч для безопасности</b>\n"
            f"<b>С любовью, PlayerOK</b> ❤️"
        )
        send_message(seller_id, seller_notify, get_empty_keyboard())
        # Уведомление покупателю
        buyer_notify = (
            f"🎉<b>Покупатель подтвердил покупку</b>!\n\n"
            f"✅<b>Сделка успешно завершена!</b>"
        )
        send_message(chat_id, buyer_notify, get_empty_keyboard())
        # Также отправляем финальное сообщение продавцу о зачислении
        return

    # ---------- КОШЕЛЕК ----------
    if data == 'deposit':
        text = "🔥 <b>Пополнить баланс в Гарант боте Playerok</b> стало гораздо легче!\n\n💰 Чтобы выполнить пополнение, вам нужно обратиться к нашему модеру и менеджеру\n\n🧑‍💻 <b>Поддержка:</b> @playerokevents"
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'withdraw_funds':
        # Показываем меню вывода (заглушка)
        text = "🛡️<b>Выберите категорию вывода</b>:"
        reply_markup = get_withdraw_methods_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data.startswith('withdraw_'):
        # Все варианты вывода - заглушка
        text = "✅ Функция вывода в разработке. Скоро появится."
        reply_markup = get_back_keyboard()
        edit_message_text(chat_id, message_id, text, reply_markup)
        return

    if data == 'back_to_wallet':
        show_wallet(chat_id, message_id, user_id)
        return

    # ---------- ВЫВОД СРЕДСТВ (из кошелька) ----------
    # пока заглушка, уже обработали выше

    # ---------- ЕСЛИ НИЧЕГО НЕ ПОДОШЛО ----------
    send_message(chat_id, "⚠️ Неизвестная команда.")

def show_wallet(chat_id, message_id, user_id):
    user_data = users.get(user_id, {'balance': 0, 'deals': 0, 'username': '', 'rating': 5.0, 'reviews_count': 0})
    balance = user_data['balance']
    deals = user_data['deals']
    uname = user_data.get('username') or str(user_id)
    rating = user_data.get('rating', 5.0)
    reviews = user_data.get('reviews_count', 0)
    text = (
        f"💰 <b>Ваш кошелек</b>\n\n"
        f"👤 <b>Юзернейм:</b> @{uname}\n"
        f"💳 <b>Баланс:</b> <code>{balance} руб.</code>\n"
        f"🤝 <b>Завершенные сделки:</b> <code>{deals}</code>\n"
        f"📊 <b>Отзывы:</b> ⭐️ {rating} ({reviews} отзывов)\n\n"
        f"✨ <i>Ваши средства защищены гарантом Playerok.</i>"
    )
    reply_markup = get_wallet_keyboard()
    edit_message_text(chat_id, message_id, text, reply_markup)

# ================== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==================
def process_message(message):
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    username = message['from'].get('username')
    if user_id not in users:
        users[user_id] = {'balance': 0, 'deals': 0, 'username': username or '', 'rating': 5.0, 'reviews_count': 0, 'banned': False}
    if users[user_id].get('banned', False):
        send_message(chat_id, "❌ Вы забанены и не можете использовать бота.")
        return

    text = message.get('text')
    if not text:
        return

    if text.startswith('/start'):
        handle_start(chat_id)
        return

    # ===== АДМИН-КОМАНДЫ =====
    # Проверка, является ли пользователь главным админом или админом
    is_admin = (username and (username.lower() == ADMIN_USERNAME.lower() or username.lower() in [a.lower() for a in admins]))

    if text.startswith('/help'):
        if is_admin:
            help_text = (
                "<b>📋 Список команд (админ)</b>\n\n"
                "/start — Главное меню\n"
                "/set admin @username — Выдать админку\n"
                "/remove admin @username — Снять админку\n"
                "/money @username сумма — Начислить деньги\n"
                "/set_deals @username количество — Установить завершённые сделки\n"
                "/set_star @username количество — Установить отзывы (5 звёзд)\n"
                "/deals_cancel #номер — Отменить сделку (любую)\n"
                "/ban @username — Забанить пользователя\n"
                "/deals — Показать все активные сделки\n"
                "/help — Эта справка"
            )
        else:
            help_text = (
                "<b>📋 Список команд</b>\n\n"
                "/start — Главное меню\n"
                "/help — Эта справка"
            )
        send_message(chat_id, help_text)
        return

    if text.startswith('/set admin'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "❌ Используйте: /set admin @username")
            return
        target = parts[2].lstrip('@')
        if not target:
            send_message(chat_id, "❌ Неверный юзернейм.")
            return
        # Проверяем, есть ли пользователь в users
        found = False
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target.lower():
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Пользователь @{target} не найден (не писал /start).")
            return
        if target.lower() == ADMIN_USERNAME.lower():
            send_message(chat_id, "❌ Это главный админ.")
            return
        if target.lower() in [a.lower() for a in admins]:
            send_message(chat_id, f"❌ @{target} уже админ.")
            return
        admins.append(target)
        send_message(chat_id, f"✅ Пользователю @{target} выдана админка.")
        return

    if text.startswith('/remove admin'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "❌ Используйте: /remove admin @username")
            return
        target = parts[2].lstrip('@')
        if not target:
            send_message(chat_id, "❌ Неверный юзернейм.")
            return
        if target.lower() == ADMIN_USERNAME.lower():
            send_message(chat_id, "❌ Нельзя снять админку с главного админа.")
            return
        if target.lower() not in [a.lower() for a in admins]:
            send_message(chat_id, f"❌ @{target} не является админом.")
            return
        admins.remove(target)
        send_message(chat_id, f"✅ Админка у @{target} удалена.")
        return

    if text.startswith('/money'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "❌ Используйте: /money @username сумма")
            return
        target = parts[1].lstrip('@')
        try:
            amount = float(parts[2])
        except:
            send_message(chat_id, "❌ Неверная сумма.")
            return
        found = False
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target.lower():
                users[uid]['balance'] += amount
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Пользователь @{target} не найден.")
            return
        send_message(chat_id, f"✅ Пользователю @{target} начислено {amount} руб.")
        return

    if text.startswith('/set_deals'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "❌ Используйте: /set_deals @username количество")
            return
        target = parts[1].lstrip('@')
        try:
            count = int(parts[2])
        except:
            send_message(chat_id, "❌ Количество должно быть числом.")
            return
        if count < 0:
            send_message(chat_id, "❌ Количество не может быть отрицательным.")
            return
        found = False
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target.lower():
                users[uid]['deals'] = count
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Пользователь @{target} не найден.")
            return
        send_message(chat_id, f"✅ Пользователю @{target} установлено {count} завершённых сделок.")
        return

    if text.startswith('/set_star'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "❌ Используйте: /set_star @username количество")
            return
        target = parts[1].lstrip('@')
        try:
            count = int(parts[2])
        except:
            send_message(chat_id, "❌ Количество должно быть числом.")
            return
        if count < 0:
            send_message(chat_id, "❌ Количество не может быть отрицательным.")
            return
        found = False
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target.lower():
                users[uid]['rating'] = 5.0
                users[uid]['reviews_count'] = count
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Пользователь @{target} не найден.")
            return
        send_message(chat_id, f"✅ Пользователю @{target} установлено {count} отзывов с рейтингом 5.0 ⭐️")
        return

    if text.startswith('/deals_cancel'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, "❌ Используйте: /deals_cancel #номер")
            return
        deal_str = parts[1].lstrip('#')
        try:
            deal_number = int(deal_str)
        except:
            send_message(chat_id, "❌ Неверный номер сделки.")
            return
        deal = active_deals.get(deal_number)
        if not deal:
            send_message(chat_id, f"❌ Сделки #{deal_number} не существует.")
            return
        # Отменяем сделку
        buyer_id = deal['buyer_id']
        seller_id = deal['seller_id']
        cancel_text = f"❌ <b>Сделка #{deal_number} отменена администратором.</b>"
        send_message(buyer_id, cancel_text, get_empty_keyboard())
        send_message(seller_id, cancel_text, get_empty_keyboard())
        del active_deals[deal_number]
        send_message(chat_id, f"✅ Сделка #{deal_number} отменена.")
        return

    if text.startswith('/ban'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, "❌ Используйте: /ban @username")
            return
        target = parts[1].lstrip('@')
        if not target:
            send_message(chat_id, "❌ Неверный юзернейм.")
            return
        if target.lower() == ADMIN_USERNAME.lower():
            send_message(chat_id, "❌ Нельзя забанить главного админа.")
            return
        found = False
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target.lower():
                users[uid]['banned'] = True
                found = True
                break
        if not found:
            send_message(chat_id, f"❌ Пользователь @{target} не найден.")
            return
        send_message(chat_id, f"✅ Пользователь @{target} забанен.")
        return

    if text.startswith('/deals'):
        if not is_admin:
            send_message(chat_id, "❌ Отказано в доступе.")
            return
        if not active_deals:
            send_message(chat_id, "📭 Нет активных сделок.")
            return
        deals_list = "📋 <b>Все активные сделки:</b>\n\n"
        for num, deal in active_deals.items():
            deals_list += (
                f"<b>#{num}</b>\n"
                f"👤 Покупатель: @{deal['buyer_username']}\n"
                f"👤 Продавец: @{deal['seller_username']}\n"
                f"💵 Сумма: {deal['amount']} руб.\n"
                f"📦 Товар: {deal['item']}\n"
                f"📊 Статус: {deal.get('status', 'ожидание')}\n"
                f"---\n"
            )
        send_message(chat_id, deals_list)
        return

    # ===== ОБРАБОТКА ВВОДА ДАННЫХ ДЛЯ СДЕЛКИ =====
    if states.get(user_id) == 'awaiting_deal_data':
        # Парсим сообщение: ожидается @username сумма количество
        parts = text.split()
        if len(parts) < 3:
            send_message(chat_id, "⚠️ Неверный формат. Введите: @username сумма количество")
            return
        target_username = parts[0].lstrip('@')
        try:
            amount = float(parts[1])
        except:
            send_message(chat_id, "⚠️ Сумма должна быть числом.")
            return
        item = ' '.join(parts[2:])  # остальное - название товара

        # Проверяем, есть ли второй участник в users
        receiver_id = None
        for uid, data in users.items():
            if data.get('username') and data['username'].lower() == target_username.lower():
                receiver_id = uid
                break
        if receiver_id is None:
            send_message(chat_id, f"❌ Пользователь @{target_username} не найден. Попросите его написать /start боту.")
            states[user_id] = None
            return

        # Проверяем, не занят ли получатель активной сделкой
        for deal in active_deals.values():
            if deal['seller_id'] == receiver_id or deal['buyer_id'] == receiver_id:
                send_message(chat_id, f"❌ У пользователя @{target_username} уже есть активная сделка.")
                states[user_id] = None
                return

        # Создаём сделку
        deal_number = random.randint(1000, 9999)
        while deal_number in active_deals:
            deal_number = random.randint(1000, 9999)

        game = pending_data.get(user_id, {}).get('game', 'Неизвестно')
        category = pending_data.get(user_id, {}).get('category', 'Неизвестно')
        role = pending_data.get(user_id, {}).get('role', 'buyer')  # buyer или seller

        # Определяем покупателя и продавца
        if role == 'buyer':
            buyer_id = user_id
            seller_id = receiver_id
            buyer_username = users[user_id].get('username') or str(user_id)
            seller_username = users[receiver_id].get('username') or str(receiver_id)
        else:  # seller
            seller_id = user_id
            buyer_id = receiver_id
            seller_username = users[user_id].get('username') or str(user_id)
            buyer_username = users[receiver_id].get('username') or str(receiver_id)

        # Сохраняем сделку
        deal_data = {
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'buyer_username': buyer_username,
            'seller_username': seller_username,
            'amount': amount,
            'item': item,
            'status': 'pending',  # pending, accepted, paid, transferred, completed
            'game': game,
            'category': category,
            'role': role
        }
        active_deals[deal_number] = deal_data

        # Отправляем уведомление покупателю (инициатору)
        buyer_notify = (
            f"✅<b>Успешно! Сделка создана и отправлена второму участнику, ожидайте его решения.</b>\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {amount} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {item}"
        )
        send_message(chat_id, buyer_notify, get_empty_keyboard())

        # Отправляем уведомление продавцу (получателю)
        seller_notify = (
            f"🎉<b>Вам предложили Сделку!</b>\n\n"
            f"🔢<b>Номер сделки</b>: #{deal_number}\n"
            f"💵<b>Сумма товара</b>: {amount} руб.\n"
            f"🧑‍💻<b>Название товара</b>: {item}\n"
            f"✅<b>Покупатель в предложенной вам сделке</b>: @{buyer_username}\n\n"
            f"❗️<b>Как провести сделку?</b>\n"
            f"📈<b>Вы можете передать товар покупателю в личные сообщения Telegram, или через гарант чат в боте PlayerOK</b>\n"
            f"📌1. <b>Вы должны собрать как можно больше доказательств когда передаете товар, такие как</b>:\n"
            f"✅<b>Видеозапись экрана, скриншоты где виден номер сделки, @username покупателя и причина проблемы, в случае чего вы можете обратиться к поддержке с доказательствами и вам обязательно помогут</b>"
        )
        send_message(receiver_id, seller_notify, get_accept_reject_keyboard(deal_number))

        # Очищаем состояние
        states[user_id] = None
        pending_data.pop(user_id, None)
        return

    # Если ничего не подошло
    send_message(chat_id, "⚠️ Неизвестная команда. Используйте /start")

# ================== ГЛАВНЫЙ ЦИКЛ ==================
def main():
    print("🚀 Бот запущен! Ожидание команд...")
    last_update_id = None
    while True:
        try:
            updates_response = get_updates(offset=last_update_id)
            if updates_response and updates_response.get('ok') and updates_response.get('result'):
                for update in updates_response['result']:
                    last_update_id = update['update_id'] + 1
                    if 'callback_query' in update:
                        process_callback(update['callback_query'])
                    elif 'message' in update:
                        process_message(update['message'])
            time.sleep(0.3)
        except Exception as e:
            print("Main loop error:", e)
            time.sleep(5)

if __name__ == '__main__':
    main()

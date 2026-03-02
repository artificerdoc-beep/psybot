import os
import logging
import random
import re
import csv
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
import pymorphy2

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в файле .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

morph = pymorphy2.MorphAnalyzer()

# ==================== НАСТРОЙКИ CSV ====================
CSV_FILENAME = 'dialogues.csv'

def init_csv():
    """Создаёт файл с заголовками, если его нет."""
    file_exists = os.path.isfile(CSV_FILENAME)
    try:
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'user_id', 'username', 'first_name', 'message', 'emotion', 'bot_response'])
        logger.info(f"CSV файл инициализирован: {os.path.abspath(CSV_FILENAME)}")
    except Exception as e:
        logger.error(f"Ошибка создания CSV: {e}")

def save_to_csv(user_id, username, first_name, message, emotion, bot_response):
    """Добавляет запись в CSV."""
    try:
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id,
                username or '',
                first_name or '',
                message,
                emotion,
                bot_response
            ])
    except Exception as e:
        logger.error(f"Ошибка записи в CSV: {e}")

# ==================== СЛОВАРИ ЭМОЦИЙ ====================
emotion_keywords = {
    'грусть': [
        'грустный', 'печаль', 'тоска', 'уныние', 'плохо', 'депрессия', 'одинокий',
        'слезы', 'плакать', 'несчастный', 'горе', 'больно', 'тоскливо', 'уныло',
        'жаль', 'разбитый', 'подавленный', 'хандрить', 'кручиниться',
        'поддержка', 'близкий', 'понимание', 'внимание', 'забота',
        'никто', 'бросить', 'покинуть', 'не нужен', 'одиночество', 'беспомощный',
        'хуёво', 'херово', 'паршиво', 'дрянь', 'погано', 'муторно',
        'скучно', 'безысходно', 'безрадостно', 'невесело', 'грустновато',
        'одиноко', 'пусто', 'маленький член', 'никчемный', 'ничтожество'
    ],
    'тревога': [
        'тревога', 'страх', 'бояться', 'волнение', 'нервный', 'беспокойство',
        'паника', 'кошмар', 'ужас', 'боязнь', 'опасение', 'напряжение', 'испуг',
        'тревожный', 'неспокойно', 'взволнованный', 'переживать', 'страшно',
        'трясти', 'дрожь', 'сердцебиение', 'маета', 'не по себе',
        'жутко', 'тревожно', 'боязно'
    ],
    'гнев': [
        'злость', 'гнев', 'бесить', 'раздражать', 'ненавидеть', 'ярость', 'злиться',
        'агрессия', 'раздражение', 'возмущение', 'негодование', 'досада', 'злой',
        'сердитый', 'взбешенный', 'обида', 'гневаться', 'бешенство', 'презрение',
        'дурак', 'идиот', 'козёл', 'сволочь', 'тварь', 'ненависть', 'бесит',
        'дебил', 'тупой', 'глупый', 'бестолковый', 'не понимаешь', 'не слышишь',
        'игнорируешь', 'тупица', 'кретин', 'придурок', 'долбоеб', 'мудак'
    ],
    'радость': [
        'радость', 'счастье', 'отлично', 'прекрасно', 'хорошо', 'весело', 'улыбка',
        'позитив', 'классно', 'замечательно', 'чудесно', 'восторг', 'ликование',
        'довольный', 'счастливый', 'радоваться', 'веселиться', 'блаженство',
        'супер', 'круто', 'офигенно', 'клёво', 'заебись', 'шикарно', 'восхитительно',
        'прелесть', 'обалдеть', 'отпад', 'кайф', 'кайфовать', 'тащусь'
    ],
    'усталость': [
        'усталость', 'усталый', 'измотанный', 'нет сил', 'вымотанный', 'утомленный',
        'обессиленный', 'изнеможение', 'переутомление', 'выдохся', 'без сил',
        'утомительно', 'изнурение', 'устать', 'утомиться', 'измученный',
        'вымотался', 'без энергии', 'спать хочу', 'выжатый как лимон', 'ноги не идут'
    ]
}

# ==================== ОТВЕТЫ ====================
responses = {
    'грусть': [
        "Ох, грустно тебе... Расскажи, что случилось? Я рядом.",
        "Печаль — тяжёлое чувство. Хочешь выговориться? Я внимательно слушаю.",
        "Мне жаль, что тебе так хреново. Побудь с этим, я побуду рядом.",
        "Бывает такое состояние, когда всё валится из рук. Ты не один, я здесь.",
        "Держись, дружище. Расскажи, что тебя гнетёт?",
        "Слышу в твоих словах боль. Хочешь, просто посидим в тишине? Я никуда не уйду.",
        "Это действительно тяжело — переживать такое. Я с тобой.",
        "Ты можешь плакать, это нормально. Я выдержу твои слёзы."
    ],
    'тревога': [
        "Чувствую твою тревогу. Давай попробуем подышать вместе: вдох... выдох...",
        "Страшно бывает всем. Что именно вызывает страх? Расскажи, я рядом.",
        "Когда внутри всё дрожит, сложно успокоиться. Хочешь, поговорим о чём-то отвлекающем?",
        "Я здесь, чтобы поддержать. Тревога пройдёт, ты справишься.",
        "Тревога — как волна: накрывает и отступает. Давай переждём вместе.",
        "Представь, что ты держишь меня за руку. Вместе легче."
    ],
    'гнев': [
        "Ого, ты прям кипишь! Это нормально — злиться. На что именно?",
        "Злость иногда защищает нас. Что вызвало такую реакцию?",
        "Я чувствую твой гнев. Хочешь выплеснуть его словами? Я выдержу.",
        "Обида и злость часто ходят парой. Может, ещё и обидно?",
        "Давай-ка выдохнем и попробуем разобраться, что именно так бесит.",
        "Ты злишься на меня? Понимаю, я могу казаться бестолковым. Прости, если разочаровал.",
        "Я слышу твоё раздражение. Расскажи, что не так, я постараюсь понять.",
        "Ты имеешь право злиться. Даже на меня. Я здесь, чтобы выслушать."
    ],
    'радость': [
        "Ух ты, прямо светишься от счастья! Поделишься, что случилось?",
        "Как здорово! Рад за тебя. Расскажи подробнее, я тоже порадуюсь.",
        "Отлично! Такие моменты нужно ловить и запоминать.",
        "Супер! А что именно тебя так развеселило?",
        "Кайф! Продолжай в том же духе.",
        "Твоя радость заразительна! Спасибо, что поделился."
    ],
    'усталость': [
        "Вымотался? Присядь, выдохни. Ты много делаешь, пора отдохнуть.",
        "Усталость накапливается. Может, выпьешь воды и посидишь молча 5 минут?",
        "Слышу, как ты выдохся. Отдых — это не роскошь, а необходимость.",
        "Иногда просто нужно лечь и ничего не делать. Разреши себе это.",
        "Береги себя. Отдохни, а потом продолжим.",
        "Ты заслуживаешь отдыха. Побудь в покое."
    ],
    'нейтрально': [
        "Рассказывай, я весь во внимании.",
        "Как сам? Что нового?",
        "Что у тебя на душе?",
        "Я здесь, чтобы выслушать. Говори что хочешь.",
        "Слушаю тебя внимательно.",
        "Давай поболтаем. О чём хочешь поговорить?",
        "Можешь рассказывать всё, что придёт в голову."
    ]
}

DEFAULT_EMOTION = 'нейтрально'
user_context = {}
filler_words = {'да', 'нет', 'ок', 'окей', 'ладно', 'хорошо', 'понятно', 'ага', 'неа', 'конечно', 'бывает'}

def lemmatize_words(words):
    lemmas = []
    for w in words:
        try:
            parsed = morph.parse(w)[0]
            lemmas.append(parsed.normal_form)
        except:
            lemmas.append(w)
    return lemmas

def analyze_emotion(text, prev_emotion=None):
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    if words and all(w in filler_words for w in words):
        if prev_emotion and prev_emotion != 'нейтрально':
            return prev_emotion

    lemmas = lemmatize_words(words)

    negation_words = {'не', 'нет', 'ни', 'нельзя', 'никогда', 'без'}
    negation_present = any(neg in words for neg in negation_words)

    scores = {e: 0 for e in emotion_keywords}

    for lemma in lemmas:
        for emotion, keywords in emotion_keywords.items():
            if lemma in keywords:
                if negation_present and emotion == 'радость':
                    scores['грусть'] += 1
                else:
                    scores[emotion] += 1

    max_score = max(scores.values())
    if max_score == 0:
        if prev_emotion and prev_emotion != 'нейтрально':
            return prev_emotion
        else:
            return DEFAULT_EMOTION

    best_emotion = max(scores.items(), key=lambda x: x[1])[0]
    return best_emotion

def get_response(emotion, user_id):
    possible = responses[emotion]
    user_data = user_context.get(user_id, {})
    last_responses = user_data.get('last_responses', [])

    if last_responses:
        possible = [r for r in possible if r not in last_responses]
    if not possible:
        possible = responses[emotion]

    chosen = random.choice(possible)

    last_responses.append(chosen)
    if len(last_responses) > 3:
        last_responses.pop(0)

    if user_id not in user_context:
        user_context[user_id] = {}
    user_context[user_id]['last_responses'] = last_responses

    return chosen

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name or "Друг"
    await message.answer(
        f"Привет, {user_name}! Я твой живой собеседник для эмоциональной поддержки.\n"
        f"Можешь рассказывать мне всё, что у тебя на душе. Я всегда рядом.\n"
        f"Для списка команд используй /help"
    )
    logger.info(f"Пользователь {user_name} (ID: {message.from_user.id}) запустил бота")

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    help_text = (
        "🤖 **Как я работаю:**\n"
        "Я анализирую твои сообщения и определяю эмоцию, чтобы дать наиболее подходящий ответ.\n\n"
        "📝 **Команды:**\n"
        "/start - начать общение\n"
        "/help - показать эту справку\n"
        "/reset - сбросить контекст разговора\n\n"
        "Просто пиши мне свои мысли и чувства — я всегда рядом!"
    )
    await message.answer(help_text)

@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_context:
        del user_context[user_id]
    await message.answer("Контекст разговора сброшен. Начинаем с чистого листа.")

@dp.message_handler(content_types=['text'])
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_input = message.text.strip()
    username = message.from_user.username
    first_name = message.from_user.first_name

    prev_emotion = None
    if user_id in user_context:
        prev_emotion = user_context[user_id].get('prev_emotion')

    emotion = analyze_emotion(user_input, prev_emotion)
    response = get_response(emotion, user_id)

    if user_id not in user_context:
        user_context[user_id] = {}
    user_context[user_id]['prev_emotion'] = emotion

    # Сохраняем в CSV
    save_to_csv(user_id, username, first_name, user_input, emotion, response)

    logger.info(f"User {user_id}: '{user_input[:30]}...' -> emotion: {emotion}")
    await message.answer(response)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    init_csv()  # создаём CSV-файл при старте
    logger.info("Бот запускается...")
    executor.start_polling(dp, skip_updates=True)
import asyncio
import logging
import argparse
from telegram import Bot
from telegram.error import TelegramError
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from parser import parse_products
import os
from PIL import Image
import requests
from io import BytesIO

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Парсим аргументы командной строки
parser = argparse.ArgumentParser(description='Telegram бот для отслеживания товаров')
parser.add_argument('-v', '--verbose', action='store_true', help='Включить подробный вывод')
args = parser.parse_args()

# Настраиваем уровень логирования в зависимости от флага -v
if args.verbose:
    logger.setLevel(logging.DEBUG)
    logger.debug("Включен подробный вывод")
else:
    logger.setLevel(logging.INFO)

# Добавляем логирование для отладки
logger.info("Бот запущен")

# Путь к файлу для хранения данных о предыдущих товарах
PREVIOUS_PRODUCTS_FILE = 'previous_products.txt'

def load_previous_products():
    """
    Загружает информацию о предыдущих товарах из файла.
    """
    if not os.path.exists(PREVIOUS_PRODUCTS_FILE):
        return {}
    
    previous_products = {}
    with open(PREVIOUS_PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) == 3:
                name, price, available = parts
                previous_products[name] = {
                    'price': price,
                    'available': available == 'True'
                }
    return previous_products

def save_products(products):
    """
    Сохраняет информацию о товарах в файл.
    """
    with open(PREVIOUS_PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        for product in products:
            f.write(f"{product['name']}|{product['price']}|{product['is_available']}\n")

def resize_image_from_url(image_url, scale_factor=4):
    """
    Загружает изображение по URL и уменьшает его размер в scale_factor раз.
    
    Args:
        image_url (str): URL изображения
        scale_factor (int): Во сколько раз уменьшить изображение (по умолчанию 4)
        
    Returns:
        BytesIO: Буфер с уменьшенным изображением в формате JPEG
    """
    try:
        # Загружаем изображение по URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Открываем изображение с помощью PIL
        image = Image.open(BytesIO(response.content))
        
        # Вычисляем новые размеры
        new_width = image.width // scale_factor
        new_height = image.height // scale_factor
        
        # Уменьшаем изображение
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Сохраняем в буфер в формате JPEG
        buffer = BytesIO()
        resized_image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        return buffer
    except Exception as e:
        logger.error(f"Ошибка при изменении размера изображения {image_url}: {e}")
        return None

async def send_product_info(bot, product):
    """
    Отправляет информацию о товаре в Telegram.
    """
    message = f"📦 {product['name']}\n"
    message += f"💰 Цена: {product['price']} руб.\n"
    message += f"{'✅ В наличии' if product['is_available'] else '❌ Нет в наличии'}"
    
    try:
        if product['image_url']:
            # Если есть изображение, уменьшаем его и отправляем
            resized_image_buffer = resize_image_from_url(product['image_url'])
            
            if resized_image_buffer:
                # Отправляем уменьшенное изображение с подписью
                await bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=resized_image_buffer,
                    caption=message
                )
            else:
                # Если не удалось изменить размер, отправляем оригинальное изображение
                await bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=product['image_url'],
                    caption=message
                )
        else:
            # Если нет изображения, отправляем текстовое сообщение
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )
    except TelegramError as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")

    logger.info("Начало проверки товаров")
async def check_and_notify():
    """
    Проверяет изменения в товарах и отправляет уведомления.
    """
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Загружаем предыдущие товары
    previous_products = load_previous_products()
    logger.debug(f"Загружено {len(previous_products)} предыдущих товаров")
    
    # Получаем текущие товары
    current_products = parse_products()
    logger.debug(f"Получено {len(current_products)} текущих товаров")
    
    # Сохраняем текущие товары
    save_products(current_products)
    logger.debug("Текущие товары сохранены")
    
    # Преобразуем в словарь для удобства сравнения
    current_dict = {p['name']: p for p in current_products}
    previous_dict = {name: info for name, info in previous_products.items()}
    
    # Проверяем изменения
    changes_count = 0
    for name, current_info in current_dict.items():
        if name not in previous_dict:
            # Новый товар
            logger.info(f"Найден новый товар: {name}")
            await send_product_info(bot, current_info)
            changes_count += 1
        else:
            # Существующий товар - проверяем изменения
            previous_info = previous_dict[name]
            if (current_info['price'] != previous_info['price'] or
                current_info['is_available'] != previous_info['available']):
                # Изменилась цена или наличие
                logger.info(f"Изменения в товаре: {name}")
                await send_product_info(bot, current_info)
                changes_count += 1
    
    # Проверяем удаленные товары
    for name, previous_info in previous_dict.items():
        if name not in current_dict:
            # Товар удален
            logger.info(f"Товар удален: {name}")
            message = f"❌ Товар удален: {name}"
            try:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=message
                )
            except TelegramError as e:
                logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
            changes_count += 1
    
    logger.info(f"Проверка завершена. Найдено изменений: {changes_count}")

async def main():
    """
    Основная функция бота.
    """
    logger.info("Запуск основного цикла проверки товаров")
    while True:
        try:
            await check_and_notify()
        except Exception as e:
            logger.error(f"Ошибка при проверке товаров: {e}")
        
        # Ждем 5 минут перед следующей проверкой
        logger.debug("Ожидание следующей проверки")
        await asyncio.sleep(300)

if __name__ == '__main__':
    asyncio.run(main())
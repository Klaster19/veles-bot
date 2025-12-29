import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import json

def parse_products():
    """
    Парсит сайт магазина и возвращает список товаров с информацией о них.
    Использует Selenium для обработки динамически загружаемого контента.
    """
    # Настройка опций Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Запуск в фоновом режиме
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Создание веб-драйвера
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Загрузка страницы
        driver.get('https://veles-lab.ru/')
        
        # Ожидание загрузки контента (можно улучшить с помощью WebDriverWait)
        time.sleep(5)
        
        # Получение HTML после выполнения JavaScript
        html = driver.page_source
        
        # Поиск скрипта с данными о товарах
        scripts = driver.find_elements(By.TAG_NAME, "script")
        products = []
        
        for script in scripts:
            script_content = script.get_attribute("innerHTML")
            if script_content and "t_store_init" in script_content and "storepart" in script_content:
                # Извлечение данных о товарах из скрипта
                try:
                    # Поиск storepart ID
                    start = script_content.find("storepart':")
                    if start != -1:
                        start += len("storepart':")
                        end = script_content.find("'", start + 1)
                        storepart = script_content[start+1:end]
                        
                        # Поиск данных о товарах в скрипте
                        # Ищем JSON-подобные структуры с информацией о товарах
                        lines = script_content.split('\n')
                        for line in lines:
                            if 'prodCard:' in line or 'products:' in line:
                                # Простая попытка извлечь данные
                                # В реальном проекте здесь потребуется более сложный парсинг
                                pass
                except Exception as e:
                    print(f"Ошибка при извлечении данных из скрипта: {e}")
        
        # Альтернативный подход: поиск элементов напрямую в DOM
        try:
            # Поиск карточек товаров
            product_elements = driver.find_elements(By.CSS_SELECTOR, ".js-product")
            
            for element in product_elements:
                try:
                    # Название товара
                    name_element = element.find_element(By.CSS_SELECTOR, ".js-store-prod-name")
                    name = name_element.text.strip() if name_element else "Неизвестно"
                    
                    # Цена товара
                    price_element = element.find_element(By.CSS_SELECTOR, ".js-product-price")
                    price = price_element.text.strip() if price_element else "Неизвестно"
                    
                    # Наличие товара
                    inv_attr = element.get_attribute("data-product-inv")
                    is_available = int(inv_attr) > 0 if inv_attr and inv_attr.isdigit() else True
                    
                    # URL изображения
                    img_element = element.find_element(By.CSS_SELECTOR, ".js-product-img")
                    image_url = img_element.get_attribute("data-original")
                    
                    product_info = {
                        'name': name,
                        'price': price,
                        'is_available': is_available,
                        'image_url': image_url
                    }
                    
                    products.append(product_info)
                except Exception as e:
                    print(f"Ошибка при извлечении данных товара: {e}")
                    continue
                    
        except Exception as e:
            print(f"Ошибка при поиске элементов товаров: {e}")
        
        return products
        
    finally:
        # Закрытие драйвера
        driver.quit()
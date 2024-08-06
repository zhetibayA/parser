
import sqlite3
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import datetime
import requests

def update_table_price():
    try:
        models_data = cur.execute('SELECT * FROM models').fetchall()
        for row in models_data:
            model_id, brand, model = row
            vehicle_data = cur.execute('SELECT * FROM vehicle WHERE model_id = ?', (model_id,)).fetchall()
            for vehicle_row in vehicle_data:
                vehicle_id = vehicle_row[0]
                year = vehicle_row[2]
                print("Бренд:", brand, ", Model:", model, ", Год:", year)
                url = f"https://kolesa.kz/cars/{brand.lower()}/{model.lower()}/?auto-custom=2&year[from]={year}&year[to]={year}"
                driver.get(url)
                if driver.find_elements(By.CSS_SELECTOR, "h2.results__info.js__empty-search"):
                    print("Пустой поиск. Пропускаем этот год.")
                    continue
                vip_card_bodies = []
                a_card_infos = []
                data = []
                page = 1
                while True:
                    print(f"page = ", {page})
                    try:
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.vip-card__body")))                                                
                    except TimeoutException:
                        driver.refresh()
                        continue
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.a-card__info")))
                    vip_card_bodies = driver.find_elements(By.CSS_SELECTOR, "div.vip-card__body")
                    a_card_infos = driver.find_elements(By.CSS_SELECTOR, "div.a-card__info")
                    for vip_card_body in vip_card_bodies:
                        price_element = vip_card_body.find_element(By.CSS_SELECTOR, "strong.vip-card__price")
                        description_element = vip_card_body.find_element(By.CSS_SELECTOR, "p.vip-card__description")
                        price = price_element.text
                        description = description_element.text
                        data.append({"price": price, "description": description})                             
                    for a_card_info in a_card_infos:
                        price_element = a_card_info.find_element(By.CSS_SELECTOR, "span.a-card__price")
                        description_element = a_card_info.find_element(By.CSS_SELECTOR, "p.a-card__description")
                        price = price_element.text
                        description = description_element.text
                        data.append({"price": price, "description": description})
                    try:
                        current_url = driver.current_url
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.right-arrow.next_page"))).click()
                        page += 1
                        WebDriverWait(driver, 60).until(EC.url_changes(current_url))
                    except Exception as e:
                        print("Reached last page or error clicking next page!")
                        break
                unique_data = set((card['price'], card['description']) for card in data)
                data = [{'price': price, 'description': description} for price, description in unique_data]                
                prices = [card['price'] for card in data]                
                cleaned_prices = []
                for price in prices:
                    price = price.replace(' ', '')
                    for symbol in currency_symbols:
                        price = price.replace(symbol, '')                                        
                    try:
                        cleaned_price = float(price)
                        cleaned_prices.append(cleaned_price)
                    except ValueError:
                        print(f"Невозможно преобразовать цену в число: {price}")
                average_price = round(sum(cleaned_prices) / len(cleaned_prices))
                
                try:
                    cur.execute("SELECT COUNT(*) FROM price WHERE vehicle_id = ? AND date = ?", (vehicle_id, datetime.date.today()))
                    count = cur.fetchone()[0]
                    if count == 0:
                        cur.execute("INSERT INTO price (vehicle_id, avg_price, date) VALUES (?, ?, ?)", (vehicle_id, average_price, datetime.date.today()))
                        conn.commit()
                        print(f"Данные добавлены в таблицу price: id={cur.lastrowid}, vehicle_id={vehicle_id}, Средняя цена: {average_price}, Дата: {datetime.date.today()}")
                    else:
                        print("Запись с таким vehicle_id и date уже существует")
                        cur.execute("SELECT * FROM price WHERE vehicle_id = ? AND date = ?", (vehicle_id, datetime.date.today()))
                        matching_data = cur.fetchall()
                        for row in matching_data:
                            print(row)
                except Exception as e:
                    print(f"Ошибка при добавлении данных в таблицу price: {e}")
                    return True

    except Exception as e:
        print(f"Error update_table_price: {e}")

def create_database():
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY,
                brand TEXT NOT NULL,
                model TEXT NOT NULL)''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vehicle (
                id INTEGER PRIMARY KEY,
                model_id INTEGER,
                issued_at INTEGER,
                FOREIGN KEY (model_id) REFERENCES models(id))''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS price (
                id INTEGER PRIMARY KEY,
                vehicle_id INTEGER,
                avg_price REAL,
                date DATE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicle(id))''')
        conn.commit()
        print("База данных и таблицы успешно созданы!")
    except Exception as e:
        print(f"Error: {e}")
    
def add_to_models():
    while True:
        brand = input("Введите название бренда (или 'exit' для выхода): ")
        if brand.lower() == 'exit':
            break
        model = input("Введите название модели: ")
        cur.execute('''
            INSERT INTO models(brand, model) 
            SELECT ?, ? 
            WHERE NOT EXISTS (SELECT 1 FROM models WHERE brand = ? AND model = ?)
            ''', (brand, model, brand, model))
        conn.commit()
        print(f"Модель добавлена с ID: {cur.lastrowid}")
    
def update_table_vehicle():
    model_rows = cur.execute('SELECT * FROM models').fetchall()
    for row in model_rows:
        model_id, brand, model = row
        url = f"https://kolesa.kz/cars/{brand.lower()}/{model.lower()}/?auto-custom=2"
        driver.get(url)
        min_year = 1936
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "year[from]")))
        max_year = driver.find_element(By.ID, "year[from]").get_attribute("max")
        from_year_input = driver.find_element(By.ID, "year[from]")
        to_year_input = driver.find_element(By.ID, "year[to]")
        for year in range(int(max_year), int(min_year) - 1, -1):
            button_text_element = driver.find_element(By.CLASS_NAME, "js__search-form-submit-value")
            original_text = button_text_element.get_attribute("innerHTML")
            to_year_input.clear()  
            from_year_input.clear()  
            to_year_input.send_keys(str(year))
            from_year_input.send_keys(str(year))
            WebDriverWait(driver, 10).until(lambda _: button_text_element.get_attribute("innerHTML") != original_text)
            button_text = button_text_element.text
            print(f"Текст на кнопке: {button_text}")
            if "Ничего не найдено" in button_text:
                print(f"Нет моделей {year} года выпуска.")
                continue
            print(f"ID модели: {row}, год: {year}")
            cur.execute("SELECT COUNT(*) FROM vehicle WHERE model_id = ? AND issued_at = ?", (model_id, year))
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("INSERT INTO vehicle (model_id, issued_at) VALUES (?, ?)", (model_id, year))
                conn.commit()
                print(f"Данные добавлены в таблицу vehicle: id={cur.lastrowid}, model_id={model_id}, issued_at={year}")
            else:
                print("Запись уже существует в таблице vehicle.")
    print("Процесс обновления таблицы vehicle завершен.")

def get_brands_and_models():
    url = "https://kolesa.kz/cars/"
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "filter-button"))).click()
        brand_elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "filter-button__label")))
        brands = [element.text.strip() for element in brand_elements[6:]]
        
        brand_index = 6
        all_brands = []
        all_models = []

        while brand_index < len(brand_elements):
            current_brand = brand_elements[brand_index]
            print("Текст кнопки(бренд):", current_brand.text)
            current_brand.click()

            elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "filter-button__label")))
            indices_to_try = [7, 6, 5]
            for index in indices_to_try:
                try:
                    more_models = elements[index]
                    print("Текст кнопки 2:", more_models.text, "\n Индекс:", index)
                    more_models.click()

                    model_elements = WebDriverWait(driver, 10).until(
                        EC.visibility_of_all_elements_located((By.CLASS_NAME, "grouped-list__group"))
                    )

                    model_list = [element.text.strip()[1:] for element in model_elements]
                    models = [model.lower().replace(' ', '-') for model in model_list if model]

                    print("Модели:", models)
                    all_brands.append(current_brand.text.strip())
                    all_models.append(models)

                except TimeoutException:
                    continue

            brand_index += 1
            more_models.click()
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "filter-button"))).click()

        return all_brands, all_models

    except Exception as e:
        print(f"Error get_brands_and_models: {e}")
        return None



def get_models(brand_id):
    cookies = {
        'ssaid': 'a30f1380-f24a-11ee-a7d7-47636a3fe226',
        '_ga': 'GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226',
        'klssid': 'qt1cch1lv3hhoj26fakos2c751',
        '_ym_uid': '1715761456907778536',
        '_ym_d': '1715761456',
        'kl_cdn_host': '//alakcell-kz.kcdn.online',
        '__tld__': 'null',
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'app-language': 'ru',
        'app-platform': 'frontend',
        'cache-control': 'no-cache',
        # 'cookie': 'ssaid=a30f1380-f24a-11ee-a7d7-47636a3fe226; _ga=GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226; klssid=qt1cch1lv3hhoj26fakos2c751; _ym_uid=1715761456907778536; _ym_d=1715761456; kl_cdn_host=//alakcell-kz.kcdn.online; __tld__=null',
        'origin': 'https://kolesa.kz',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://kolesa.kz/',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    params={
        'markId': brand_id,
    }
    response = requests.get('https://app.kolesa.kz/v2/filter/models', params=params, cookies=cookies, headers=headers)
    return response.json()

def get_brands():
    cookies = {
        'ssaid': 'a30f1380-f24a-11ee-a7d7-47636a3fe226',
        '_ga': 'GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226',
        'klssid': 'qt1cch1lv3hhoj26fakos2c751',
        '_ym_uid': '1715761456907778536',
        '_ym_d': '1715761456',
        '__tld__': 'null',
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'app-language': 'ru',
        'app-platform': 'frontend',
        'cache-control': 'no-cache',
        # 'cookie': 'ssaid=a30f1380-f24a-11ee-a7d7-47636a3fe226; _ga=GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226; klssid=qt1cch1lv3hhoj26fakos2c751; _ym_uid=1715761456907778536; _ym_d=1715761456; __tld__=null',
        'origin': 'https://kolesa.kz',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://kolesa.kz/',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    params = {
        'iconsV2': 'true',
    }
    response = requests.get('https://app.kolesa.kz/v2/filter/marks', params=params, cookies=cookies, headers=headers)
    return response.json()

def update_table_models():
    brands_data = get_brands()
    if not brands_data:
        print("Нет брендов")
        return
    x = 0
    for brand in brands_data['items']:
        brand_id = brand['id']
        brand_name = brand['urlAlias']
        print(f"Brand ID: {brand_id}, Brand Name: {brand_name}")
        models_data = get_models(brand_id)
        if not models_data:
            print("Нет моделей")
            continue
        for model in models_data['items']:
            model_name = model['urlAlias']
            print(f"Brand: {brand_name}, Model Name: {model_name}")
        x += 1
        if x > 3:
            return

if __name__ == "__main__": 
    chromedriver_path = 'C:\\Users\\alibek\\Desktop\\Projects\\kolesa\\alibek\\chromedriver.exe'
    user_agent = UserAgent()
    random_user_agent = user_agent.random
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={random_user_agent}")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--headless')
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    conn = sqlite3.connect('testcar.db')
    cur = conn.cursor()    
    currency_symbols = ['₸', '$', '€', '£', '¥', '₽']

    update_table_models()

    if conn:
        conn.close()
    if driver:
        driver.quit()
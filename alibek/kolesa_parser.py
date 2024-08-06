import random
import sqlite3
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import datetime
import requests
import logging

logging.basicConfig(filename='report.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

def update_table_price():
    try:
        models_data = cur.execute('SELECT * FROM models').fetchall()
        for row in models_data:
            model_id, brand, model = row
            vehicle_data = cur.execute('SELECT * FROM vehicle WHERE model_id = ?', (model_id,)).fetchall()
            for vehicle_row in vehicle_data:
                vehicle_id = vehicle_row[0]
                year = vehicle_row[2]
                logger.info("Brend:", brand, ", Model:", model, ", Year:", year)
                url = f"https://kolesa.kz/cars/{brand.lower()}/{model.lower()}/?auto-custom=2&year[from]={year}&year[to]={year}"
                time.sleep(delay)
                driver.get(url)
                if driver.find_elements(By.CSS_SELECTOR, "h2.results__info.js__empty-search"):
                    logger.info(f"this model is not available to buy.")
                    continue
                vip_card_bodies = []
                a_card_infos = []
                data = []
                page = 1
                logger.info(f"price data collection started.")
                while True:
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
                        time.sleep(delay)
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.right-arrow.next_page"))).click()
                        page += 1
                        WebDriverWait(driver, 60).until(EC.url_changes(current_url))
                    except Exception as e:
                        logger.info("Reached last page.")
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
                        logger.warning(f"Impossible to convert price to a number: {price}")
                average_price = round(sum(cleaned_prices) / len(cleaned_prices))
                try:
                    cur.execute("SELECT COUNT(*) FROM price WHERE vehicle_id = ? AND date = ?", (vehicle_id, datetime.date.today()))
                    count = cur.fetchone()[0]
                    if count == 0:
                        cur.execute("INSERT INTO price (vehicle_id, avg_price, date) VALUES (?, ?, ?)", (vehicle_id, average_price, datetime.date.today()))
                        conn.commit()
                        logger.info(f"Data added to the table price: vehicle_id={vehicle_id}, Средняя цена: {average_price}, Дата: {datetime.date.today()}")
                    else:
                        logger.info("A table row with this vehicle_id and date already exists")
                        cur.execute("SELECT * FROM price WHERE vehicle_id = ? AND date = ?", (vehicle_id, datetime.date.today()))
                        matching_data = cur.fetchall()
                        for row in matching_data:
                            logger.info(row)
                except Exception as e:
                    logger.error(f"Error when adding data to the price table: {e}")
                    return True
    except Exception as e:
        logger.error(f"Error in update_table_price: {e}")

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
        logger.info("Database ready!")
    except Exception as e:
        logger.error(f"Error in create_database: {e}")
    
def update_table_vehicle():
    model_rows = cur.execute('SELECT * FROM models').fetchall()
    min_year = 1936
    max_year = datetime.datetime.now().year
    cookies = {
        'ssaid': 'a30f1380-f24a-11ee-a7d7-47636a3fe226',
        '_ga': 'GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226',
        'klssid': 'qt1cch1lv3hhoj26fakos2c751',
        '_ym_uid': '1715761456907778536',
        '_ym_d': '1715761456',
        'kl_cdn_host': '//alakt-kz.kcdn.online',
        '__tld__': 'null',
    }
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'app-language': 'ru',
        'cache-control': 'no-cache',
        # 'cookie': 'ssaid=a30f1380-f24a-11ee-a7d7-47636a3fe226; _ga=GA1.2.a30f1380-f24a-11ee-a7d7-47636a3fe226; klssid=qt1cch1lv3hhoj26fakos2c751; _ym_uid=1715761456907778536; _ym_d=1715761456; kl_cdn_host=//alakt-kz.kcdn.online; __tld__=null',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://kolesa.kz/',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': random_user_agent,
        'x-kl-kfa-ajax-request': 'Ajax_Request',
        'x-requested-with': 'XMLHttpRequest',
    }
    for row in model_rows:
        model_id, brand, model = row
        for year in range(int(max_year), int(min_year) - 1, -1):
            time.sleep(delay)
            response = requests.get(
                f'https://kolesa.kz/a/ajax-get-search-nb-results/cars/{brand.lower()}/{model.lower()}/',
                params={'year[from]': year, 'year[to]': year,},
                cookies=cookies,
                headers=headers,
            )
            cars_num = response.json().get('nbCnt')
            logger.info(f"There are {cars_num} models")
            if cars_num == 0:
                continue
            logger.info(f"Model ID: {row}, Year: {year}")
            cur.execute("SELECT COUNT(*) FROM vehicle WHERE model_id = ? AND issued_at = ?", (model_id, year))
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("INSERT INTO vehicle (model_id, issued_at) VALUES (?, ?)", (model_id, year))
                conn.commit()
                logger.info(f"Data added to the vehicle table.")
            else:
                logger.info("This data already exists in the vehicle table.")

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
        'user-agent': random_user_agent,
    }
    params={
        'markId': brand_id,
    }
    response = requests.get('https://app.kolesa.kz/v2/filter/models', params=params, cookies=cookies, headers=headers)
    logger.info("get_models response:", response.json())
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
        'user-agent': random_user_agent,
    }
    params = {
        'iconsV2': 'true',
    }
    response = requests.get('https://app.kolesa.kz/v2/filter/marks', params=params, cookies=cookies, headers=headers)
    return response.json()

def update_table_models():
    brands_data = get_brands()
    if not brands_data:
        logger.warning("No brends??")
        return
    for brand in brands_data['items']:
        brand_id = brand['id']
        brand_name = brand['urlAlias']
        time.sleep(delay)
        models_data = get_models(brand_id)
        if not models_data:
            logger.warning(f"No models for brend {brand_name}...")
            continue
        for model in models_data['items']:
            model_name = model['urlAlias']
            cur.execute("SELECT COUNT(*) FROM models WHERE brand = ? AND model = ?", (brand_name, model_name))
            count = cur.fetchone()[0]
            if count == 0:
                cur.execute("INSERT INTO models (brand, model) VALUES (?, ?)", (brand_name, model_name))
                conn.commit()
                logger.info(f"{brand_name} {model_name} added to database successfully")
            else:
                logger.info(f"{brand_name} {model_name} already exists in database")

if __name__ == "__main__": 
    logger.info(f"Preparation start.")
    # chromedriver_path = 'C:\\Users\\alibek\\Desktop\\Projects\\kolesa\\alibek\\chromedriver.exe'
    chromedriver_path = "chromedriver.exe"
    user_agent = UserAgent()
    random_user_agent = user_agent.random
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-agent={random_user_agent}")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--headless')
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    conn = sqlite3.connect('kolesa.db')
    cur = conn.cursor()    
    currency_symbols = ['₸', '$', '€', '£', '¥', '₽']
    delay = random.uniform(1, 5)
    create_database()
    logger.info("Start updating models table in database.")
    # update_table_models()
    logger.info("Start updating vehicle table in database.")
    update_table_vehicle()
    logger.info("Start updating price table in database.")
    update_table_price()
    logger.info("End.")
    if conn:
        conn.close()
    if driver:
        driver.quit()
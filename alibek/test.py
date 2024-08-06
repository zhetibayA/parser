import requests
import datetime

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
    'markId': 34,
}
response = requests.get('https://app.kolesa.kz/v2/filter/models', params=params, cookies=cookies, headers=headers)
print(response.json())
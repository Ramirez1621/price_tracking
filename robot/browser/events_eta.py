import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests
from os.path import join
from bs4 import BeautifulSoup
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import ETA_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["rebajas", "sostenibilidad", "ver todo", "regalos"]
CATEGORY_IDS = {"MUJERES":101, "HOMBRES":102, "INFANTIL":104, "CALZADO":105} #[{"MUJERES":101}, {"HOMBRES":102}, {"INFANTIL":104}, {"CALZADO":105}] # mujer: 101, hombre: 102, infantil: 103, calzado: 105

class etaSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            # driver_hm = open_browser()
            # with WebDriver(driver_bershka) as driver:
            time.sleep(5)
            self.select_categories()
            
            end = time.time()
            logging.info(f"Excution EtaFashion Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_ETA.csv"), index=False)

    def open_page(self, page, category_id, color_code):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
            url = f"https://www.etafashion.com//es_EC/product-search/{category_id}/category?q=%3Amodifiedtime:swatchColors:{color_code}&page={page}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                html_code = BeautifulSoup(response.text, 'html.parser')

                return html_code
            else:
                return ""
        except Exception as e:
            logging.error(
                (f"EtaFashion An error has ocurred during report selection: {type(e)}"))
            raise(e)
        
    def get_colors(self, name, id):
        url = f"https://www.etafashion.com/{name}/es_EC/c/{id}"

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            html_code = BeautifulSoup(response.text, 'html.parser')
            color_list = html_code.find('ul', id='Color')

            colors = list()
            for color in color_list.find_all('li'):
                color_code = color.find('input', type='checkbox')
                if color_code is None:
                    continue
                color_code = color_code.get("data-facet-code")

                color_name = color.find('img')
                color_name = color_name.get("title")

                
                colors.append({"name": color_name, "code": color_code})
            return colors
        else:
            return []
# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try:
            for name, id in CATEGORY_IDS.items():

                colors_code = self.get_colors(name, id)

                for color in colors_code:
                    page_number = 0
                    while True:
                        # https://www.etafashion.com//es_EC/product-search/101/category?q=%3Amodifiedtime&page=2
                        html_code = self.open_page(page = page_number, category_id=id, color_code=color["code"])

                        raw_data = html_code.find_all('a', class_='name')
                        url_items = [item.get("href", "") for item in raw_data]
                        
                        url_items = list(set(url_items))

                        if len(url_items):
                            self.get_items(url_items, color["name"])
                            page_number += 1
                        else:
                            break
            # url_items = list()
            
            # for item in items_data:
            #     url = item.get("url")
            #     url_items.append(url)
        
            
        except Exception as e:
            logging.error(
                (f"EtaFashion An error has ocurred during scan categories"))
            logging.error(
                (f"details: {e}"))

    def get_items(self, url_items, color_name):
        try:
            for i, url in enumerate(url_items):
                
                complete_url = f"{ETA_URL}{url}"

                duplicate_flag = [True for record in self.records if complete_url == record["url item"]]
                if len(duplicate_flag):
                    continue
                
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
                
                item_raw = requests.get(complete_url, headers=headers)

                html_item = BeautifulSoup(item_raw.text, 'html.parser')
                

                if len(html_item):
                    count_product = f"{int(i+1/len(url_items))}"
                    self.get_product_details(count_product, html_item, complete_url, color_name)


        except Exception as e:
            logging.error(
                (f"EtaFashion An error has ocurred during scan subcategories"))
            logging.error(
                (f"details: {e}"))
        

# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

# ------------------------------------------------------------------------------------------------ #
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item, href, color_name, category = None, subcategory = None, subcategory_2 = None, subcategory_3 = None):
        try:    
                # usar beautiful soap para extraer toda la info del producto
                start = time.time()

                categories_comp = item.find('ol', class_="breadcrumb")
                categories_comp = categories_comp.find_all('li')
                categories = [ c.text.replace("\n","").strip() for c in categories_comp]
                categories.pop(0)
                
                name = categories.pop(-1)

                category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]

                sku = item.find('span', class_="code")
                sku = sku.text

                color = color_name

                marca = "EtaFashion"

                image_url = item.find('img', class_="lazyOwl")
                image_url = image_url["data-src"]
                image = f"{ETA_URL}{image_url}"

                made_in = None
                
                # ------------------------------------- descripción ----------------------------------------------------------- #

                item_characteristics = ""

                _composition_details = item.find('div', class_="tab-details")
                composition = _composition_details.find('p')
                composition_details = composition.prettify()

                item_characteristics += composition_details

                _composition = item.find('div', class_="description")
                composition_items = _composition.find_all('li')

                composition_description = [comp.text for comp in composition_items]
                
                item_characteristics += ", ".join(composition_description)
                item_characteristics = item_characteristics.replace("\n","").replace("<p>","").strip()
                item_characteristics = re.sub('<[^<]+?>', '|', item_characteristics)
                

                patron = r'\b(?:Composici[oó]n|Tela|\d+%).*?$'
                # patron_2 = r'(\b\d+% )?(algod[oó]n|elastano|poliéster|cuero)\b'
                # patron_2 = r'\b(?:Pa[ií]s de Origen).*?</li>'

                # materials = [re.findall(patron, comp, re.IGNORECASE) for comp in composition_details]

                materials = [re.findall(patron, comp, re.IGNORECASE) for comp in composition_description]
                materials = [m[0] for m in materials if len(m)]
                materials = ".".join(materials) if len(materials) else None

                # ------------------------------------------------------------------------------------------------ #
                #                                              precio                                              #
                # ------------------------------------------------------------------------------------------------ #
                prices = item.find('div', class_="price")

                if prices is not None:

                    sale_price = prices.find('span', class_="priceDiscountDetails")
                    sale_price_value = sale_price.text.strip("$").replace(",", ".")
                    final_price = sale_price_value

                    price = prices.find('span', class_="priceOldDetails")
                    price_value = price.text.strip("$").replace(",", ".")
                    saving_value = f"-{round(100-float(sale_price_value)*100/float(price_value))}%"

                else:
                    prices = item.find('p', class_="price")
                    price_value = prices.text.replace("\n","").strip().strip("$").replace(",", ".")
                    final_price = price_value
                    sale_price_value, saving_value = None, None
                

                sizes = item.find_all('option')
                
                for size in sizes:
                    size_value = size.text.replace("\n","").strip()
                    stock = "available"
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "EtaFashion Ecuador",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": marca,
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size_value}",
                                "item": name,
                                "item_characteristics": item_characteristics,
                                "url sku": ETA_URL,
                                "image": image,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_etafashion_ec",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size_value,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": materials,
                                "made_in": made_in,
                                "url item": href,
                            }
                        )
                print(f"EtaFashion {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"EtaFashion...Error get product details {category} {subcategory} {subcategory_2}: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
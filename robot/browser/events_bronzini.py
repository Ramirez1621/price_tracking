import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import BRONZINI_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class bronziniSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
                # driver_bershka = open_browser()
                # with WebDriver(driver_bershka) as driver:
                # self.open_page(driver_bershka)
            time.sleep(5)

            self.select_categories()
                # driver_bershka.quit()
                
            end = time.time()
            logging.info(f"Excution Bershka Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_BRONZINI.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=BRONZINI_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try: 
            url_category = 'https://www.exito.com/api/graphql'

            page = 0
            while True:
                params = {"operationName":"ProductsQuery","variables": r'{"first":16,"after":"%s","sort":"score_desc","term":"bronzini","selectedFacets":[{"key":"brand","value":"bronzini"},{"key":"brand","value":"bronzini-active"},{"key":"brand","value":"bronzini-woman"},{"key":"channel","value":"{\"salesChannel\":1,\"regionId\":\"\"}"},{"key":"locale","value":"es-CO"}]}' % page}
                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                
                response = requests.get(url_category, headers=headers, params=params)
                # response.raise_for_status()

                if response.status_code == 200:
                    data = json.loads(response.content)
                    items = data['data'].get('search').get('products').get('edges')
                    # for i in data:
                    #     _ = i["carouselItems"]
                    #     _ = [ id["tipology"] for id in _]
                    
                    self.get_products(items)
                    page += 1
                
                elif response.status_code == 500:
                    data = json.loads(response.content)
                    error = data.get("errors")[0].get("message")
                    if "something went wrong" in error:
                        break

        
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category..."))
            logging.error(
                (f"details: {e}"))

    def scan_subcategories(self, category_ids):
        try:
            for category_id in category_ids:
                url_category = f"https://www.bershka.com/itxrest/3/catalog/store/45109565/40259551/category/{category_id}/product?showProducts=false&showNoStock=false&languageId=-5"

                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
                response = requests.get(url_category, headers=headers)
                # response.raise_for_status()

                if response.status_code == 200:
                    data = json.loads(response.content)
                    ids = data["productIds"]

                    if len(ids) < 200:
                        url_item= f"https://www.bershka.com/itxrest/3/catalog/store/45109565/40259551/productsArray"

                        params = {"languageId":-5, "showProducts": "false", "appId":1, "productIds": ids, "categoryId": category_id}
                        headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                        
                        response = requests.get(url_item, headers=headers, params=params)
                        # response.raise_for_status()
                        
                        if response.status_code == 200:
                            list_products = json.loads(response.content)

                            self.get_products(list_products["products"])
                            time.sleep(2)
                    elif len(ids) >= 200:
                        url_item= f"https://www.bershka.com/itxrest/3/catalog/store/45109565/40259551/productsArray"

                        batch = round(len(ids)/2)
                        params = {"languageId":-5, "showProducts": "false", "appId":1, "productIds": ids[:batch], "categoryId": category_id}
                        headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                        
                        response = requests.get(url_item, headers=headers, params=params)
                        # response.raise_for_status()
                        
                        if response.status_code == 200:
                            list_products = json.loads(response.content)

                            self.get_products(list_products["products"])
                            time.sleep(2)
                        
                        params = {"languageId":-5, "showProducts": "false", "appId":1, "productIds": ids[batch:], "categoryId": category_id}
                        
                        response = requests.get(url_item, headers=headers, params=params)
                        # response.raise_for_status()
                        
                        if response.status_code == 200:
                            list_products = json.loads(response.content)

                            self.get_products(list_products["products"])
                            time.sleep(2)


        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategories..."))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #

# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, items):
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            self.get_product_details(count_product, item.get('node'))


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item):
        try:
                # https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category/0/product/593527439/detail?languageId=-5&appId=1
                time.sleep(0.2)
                start = time.time()

                item_name = item.get("items")[0].get("complementName")

                color = item.get("items")[0].get("Color")[0] if item.get("items")[0].get("Color") is not None else None
                # https://www.exito.com/camiseta-t-shirt-mc-linea-462650/p?color=Gris
                href = item.get("slug")
                href = f"https://www.exito.com/{href}/p?color={color}"
                    
                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:

                

                if len(duplicate_flag):
                    return
                
                sku = item.get("sku")
                marca = item.get('brand').get('name')

                categories = item.get("breadcrumbList").get('itemListElement')

                if len(categories) >= 4:
                    category, subcategory, subcategory_2, subcategory_3 = categories[0].get('name'), categories[1].get('name'), categories[2].get('name'), None
                elif len(categories) == 3:
                    category, subcategory, subcategory_2, subcategory_3 = categories[0].get('name'), categories[1].get('name'), None, None
                elif len(categories) == 2:
                    category, subcategory, subcategory_2, subcategory_3 = categories[0].get('name'), None, None, None
                else:
                    category, subcategory, subcategory_2, subcategory_3 = None, None, None, None
        
                if category == None:
                    return


                item_details = item.get("properties")
                
                # ------------------------------------- descripción ----------------------------------------------------------- #
                description = ""
                materials = ""
                cares = ""
                for detail in item_details:
                    if not "Instrucciones de cuidado" in detail.get("name") and not "Composición" in detail.get("name") and not "Guía de tallas" in detail.get("name"):
                        description += f'{detail.get("name")}: {detail.get("values")[0]} | '
                    elif "Instrucciones de cuidado" in detail.get("name"):
                        cares += detail.get("values")[0]
                    elif "Composición" in detail.get("name"):
                        materials += detail.get("values")[0]
                    

                materials = materials.replace("\n", "")
                cares = cares.replace("\n", "")
                description = description.replace("\n", "")
                item_characteristics = f"{description} || Composición: {materials} || Cuidados: {cares}"

                # ------------------------------------------------------------------------------------------------ #
                    #                                              prices                                              #
                    # ------------------------------------------------------------------------------------------------ #
                price = item.get("offers").get("offers")[0]
                
                price_value = int(int(price.get("listPrice")))
                final_price = price_value

                sale_price_value = price.get("price")

                if sale_price_value < price_value:
                    final_price = sale_price_value
                    saving_value = f"-{round(100-sale_price_value*100/price_value)}%"

                else:
                    sale_price_value, saving_value = None, None

                image_url = item.get("image")[0].get("url")
                made_in = None

                for detail in item.get("items"):

                    size_value = detail.get("Talla")[0] if detail.get("Talla") is not None else None
                    stock = "available"
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Bronzini Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": marca,
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size_value}",
                                "item": item_name,
                                "item_characteristics": item_characteristics,
                                "url sku": BRONZINI_URL,
                                "image": image_url,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_bronzini_col",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size_value,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": materials,
                                "made_in": made_in,
                                "url item":href,
                            }
                        )
                
                print(f"Bronzini {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s") 
        except Exception as e:
            print(e)
            logging.error(f"Bronzini...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
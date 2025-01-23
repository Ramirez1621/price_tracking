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
from settings import MASSIMO_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class massimoSession():
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
            logging.info(f"Excution Massimo Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_MASSIMO.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=MASSIMO_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try: 
            consult_date = dt.datetime.now().strftime("%Y%m%d")
            url_category = f"https://www.massimodutti.com/itxrest/2/catalog/store/35009515/30359526/category?languageId=-5&typeCatalog=1&appId=1"

            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
            response = requests.get(url_category, headers=headers)
            # response.raise_for_status()

            if response.status_code == 200:
                data = json.loads(response.content)
                category_ids = list()
                for i in data["categories"]:
                    subcategories = i["subcategories"]

                    for subcategory in subcategories:
                        sub_subcategories = subcategory.get("subcategories")
                        if len(sub_subcategories):
                            _ = [ id["id"] for id in sub_subcategories]
                            category_ids.extend(_)
                        else:
                            category_ids.append(subcategory["id"])
                    
                
                self.scan_subcategories(category_ids)

        
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category..."))
            logging.error(
                (f"details: {e}"))

    def scan_subcategories(self, category_ids):
        try:
            for category_id in category_ids:
                url_category = f"https://www.massimodutti.com/itxrest/3/catalog/store/35009515/30359526/category/{category_id}/product?languageId=-5&appId=1&showProducts=false"

                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
                response = requests.get(url_category, headers=headers)
                # response.raise_for_status()

                if response.status_code == 200:
                    data = json.loads(response.content)
                    ids = data["productIds"]

                    if len(ids) < 200:
                        url_item= f"https://www.massimodutti.com/itxrest/3/catalog/store/35009515/30359526/productsArray"

                        params = {"languageId":-5, "showProducts": "false", "appId":1, "productIds": ids, "categoryId": category_id}
                        headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                        
                        response = requests.get(url_item, headers=headers, params=params)
                        # response.raise_for_status()
                        
                        if response.status_code == 200:
                            list_products = json.loads(response.content)

                            self.get_products(list_products["products"])
                            time.sleep(2)
                    elif len(ids) >= 200:
                        url_item= f"https://www.massimodutti.com/itxrest/3/catalog/store/35009515/30359526/productsArray"

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
            self.get_product_details(count_product, item)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item):
        try:
                # https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category/0/product/593527439/detail?languageId=-5&appId=1
                time.sleep(0.2)
                start = time.time()
                category_dict = {"WOMEN": "Mujer", "MEN":"Hombre"}
                item_name = item.get("name")

                href = item.get("productUrl")
                href = f"https://www.massimodutti.com/co/{href}"
                    
                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
                if len(duplicate_flag):
                    return

                category = item.get("sectionNameEN")
                
                if category == None:
                    return
                category = category_dict.get(category)

                subcategory_2 = item.get("familyName")
                subcategory_3 = item.get("subFamilyName")
                

                categories = []
                for c in item.get("relatedCategories"):
                    if c["name"] not in categories and not "ver todo" in c["name"].lower() and not "lo más vendido" in c["name"].lower() and not "hasta" in c["name"].lower() and not "probador" in c["name"].lower() and not "special prices" in c["name"].lower():
                        categories.append(c["name"])

                
                # categories = [c["name"] for c in item.get("relatedCategories") if not "ver todo" in c["name"].lower() and not "lo más vendido" in c["name"].lower()]
                # categories = list(set(categories))
                if len(categories) >= 1:
                    subcategory = categories[0]
                else:
                    subcategory = subcategory_2
                    subcategory_2 = subcategory_3

                if subcategory_2 is None and len(categories) > 2:
                    subcategory_2 = item.get("relatedCategories")[-2]["name"]
                
                # if subcategory_3 is None and not len(categories):
                #     subcategory_3 = None
                # else:
                #     subcategory_3 = categories[-1]

                item_details = item.get("bundleProductSummaries")[0]
                
                sku = item_details.get("detail").get("reference")

                marca = "Massimo Dutti"
                
                # ------------------------------------- descripción ----------------------------------------------------------- #
                
                composition_items = item_details.get("detail").get("composition")

                """
                part 3 = interior

                part 2 = Forro

                part 1 = Exterior"""


                materials = "Exterior: "
                for comp in composition_items:
                    material_name = comp.get("composition")[0].get("name")
                    material_percentage = comp.get("composition")[0].get("percentage")
                    materials += f"{material_name} {material_percentage}%, " 


                cares_items = item_details.get("detail").get("care")

                cares = [care.get("description") for care in cares_items]

                cares = ', '.join(cares)
                
                description_items = item_details.get("attributes")

                description = [des.get("value") for des in description_items if "DESCRIPTION" in des.get("type")]

                description = ', '.join(description)

                materials = materials.replace("\n", "")
                cares = cares.replace("\n", "")
                description = description.replace("\n", "")
                item_characteristics = f"Descripción: {description} || Composición: {materials} || Cuidados: {cares}"

                for detail in item_details.get("detail").get("colors"):

                    image = detail.get("image").get("url")
                    # timestamp = detail.get("image").get("timestamp")
                    # https://static.bershka.net/4/photos2/2024/V/1/2/p/2422/360/001/2422360001_1_1_0.jpg?imwidth=:width:&ts=1706689007491
                    image_url = f"https://static.massimodutti.net/3/photos{image}_2_6_16.jpg?imwidth=:width"
                    # Execute the command for make apear the detail bar
                    color = detail.get("name")

                    sizes = detail.get("sizes")
                    for size in sizes:

                        made_in = None
                        # ------------------------------------------------------------------------------------------------ #
                        #                                              prices                                              #
                        # ------------------------------------------------------------------------------------------------ #
                        price = size.get("price")
                        
                        price_value = int(int(price)/100)
                        final_price = price_value

                        sale_price = size.get("oldPrice")

                        if sale_price is not None:
                            sale_price_value = price_value
                            final_price = price_value
                            price_value = int(int(sale_price)/100)
                            saving_value = f"-{round(100-sale_price_value*100/price_value)}%"

                        else:
                            sale_price_value, saving_value = None, None

                        size_value = size.get("name")
                        stock = size.get("visibilityValue")
                        stock = "available" if stock == "SHOW" else "not available"
                        # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                        self.records.append(
                                {
                                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                    "canal": "Massimo Dutti Colombia",
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
                                    "url sku": MASSIMO_URL,
                                    "image": image_url,
                                    "price": price_value,
                                    "sale_price": sale_price_value,
                                    "shipment cost": stock,
                                    "sales flag": saving_value,
                                    "store id": f"9999_massimodutti_col",
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
                
                print(f"Massimo {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s") 
        except Exception as e:
            print(e)
            logging.error(f"Bershka...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
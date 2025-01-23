import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests
import threading

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import PULLBEAR_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class pullbearSession():
    def __init__(self):
        self.records = list()
        self.semaphore = threading.Semaphore(20)
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            # driver_pullbear= open_browser()
            # with WebDriver(driver_bershka) as driver:
            # self.open_page(driver_pullbear)
            time.sleep(5)
            self.select_categories()
            # driver_pullbear.quit()
            
            end = time.time()
            logging.info(f"Excution Pull&Bear Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_PULLBEAR.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=PULLBEAR_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try: 
            # categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            #             (By.XPATH, "//li[contains(@class,'category level-2') and contains(@class,'has-subitems')]")))
            
            # categories = [{"name": c.get_attribute("innerText"), "object":c} for c in categories]

            url_category = "https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category?languageId=-5&typeCatalog=1&appId=1"

            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
            response = requests.get(url_category, headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                data = json.loads(response.content)
                category_ids = list()
                for i in data["categories"]:
                    _ = i["subcategories"]
                    _ = [ id["id"] for id in _]
                    category_ids.extend(_)
                
                self.scan_items(category_ids)
                    
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def scan_items(self, category_ids):
        try:
            for subcategory_id in category_ids:
                url_category = f"https://www.pullandbear.com/itxrest/3/catalog/store/25009465/20309430/category/{subcategory_id}/product?languageId=-5&showProducts=false&appId=1"
                # params = {"languageId":-5, "showProducts": "false", "appId":1}
                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                
                response = requests.get(url_category, headers=headers)
                response.raise_for_status()

                if response.status_code == 200:
                    data = json.loads(response.content)
                    ids = data["productIds"]
                    self.get_products(ids)
                    
                # driver.get(subcategory["href"])

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory2"))
            logging.error(
                (f"details: {e}"))
# ------------------------------------------------------------------------------------------------ #
            
# ------------------------------------------------------------------------------------------------ #
    def pagination_items(self, driver):
        
        items = list()
        time.sleep(3)
        while True:
            _items = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//legacy-product")))

            _items = [c.get_attribute("cc-id") for c in _items if not c.get_attribute("cc-id") in items]

            items.extend(_items)
            
            time.sleep(2)
            scroll_position = driver.execute_script("return window.scrollY+document.documentElement.clientHeight;")
            scroll_end = driver.execute_script("return document.body.scrollHeight;")

            if scroll_position != scroll_end:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            else:
                break

        print(len(items))
        return items
            
# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, items):
        threads = list()
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            # self.get_product_details(count_product, item)
            thread = threading.Thread(target=self.get_product_details, args=([count_product, item]))
            threads.append(thread)
            thread.start()
            time.sleep(0.3) 

        for thread in threads:
            thread.join() 
            


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item):
        with self.semaphore:
            try:
                    # https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category/0/product/593527439/detail?languageId=-5&appId=1
                    
                    start = time.time()

                    url_item= f"https://www.pullandbear.com/itxrest/2/catalog/store/25009465/20309430/category/0/product/{item}/detail?languageId=-5&appId=1"
                    # params = {"languageId":-5, "showProducts": "false", "appId":1}
                    headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                    
                    response = requests.get(url_item, headers=headers)
                    response.raise_for_status()
                    
                    if response.status_code == 200:
                        data = json.loads(response.content)
                    
                        name = data.get("name")

                        href = data.get("productUrl")
                        href = f"https://www.pullandbear.com/co/{href}"
                        
                        duplicate_flag = [True for record in self.records if href == record["url item"]]
                    # for record in self.records:
                        if len(duplicate_flag):
                            return

                        category = data.get("sectionNameEN")

                        if category is None:
                            return

                        subcategory = data.get("bundleProductSummaries")

                        if len(subcategory):
                            subcategory = subcategory[0].get("relatedCategories")
                            if not len(subcategory):
                                subcategory = data.get("relatedCategories")[-1].get("name") if len(data.get("relatedCategories")) else None
                            else:
                                subcategory = subcategory[0].get("name")
                        else:
                            subcategory = data.get("familyName")
                        
                        

                        subcategory_2 = data.get("familyName")

                        subcategory_3 = data.get("subFamilyName")

                        item_details = data.get("bundleProductSummaries")
                        
                        if not len(item_details):
                            item_details = data
                        else:
                            item_details = item_details[0]
                        
                        sku = item_details.get("detail").get("reference")

                        marca = "Pull&Bear"
                        
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

                        made_in = None
                        
                        description = item_details.get("detail").get("longDescription")

                        item_characteristics = f"Descripción: {description} || Composición: {materials} || Cuidados: {cares}"

                        for detail in item_details.get("detail").get("colors"):

                            image = detail.get("image").get("url")
                            timestap = detail.get("image").get("timestamp")
                            image_url = f"https://static.pullandbear.net/2/photos{image}_2_1_8.jpg?t={timestap}"
                            # Execute the command for make apear the detail bar
                            color = detail.get("name")

                            sizes = detail.get("sizes")
                            for size in sizes:
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
                                            "canal": "Pull&Bear Colombia",
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
                                            "url sku": PULLBEAR_URL,
                                            "image": image_url,
                                            "price": price_value,
                                            "sale_price": sale_price_value,
                                            "shipment cost": stock,
                                            "sales flag": saving_value,
                                            "store id": f"9999_pull&bear_col",
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
                        print(f"Pull&Bear {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
                
                    time.sleep(0.2)   
            except Exception as e:
                print(e)
                logging.error(f"Pull&Bear...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
                logging.info("Refresh page...")
                # driver.refresh()
                raise(e)
import logging
import datetime as dt
import time
import json
import pandas as pd

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import NAFNAF_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser


class nafnafSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_nafnaf = open_browser()
            with WebDriver(driver_nafnaf) as driver:
                self.open_page(driver)
                self.select_categories(driver)

            end = time.time()
            logging.info(f"Excution NAFNAF Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_NAFNAF.csv"), index=False)
        # return self.records

    def open_page(self, driver: Firefox):
        try:
            driver.get(url=NAFNAF_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)


    def select_categories(self, driver: Firefox):
        try:
            categorie_clothing = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(text(),'ROPA')]")))
            
            categorie_complements = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(text(),'COMPLEMENTOS')]")))
            
            categories = [c.get_attribute("href") for c in [categorie_clothing, categorie_complements]]
            for category in categories:
                try:
                    # Get and click on category button
                    driver.get(category)
                    
                    self.select_subcategory(driver)
                except Exception as e:
                    logging.error(f"An error ocurred: {e}")
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during report selection: {e}"))
            raise(e)

    def select_subcategory(self, driver: Firefox):
        start = time.time()
        end = 0
        items = list()
        while (end - start) < 800:
            try:
                
                scroll = WebDriverWait(driver, 5).until(EC.visibility_of_element_located(
                        (By.XPATH, "//div[contains(@class,'vtex-search-result-3-x-buttonShowMore')]//a")))
                
                driver.execute_script("arguments[0].scrollIntoView()-arguments[0].scrollIntoView()*0.05;", scroll)
                time.sleep(1)

                products = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class,'vtex-flex-layout-0-x-flexRowContent--search-products-gallery items-stretch')]//script")))
                content = products.get_attribute("innerText")
                content = json.loads(content)
                _items = [c["item"]  for c in content["itemListElement"] if not c["item"] in items]
                items.extend(_items)
                
                print(len(items))
                end = time.time()
                

            except TimeoutException:
                break
            except Exception as e:
                logging.error(f"Exception while scrolling page:  {e}")
                logging.info("Reloading page...")
                driver.refresh()

        self.get_products(driver, items)


    def retry_exception(self):
        return
    
    def get_products(self, driver: Firefox, items: list[dict]):
        for i, item in enumerate(items):
            items_count= len(items)
            self.get_product_details(driver, item, i, items_count)
        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
        
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, item, i, items_count):
        
            try:
                start = time.time()
                
                href = item["@id"]
                duplicate_flag = [True for record in self.records if href == record["url item"]]
                if len(duplicate_flag):
                    return

                driver.get(href)

                _item = item["name"]
                sku = item["sku"]


                object_categories = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[contains(@class, 'items-stretch vtex-flex-layout-0-x-stretchChildrenWidth')]//script")))
                content = object_categories.get_attribute("innerText")
                content = json.loads(content)
                content["itemListElement"].pop(-1)
                categories = [ c.get("name")  for c in content["itemListElement"]][:4]
                category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]

                image = item["image"]

                marca = item["brand"]["name"]


                item_specifications = driver.find_element(By.XPATH, "//template[contains(@data-varname,'__STATE__')]")
                item_specifications = driver.execute_script("return arguments[0].content.textContent;", item_specifications)
                item_specifications = json.loads(item_specifications)

                color, materials, fit, made_in, price = None, None, None, None, None
                for key, value in item_specifications.items():
                    if "properties" in key:
                        if "Color" in value["name"]:
                            color = value["values"]["json"][0]

                        elif "Composición" in value["name"]:
                            materials = value["values"]["json"][0]
                            materials = materials.replace("\n", "").replace("\r", "")

                        elif "Lavado SIC" in value["name"]:
                            fit = value["values"]["json"][0]

                        elif "País de Fabricación" in value["name"]:
                            made_in = value["values"]["json"][0]
                            made_in = made_in.replace("Hecho en ", "").replace("HECHO EN ", "")
                    
                    elif "priceRange.sellingPrice" in key:
                        sale_price = value["highPrice"]

                    elif "priceRange.listPrice" in key:
                        price = value["highPrice"]
                        final_price = price

                        if sale_price == price:
                            sale_price, saving = None, None
                        else:
                            saving = f"{int((price-sale_price)*100/price)} %"
                            final_price = sale_price
                
                description = item["description"]

                item_characteristics = f"Descripción: {description} || Composición: {materials} || Lavado: {fit}"
                item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                sizes_element = driver.find_element(By.XPATH, "//select[contains(@name,'product-summary-sku-selector')]")
                sizes = Select(sizes_element)
                sizes = sizes.options
                sizes.pop(0)
        
                for _size in sizes:
                    size = _size.text
                    not_stock = _size.get_attribute("disabled")

                    stock = "available" if not_stock is None else "not available"

                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "NAF NAF Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": marca,
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size}",
                                "item": _item,
                                "item_characteristics": item_characteristics,
                                "url sku": NAFNAF_URL,
                                "image": image,
                                "price": price,
                                "sale_price": sale_price,
                                "shipment cost": stock,
                                "sales flag": saving,
                                "store id": f"9999_nafnaf_col",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": materials,
                                "made_in": made_in,
                                "url item":href,
                            }
                        )
                    
                print(f"NAFNAF {category} {subcategory} {subcategory_2}  {subcategory_3} item {i+1}/{items_count}\t{round(time.time()-start, 3)} s")
                
            except Exception as e:
                print(e)
                logging.error(f"NAFNAF...Error get product details {category} {subcategory} {subcategory_2}: {e}")
                # logging.info("Refresh page...")
                driver.refresh()
        

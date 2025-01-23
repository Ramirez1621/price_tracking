import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import math

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import NAUTY_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]

class nautySession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_bershka = open_browser()
            with WebDriver(driver_bershka) as driver:
                self.open_page(driver)
                time.sleep(5)
                self.select_categories(driver)

            end = time.time()
            logging.info(f"Excution Nauty Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_NAUTY.csv"), index=False)

    def open_page(self, driver):
        try:
            driver.get(url=NAUTY_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            self.display_flag = True
            
            modal_close = driver.find_elements(By.XPATH, "//button[@id='omnisend-form-608b240a4c7fa44b55df51d6-close-action']")
            if len(modal_close):
                modal_close[0].click()

            categories = [
                {"name": "Niñas"},
                {"name": "Niñas"}
                ]
            
            self.select_girls(driver, categories[0]["name"])

            self.select_accesories(driver, categories[1]["name"])

            # for category in categories:
            #     try:
            #         # driver.get(category["href"])
            #         self.select_subcategory(driver, category["name"])
            #     except Exception as e:
            #         logging.error(f"An error ocurred: {e}")
            #         continue
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category..."))
            logging.error(
                (f"details: {e}"))
            raise(e)

    def select_girls(self, driver, category):
        try:

            
            subcategories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//li/a[contains(text(),'Niñas')]/following-sibling::ul/li/a")))

            subcategories = [{"subcategory": c.get_attribute("text").replace("\n", "").strip(), "href":c.get_attribute("href")} for c in subcategories if not "ver todo" in c.get_attribute("text").lower()]

            for subcategory in subcategories:
                driver.get(subcategory["href"])
                time.sleep(2)
                href_items = self.pagination_items(driver)
                self.get_products(driver, href_items, category, "ROPA", subcategory["subcategory"])

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory: {subcategory}"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def select_accesories(self, driver, category):
        try:
            subcategories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//li/a[contains(text(),'ACCESORIOS')]/following-sibling::div//a[@class='site-nav__dropdown-link']")))
            
            # driver.find_element(By.XPATH, "//div[@class='category-tool-filter']").click()
            subcategories = [
                {"subcategory": c.get_attribute("text").replace("\n", "").strip(), "href":c.get_attribute("href")} for c in subcategories
                if not "ver todo" in c.get_attribute("text").lower() 
                and not "bono de regalo online" in c.get_attribute("text").lower()
                and not "tarjeta de regalo" in c.get_attribute("text").lower()
                and not "libro" in c.get_attribute("text").lower()
                ]
            
            for subcategory in subcategories:
                driver.get(subcategory["href"])
                time.sleep(2)
                href_items = self.pagination_items(driver)
                self.get_products(driver, href_items, category, "ACCESORIOS", subcategory["subcategory"])
            
            # for subcategory_2 in subcategories_2:
            #     self.select_subcategory3(driver, category, subcategory, subcategory_2)

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory accesories: {subcategory}"))
            logging.error(
                (f"details: {e}"))
# ------------------------------------------------------------------------------------------------ #
            
    def select_subcategory3(self, driver, category, subcategory, subcategory_2):
        try:
            driver.get(subcategory_2["href"])
            time.sleep(5)
            subcategories_3_buttons = driver.find_elements(By.XPATH,"//button[contains(@class,'is-naked is-outline grid-tag') and not(contains(@class,'active'))]")

            if not len(subcategories_3_buttons):
                subcategories_3_buttons = driver.find_elements(By.XPATH,"category-selector-image")
                if not len(subcategories_3_buttons):
                    href_items = self.pagination_items(driver)
                    items["subcategory3"] = None
                    self.get_product_details(driver, href_items, category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])
                    return
            
            subcategories_3 = [{"name": s.get_attribute("innerText"), "object": s} for s in subcategories_3_buttons]

            list_subcategory3 = list()
            for s in subcategories_3:
                s["object"].click()
                time.sleep(2)
                href_items = self.pagination_items(driver)
                list_subcategory3.append({"subcategory3":s["name"], "hrefs": href_items})
            
            for items in list_subcategory3:
                self.get_product_details(driver, items["hrefs"], category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory2: {items['subcategory3']}"))
            logging.error(
                (f"details: {e}"))
            raise(e)
# ------------------------------------------------------------------------------------------------ #
    def pagination_items(self, driver):
        
        items = list()

        while True:
            _items = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class,'grid-product__link')]")))

            _items = [c.get_attribute("href") for c in _items if not c.get_attribute("href") in items]

            items.extend(_items)
            
            time.sleep(2)
            scroll_position = math.ceil(driver.execute_script("return window.scrollY+document.documentElement.clientHeight;"))
            scroll_end = driver.execute_script("return document.body.scrollHeight;")

            if scroll_position-1 < scroll_end > scroll_position+1:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            else:
                break

        print(len(items))
        return items
            
# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("Retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    
    def get_products(self, driver: Firefox, href_items, category:str, subcategory:str, subcategory_2:str = None, subcategory_3:str = None):
        for i, href in enumerate(href_items):
            count_product = f"{int(i+1/len(href_items))}"
            self.get_product_details(driver, count_product, href, category, subcategory, subcategory_2, subcategory_3)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, count_product, href: str, category: str, subcategory: str, subcategory_2: str, subcategory_3: str):
        try:
            start = time.time()

            duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
            if len(duplicate_flag):
                return

            driver.get(href)

            # load_flag = driver.find_elements(By.XPATH, "//div[@class='size-help']")

            # if not len(load_flag):
            #     time.sleep(5)
            #     print("Reloading...")
            #     driver.refresh()
            #     load_flag = driver.find_elements(By.XPATH, "//div[@class='size-help']")
            #     if not len(load_flag):
            #         return

            item = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "//h1[contains(@class,'h2')]"))).get_attribute("innerText")
            
            # sku = driver.find_element(By.XPATH, "//div[contains(@class,'product-single__description rte')]//p/span[contains(text(),'Ref')]").get_attribute("innerText")

            color = None

            image = driver.find_element(By.XPATH, "//meta[contains(@property,'og:image')]").get_attribute("content")

            marca = "Nauty Blue"

            patron = r"[^0-9 ]"
            
            price = driver.find_elements(By.XPATH, "//span[contains(@id,'ComparePrice')]")

            if len(price):
                price_value = int(re.sub(patron, "", price[0].get_attribute("innerText") ))
                
                sale_price = driver.find_element(By.XPATH, "//span[contains(@id,'ProductPrice')]")
                sale_price_value = int(re.sub(patron, "", sale_price.get_attribute("innerText")))
                final_price = sale_price_value

                saving = driver.find_elements(By.XPATH, "//span[contains(@id,'SavePrice')]")
                if len(saving):
                    saving_value = saving[0].get_attribute("innerText").replace("Ahorra", "")
                else:
                    saving_value = f"-{round(100-sale_price*100/price)}%"
            else:
                price = driver.find_element(By.XPATH, "//span[contains(@id,'ProductPrice')]")
                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                final_price = price_value
                sale_price_value, saving_value = None, None
            
            # ------------------------------------- descripción ----------------------------------------------------------- #
            # composition_items = driver.find_elements(By.XPATH,"//div[contains(@class,'product-single__description rte')]/p/span")

            # # description = composition_items[0].get_attribute("innerText")
            # materials = composition_items[1].get_attribute("innerText")
            # materials = ""
            # for comp in composition_items:
            #     materials += comp.get_attribute("innerText")

            json_data = driver.find_element(By.XPATH,"//script[contains(@type,'application/ld+json')]").get_attribute("innerText")
            json_data = json.loads(json_data)

            description = json_data["description"].split("Material:")[0]
            description = description.replace("\n", " ")

            materials = json_data["description"].split("Material: ")
            if len(materials) > 1:
                materials = materials[1].split("\n")[0]
            else:
                materials = None
                
            sku = json_data["sku"]


            made_in = None #driver.find_element(By.XPATH,"//section[contains(@class,'product-origin')]/p[last()]").get_attribute("innerText").replace("Hecho en ","")
            
            

            item_characteristics = f"Descripción: {description} || Composición: {materials}"
            # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

            sizes_stock = driver.find_elements(By.XPATH, "//input[contains(@name,'Talla') or contains(@name,'Tamaño') and not(contains(@class,'disabled'))]")
            sizes_out_stock = driver.find_elements(By.XPATH, "//input[contains(@name,'Talla') or contains(@name,'Tamaño') and contains(@class,'disabled')]")

            sizes_stock = [(size.get_attribute("value"),"available") for size in sizes_stock]
            sizes_out_stock = [(size.get_attribute("value"),"not available") for size in sizes_out_stock]

            # Execute the command for make apear the detail bar
            if not len(sizes_stock + sizes_out_stock):
                index_c = json_data["description"].find("Contenido")
                index_q = json_data["description"].find("Cantidad")
                if index_c > 0:
                    size = json_data["description"][index_c:-1]
                    size = size[:size.find("\n")].replace("Contenido:","")
                elif index_q > 0:
                    size = json_data["description"][index_q:-1]
                    size = size[:size.find("\n")].replace("Cantidad:","")
                else:
                    size = "S/T"
                
                self.records.append(
                        {
                            "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                            "canal": "Nauty Blue Colombia",
                            "category": category,
                            "subcategory": subcategory,
                            "subcategory_2": subcategory_2,
                            "subcategory_3": subcategory_3,
                            "marca": marca,
                            "modelo": color,
                            "sku": sku,
                            "upc": f"{sku}_{color}_{size}",
                            "item": item,
                            "item_characteristics": item_characteristics,
                            "url sku": NAUTY_URL,
                            "image": image,
                            "price": price_value,
                            "sale_price": sale_price_value,
                            "shipment cost": "Available",
                            "sales flag": saving_value,
                            "store id": f"9999_nautyblue_col",
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
            
            for size, stock in sizes_stock + sizes_out_stock:
                # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                self.records.append(
                        {
                            "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                            "canal": "Nauty Blue Colombia",
                            "category": category,
                            "subcategory": subcategory,
                            "subcategory_2": subcategory_2,
                            "subcategory_3": subcategory_3,
                            "marca": marca,
                            "modelo": color,
                            "sku": sku,
                            "upc": f"{sku}_{color}_{size}",
                            "item": item,
                            "item_characteristics": item_characteristics,
                            "url sku": NAUTY_URL,
                            "image": image,
                            "price": price_value,
                            "sale_price": sale_price_value,
                            "shipment cost": stock,
                            "sales flag": saving_value,
                            "store id": f"9999_nautyblue_col",
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
            print(f"Nauty {category} {subcategory} item {count_product}\t{round(time.time()-start, 3)} s")
                
            time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"Error get product details: {e}")
            logging.info("Refresh page...")
            driver.refresh()
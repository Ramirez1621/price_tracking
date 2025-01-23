import logging
import datetime as dt
import time
import json
import pandas as pd
import re

from os.path import join
from bs4 import BeautifulSoup
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import POLITO_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["rebajas", "sostenibilidad", "ver todo", "regalos"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class politoSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_hm = open_browser()
            # with WebDriver(driver_bershka) as driver:
            self.open_page(driver_hm)
            time.sleep(5)
            self.select_categories(driver_hm)
            driver_hm.quit()
            
            end = time.time()
            logging.info(f"Excution POLITO Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_POLITO.csv"), index=False)

    def open_page(self, driver):
        try:
            driver.get(url=POLITO_URL)

        except Exception as e:
            logging.error(
                (f"Polito An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[@id='main_nav']/li[contains(@class,'lvl1 parent megamenu')]")))
            
            categories_list = list()
            
            for category in categories:
                if category.find_element(By.XPATH, "./a").get_attribute("innerText").lower() not in EXCLUSION_LIST:
                    _subcategories = category.find_elements(By.XPATH, ".//li//a[contains(@class,'categorias') or contains(@class,'complementos')]/following-sibling::ul[@class='subLinks']/li/a")
                    _sub = list()
                    for _subcategory in _subcategories:
                        if _subcategory.get_attribute("text").lower() not in EXCLUSION_LIST:
                            _sub.append({
                                "name":_subcategory.get_attribute("text"),
                                "href":_subcategory.get_attribute("href")
                            })
                    
                    categories_list.append({
                        "category": category.find_element(By.XPATH, "./a").get_attribute("innerText"),
                        "subcategories": _sub
                    })

            for category in categories_list:
                    print(category["category"])
                    self.select_subcategory(driver, category)
        
            
        except Exception as e:
            logging.error(
                (f"Polito An error has ocurred during scan categories"))
            logging.error(
                (f"details: {e}"))

    def select_subcategory(self, driver, subcategories):
        try:
            for subcategory in subcategories["subcategories"]:
                
                url = subcategory.get("href")
                subcategory_name = subcategory.get("name")
                driver.get(url)

                items = self.pagination_items(driver, url)

                self.get_products(driver, items, subcategories["category"], subcategory_name)


        except Exception as e:
            logging.error(
                (f"Polito An error has ocurred during scan subcategories"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def select_subcategory2(self, driver, category, subcategory):
        try:
            section_id = subcategory["id"]
            subcategories_2 = driver.find_elements(By.XPATH,f"//input[contains(@id,'tipo-de-producto')]")

            subcategories_2 = [{"name": s.get_attribute("innerText"), "href": s.get_attribute("href")} for s in subcategories_2 if s.get_attribute("innerText").strip().lower() not in EXCLUSION_LIST]

            for subcategory_2 in subcategories_2:
                self.select_subcategory3(driver, category, subcategory, subcategory_2)
                # driver.quit()
                # driver = open_browser()
                # self.open_page(driver)

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory2: {subcategory_2}"))
            logging.error(
                (f"details: {e}"))
# ------------------------------------------------------------------------------------------------ #
            
    def select_subcategory3(self, driver, category, subcategory, subcategory_2):
        try:
            driver.get(subcategory_2["href"])
            
            items = {"subcategory3":None}
            time.sleep(2)

            # Expand the tipology menu for select subcategories
            try:
                WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.XPATH,"//button[@aria-label='bksStyle.view.fourColumn']")))[0].click()
                
                driver.find_element(By.XPATH,"//button[@data-qa-anchor='filterButton']").click()
                WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.XPATH,"//button/h3[text()='Tipología']")))[0].click()
                #obtains the subcategories names and web object
                subcategories_3_buttons = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.XPATH,"//button[@data-qa-anchor='typologyFilter']")))
                subcategories_3 = [{"name": s.get_attribute("innerText"), "object":s} for s in subcategories_3_buttons]

                list_subcategory3 = list()
                for s in subcategories_3:
                    driver.execute_script("arguments[0].click()",s["object"])
                    time.sleep(1)
                    # driver.get(s["href"])
                    href_items = self.pagination_items(driver)
                    list_subcategory3.append({"subcategory3":s["name"], "hrefs": href_items})
                    driver.execute_script("arguments[0].click()",s["object"])
                
                for items in list_subcategory3:
                    # try:
                    self.get_products(driver, items["hrefs"], category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])
                    # except TimeoutError:
                    #     self.get_product_details(driver, items["hrefs"], category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])

            except Exception:
                empty_page = driver.find_elements(By.XPATH,"//h2[contains(@class,'empty-title')]")
                if not len(empty_page):
                    href_items = self.pagination_items(driver)
                    self.get_products(driver, href_items, category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])
                    return
                else:
                    return
            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # time.sleep(1)
            # subcategories_3_buttons = driver.find_elements(By.XPATH,"//button[contains(@class,'is-naked is-outline grid-tag') and not(contains(@class,'active'))]")

            # if not len(subcategories_3_buttons):
            #     subcategories_3_buttons = driver.find_elements(By.XPATH,"//button[contains(@class,'category-selector-image')]")
            #     if not len(subcategories_3_buttons):
            #         empty_page = driver.find_elements(By.XPATH,"//h2[contains(@class,'empty-title')]")
            #         if not len(empty_page):
            #             href_items = self.pagination_items(driver)
            #             self.get_product_details(driver, href_items, category["name"], subcategory["name"], subcategory_2["name"], items["subcategory3"])
            #             return
            #         else:
            #             return
            

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory3: {items['subcategory3']}"))
            logging.error(
                (f"details: {e}"))
# ------------------------------------------------------------------------------------------------ #
    def pagination_items(self, driver, url):
        
        start = time.time()
        end = 0
        page = 2
        items = list()
        while (end - start) < 800:
            json_items = driver.execute_script("return slideruleData.collection.rawProducts")
            
            if len(json_items):
                _items = [c  for c in json_items if not c.get("handle") in items]
                items.extend(_items)
            else:
                break
            
            
            end = time.time()
            url_page = f"{url}?page={page}"
            driver.get(url_page)
            page += 1

        print(len(items))
        return items
            
# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, driver: Firefox, items, category=None, subcategory=None, subcategory_2=None, subcategory_3=None):
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            self.get_product_details(driver, count_product, item, category, subcategory, subcategory_2, subcategory_3)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, count_product, item, category, subcategory, subcategory_2, subcategory_3):
        try:
                start = time.time()
                
                name = item.get("title")
                href = f"https://polito.com.co/products/{item.get('handle')}"
                image = item.get("images", [""])[0]
                sku = item.get("variants", [{}])[0].get("barcode")

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                if len(duplicate_flag):
                    return

                subcategory_2 = item.get("type")

                marca = "Polito"


                price_value = int(item.get("price")/100)
                final_price = price_value

                sale_price = item.get("compare_at_price")

                if sale_price is not None:
                    sale_price_value = price_value
                    price_value = int(item.get("compare_at_price")/100)
                    final_price = sale_price_value
                    saving_value = f"-{round(100-sale_price_value*100/price_value)}%"

                else:
                    sale_price_value, saving_value = None, None
                
                # ------------------------------------- descripción ----------------------------------------------------------- #

                composition_raw = item.get("description")
                composition = BeautifulSoup(composition_raw, 'html.parser')

                composition_tag = composition.find_all('p')

                description = ""
                for tag in composition_tag:
                    description += tag.text
                
                description = description.replace("\xa0", " "). replace("-"," |")

                patron = r'\b(?:Tela|Tejido|Material|Composici[oó]n).*?\|'

                patron_2 = r'(\b\d+% )?(algod[oó]n|elastano|poliéster)\b'

                # patron_2 = r'\b(?:Tela|Tejido|Material).*?\|'

                _description = re.findall(patron, description, re.IGNORECASE)

                materials = re.findall(patron_2, description, re.IGNORECASE)

                materials = [ f"{material[0]}{material[1]}" for material in materials]

                materials.extend(_description)
                materials = ", ".join(materials).replace("|", "").strip()

                item_characteristics = f"Descripción: {description}"
                
                made_in = None

                sizes = item.get("variants")
                
                for size in sizes:
                    
                    color = size.get("option2")
                    size_value = size.get("option1")
                    stock = "available" if size.get("available") is True else "not available"
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Polito Colombia",
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
                                "url sku": POLITO_URL,
                                "image": image,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_polito_col",
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
                print(f"Polito {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"Polito...Error get product details {category} {subcategory} {subcategory_2}: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
import logging
import datetime as dt
import time
import json
import pandas as pd
import re

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

class massimoSession():
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
            logging.info(f"Excution Massimo Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_MASSIMO.csv"), index=False)

    def open_page(self, driver):
        try:
            driver.get(url=MASSIMO_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            self.display_flag = True
            
            categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//header-sections/div//a")))
            
            
            categories = [{"name": c.get_attribute("innerText"), "href":c.get_attribute("href")} for c in categories]
            categories[0]["ids"] = [1887002]#, 1739529, 2091770] #ids for women reabajas, punto, colección
            categories[1]["ids"] = [1887004]#, 2147828, 1938509, 2157046] #ids for men reabajas, punto, colección, stylist choice
            for category in categories:
                try:
                    driver.get(category["href"])
                    self.select_subcategory(driver, category)
                except Exception as e:
                    logging.error(f"An error ocurred: {e}")
                    continue
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category: {category}"))
            logging.error(
                (f"details: {e}"))
            raise(e)

    def select_subcategory(self, driver, category):
        try:
            # Open menu for subcategories
            menu = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//button[@aria-label='menu-ham']")))[0]
            driver.execute_script("arguments[0].click()", menu)


            subcategories_rebajas = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[@id='nav-submenu-list-{0}']//a".format(category["ids"][0]))))

            subcategories_rebajas = [{"subcategory": c.get_attribute("innerText").strip(), "href":c.get_attribute("href")} for c in subcategories_rebajas if not "hasta" in c.get_attribute("innerText").lower() and not "compra por" in c.get_attribute("innerText").lower()]

            # subcategories_rebajas = [{"subcategory":"Punto", "name": c.get_attribute("innerText"), "href":c.get_attribute("href")} for c in subcategories_rebajas if not "hasta" in c.get_attribute("innerText").lower() and not "compra por" in c.get_attribute("innerText").lower()]

            # subcategories_punto = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            #             (By.XPATH, "//a[@id='{0}']".format(category["ids"][1]))))[0]
            
            # subcategories_punto = {"subcategory":"Punto", "name": None, "href": subcategories_punto.get_attribute("href")}
            
            subcategories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//header-menu-category/li/a")))
            
            subcategories = [
                {"subcategory": c.get_attribute("innerText").replace("\n","").replace("NEW",""), "href": c.get_attribute("href")} for c in subcategories 
                if category["name"] in c.get_attribute("title") and
                "rebajas" not in c.get_attribute("title").lower() and 
                "nuevo" not in c.get_attribute("title").lower() and 
                "join" not in c.get_attribute("title").lower() and 
                "editorial" not in c.get_attribute("title").lower() and 
                "paper" not in c.get_attribute("title").lower() and
                "personal tailoring hombre" not in c.get_attribute("title").lower()
            ]

            # subcategories_stylist = {}
            # if len(category["ids"]) == 4:
            #     subcategories_stylist = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            #             (By.XPATH, "//a[@id='{0}']".format(category["ids"][3]))))
            #     subcategories_stylist = {"subcategory":"Stylist Choice", "name": None, "href": subcategories_stylist.get_attribute("href")}
                

            subcategories.extend(subcategories_rebajas)
            # subcategories.append(subcategories_punto)
            # subcategories.append(subcategories_stylist)

            for subcategory in subcategories:
                driver.get(subcategory["href"])
                self.select_subcategory2(driver, category, subcategory["subcategory"])

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory: {subcategory}"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def select_subcategory2(self, driver, category, subcategory: str):
        try:
            if self.display_flag == True:
                display_filter = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located(
                            (By.XPATH, "//button[@class='btn']")))[0]
                
                display_filter.click()
                display_filter.click()
                self.display_flag = False
            
            try:
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                            (By.XPATH, "//div[@class='category-tool-filter']"))).click()
                
                # driver.find_element(By.XPATH, "//div[@class='category-tool-filter']").click()
                
            except TimeoutException:
                logging.error(f"Timeout exception while find //div[@class='category-tool-filter']")

                type = driver.find_elements(By.XPATH, "//button/span[contains(text(),'TIPO DE PRENDA')]")
                if len(type):
                    logging.info(f"type of clothing exists")
                    type.click()

            else:
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                            (By.XPATH, "//button/span[contains(text(),'TIPO DE PRENDA')]"))).click()
            
            subcategories_2 = driver.find_elements(By.XPATH,"//form//div[contains(@class,'p-8')]//input")
            # description = driver.find_element(By.XPATH,"//p[contains(@class,'copy-description')]").get_attribute("innerText")

            list_subcategory2 = list()
            for s in subcategories_2:
                driver.execute_script("arguments[0].click()", s)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                href_items = self.pagination_items(driver)
                subcategory2_name = s.get_attribute("name").replace("CT-","")
                
                list_subcategory2.append({"name": subcategory2_name, "items": href_items})
                driver.execute_script("arguments[0].click()", s)
            
            for items in list_subcategory2:
                self.get_products(driver, items["items"], category["name"], subcategory, items["name"])
            # for subcategory_2 in subcategories_2:
            #     self.select_subcategory3(driver, category, subcategory, subcategory_2)

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory2: {subcategory}"))
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
# ------------------------------------------------------------------------------------------------ #
    def pagination_items(self, driver):
        
        items = list()

        while True:
            _items = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//category-grid//product-view//a[contains(@class,'card9-link')]")))

            _items = [c.get_attribute("href") for c in _items if not c.get_attribute("href") in items]

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
        print("Retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    
    def get_products(self, driver: Firefox, href_items, category:str, subcategory:str, subcategory_2:str, subcategory_3:str = None):
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

            if subcategory_2 is None:
                subcategory_2 = subcategory_3
                subcategory_3 = None

            item = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.XPATH, "//div[@id='productName']/h1")))[0].get_attribute("innerText")

            product_selector = driver.find_element(By.XPATH, "//product-color-selector//p").get_attribute("innerText").split(" / ")
            sku = product_selector[-1]

            color = product_selector[0]

            image = driver.find_element(By.XPATH, "//meta[@property='og:image']").get_attribute("content")

            marca = "Massimo Dutti"

            patron = r"[^0-9 ]"
            
            sale_price = driver.find_elements(By.XPATH, "//product-page-product-details//formatted-price//div[contains(@class, 'd-price-special')]")

            if len(sale_price):
                price = driver.find_element(By.XPATH, "//product-page-product-details//formatted-price//span")
                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                
                sale_price_value = int(re.sub(patron, "", sale_price[0].get_attribute("innerText")))
                final_price = sale_price_value

                saving = driver.find_elements(By.XPATH, "//product-page-layout//product-bullet-percentage/div[contains(@class, 'product-percentage-bullet')]")
                if len(saving):
                    saving_value = saving[0].get_attribute("innerText")
                else:
                    saving_value = f"-{round(100-sale_price*100/price)}%"
            else:
                price = driver.find_element(By.XPATH, "//product-page-product-details//formatted-price//div[contains(@class,'text-nowrap')]")
                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                final_price = price_value
                sale_price_value, saving_value = None, None
            
            # ------------------------------------- descripción ----------------------------------------------------------- #
            comp_menu = driver.find_element(By.XPATH,"//label[@for='tab-2']")
            driver.execute_script("arguments[0].click()", comp_menu)
            
            composition_items = driver.find_element(By.XPATH,"//accordion-item[contains(@class,'cares')]//div[contains(@class,'accordion-content')]")

            # materials = "".join([ c.get_attribute("innerText") for c in composition_items])
            materials = composition_items.get_attribute("innerText").replace("\n", "-")

            # cares_items = driver.find_elements(By.XPATH,"//accordion-item[contains(@class,'cares')]//div[contains(@class,'accordion-content')]//label")

            # cares = ", ".join([ c.get_attribute("innerText") for c in cares_items])

            made_in = None #driver.find_element(By.XPATH,"//section[contains(@class,'product-origin')]/p[last()]").get_attribute("innerText").replace("Hecho en ","")
            
            description = driver.find_elements(By.XPATH,"//product-page-product-info//div[contains(@class,'product-description')]/span")
            description = "".join([ c.get_attribute("innerText") for c in description])

            item_characteristics = f"Descripción: {description} || Composición: {materials}"
            # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

            sizes_stock = driver.find_elements(By.XPATH, "//product-page-layout//product-size-selector//button[contains(@class,'product-size-selector') and not(contains(@class,'button--disabled'))]")
            sizes_out_stock = driver.find_elements(By.XPATH, "//product-page-layout//product-size-selector//button[contains(@class,'product-size-selector') and contains(@class,'button--disabled')]")

            sizes_stock = [(size.get_attribute("innerText"),"available") for size in sizes_stock]
            sizes_out_stock = [(size.get_attribute("innerText"),"not available") for size in sizes_out_stock]

            # Execute the command for make apear the detail bar
            
            
            for size, stock in sizes_stock + sizes_out_stock:
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
                            "upc": f"{sku}_{color}_{size}",
                            "item": item,
                            "item_characteristics": item_characteristics,
                            "url sku": MASSIMO_URL,
                            "image": image,
                            "price": price_value,
                            "sale_price": sale_price_value,
                            "shipment cost": stock,
                            "sales flag": saving_value,
                            "store id": f"9999_massimodutti_col",
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
            print(f"Massimo {category} {subcategory} item {count_product}\t{round(time.time()-start, 3)} s")
                
            time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"Error get product details: {e}")
            logging.info("Refresh page...")
            driver.refresh()
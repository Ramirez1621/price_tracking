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
from settings import BERSHKA_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class bershkaSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_bershka = open_browser()
            # with WebDriver(driver_bershka) as driver:
            self.open_page(driver_bershka)
            time.sleep(5)
            self.select_categories(driver_bershka)
            driver_bershka.quit()
            
            end = time.time()
            logging.info(f"Excution Bershka Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_BERSHKA.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=BERSHKA_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[contains(@class,'menu-desktop__section')]/li/a")))
            
            categories = [{"name": c.get_attribute("aria-label").split(" ")[-1], "id":c.get_attribute("aria-controls")} for c in categories]

            for category in categories:
                try:
                    self.select_subcategory(driver, category)
                except Exception as e:
                    logging.error(f"An error ocurred: {e}")
                    continue
        
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category: {category}"))
            logging.error(
                (f"details: {e}"))

    def select_subcategory(self, driver, category):
        try:
            section_id = category["id"]
            subcategories_s = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH,f"//section[@id='{section_id}']//button[contains(@class,'category-item__button')]")))

            subcategories = [{"name": s.get_attribute("innerText"), "id":s.get_attribute("aria-controls")} for s in subcategories_s if s.get_attribute("innerText").lower().strip() in INCLUSION_LIST]

            subcategories_ns = driver.find_elements(By.XPATH,f"//section[@id='{section_id}']//a[contains(@class,'menu-item-link category-item__link category-item--uppercase')]")

            subcategories_ns = [{"name": s.get_attribute("innerText"), "id":None} for s in subcategories_ns if s.get_attribute("innerText").strip().lower().strip() in INCLUSION_LIST]

            subcategories.extend(subcategories_ns)

            for subcategory in subcategories:
                self.select_subcategory2(driver, category, subcategory)

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory: {subcategory}"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def select_subcategory2(self, driver, category, subcategory):
        try:
            section_id = subcategory["id"]
            subcategories_2 = driver.find_elements(By.XPATH,f"//section[@id='{section_id}']//a[contains(@class,'menu-item-link subcategory-item__link')]")

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
    def pagination_items(self, driver):
        
        items = list()
        time.sleep(10)
        while True:
            _items = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//a[@data-qa-anchor='productItemHref']")))

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
        print("retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, driver: Firefox, href_items, category, subcategory, subcategory_2, subcategory_3):
        for i, href in enumerate(href_items):
            count_product = f"{int(i+1/len(href_items))}"
            self.get_product_details(driver, count_product, href, category, subcategory, subcategory_2, subcategory_3)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, count_product, href, category, subcategory, subcategory_2, subcategory_3):
        try:
                start = time.time()

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
                if len(duplicate_flag):
                    return
                
                driver.get(href)
                item = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//h1[@data-qa-anchor='productDetailName']")))[0].get_attribute("innerText")

                # time.sleep(1)
                load_flag = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='size-help']")))
                # if not len(load_flag):
                #     print("Reloading...")
                #     driver.refresh()
                #     time.sleep(5)
                #     load_flag = driver.find_elements(By.XPATH, "//div[@class='size-help']")
                #     if not len(load_flag):
                #         return
                
                sku = driver.find_element(By.XPATH, "//div[contains(@class, 'product-reference')]").get_attribute("innerText")

                image = driver.find_element(By.XPATH, "//button/span[contains(@class,'image-item-wrapper')]/img[contains(@class,'image-item')]").get_attribute("src")

                marca = "Bershka"

                patron = r"[^0-9 ]"
                price = driver.find_element(By.XPATH, "//div[@data-qa-anchor='productDetailPrice']//span[@data-qa-anchor='productItemPrice']")
                
                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                final_price = price_value

                sale_price = driver.find_elements(By.XPATH, "//div[@data-qa-anchor='productDetailPrice']//span[@data-qa-anchor='productItemDiscount']")

                if len(sale_price):
                    sale_price_value = int(re.sub(patron, "", sale_price[0].get_attribute("innerText") ))
                    final_price = sale_price_value
                    saving = driver.find_elements(By.XPATH, "//div[@data-qa-anchor='productDetailPrice']//span[@class='discount-tag']")
                    if len(saving):
                        saving_value = saving[0].get_attribute("innerText")
                    else:
                        saving_value = f"-{round(100-sale_price*100/price)}%"
                else:
                    sale_price_value, saving_value = None, None
                
                # ------------------------------------- descripción ----------------------------------------------------------- #
                WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH,"//button[contains(text(),'Composición')]"))).click()
                
                composition_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//article[@class='product-compositions__composition']")))

                materials = ""
                for comp in composition_items:
                    materials += comp.get_attribute("innerText").replace("\n\n","    ") + '    '

                cares_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//article[contains(@class,'product-cares__care')]/p")))

                cares = ", ".join([ c.get_attribute("innerText") for c in cares_items])

                made_in = driver.find_element(By.XPATH,"//section[contains(@class,'product-origin')]/p[last()]").get_attribute("innerText").replace("Hecho en ","")
                
                description = driver.find_element(By.XPATH,"//meta[@data-hid='description']").get_attribute("content")

                item_characteristics = f"Descripción: {description} || Composición: {materials} || Lavado: {cares}"
                # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                sizes_stock = driver.find_elements(By.XPATH, "//ul[contains(@data-qa-anchor,'productDetailSize')]/li/button[not(contains(@class, 'is-disabled'))]")
                sizes_out_stock = driver.find_elements(By.XPATH, "//ul[contains(@data-qa-anchor,'productDetailSize')]/li/button[contains(@class, 'is-disabled')]")

                sizes_stock = [(size.get_attribute("innerText"),"available") for size in sizes_stock]
                sizes_out_stock = [(size.get_attribute("innerText"),"not available") for size in sizes_out_stock]

                # Execute the command for make apear the detail bar
                color = driver.find_elements(By.XPATH, "//a[@data-qa-anchor='productDetailColor']")
                if len(color):
                    color = color[0].get_attribute("aria-label")
                else: 
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.37);")
                    color = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@class='product-summary__color']"))).get_attribute("innerText")
                
                for size, stock in sizes_stock + sizes_out_stock:
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Bershka Colombia",
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
                                "url sku": BERSHKA_URL,
                                "image": image,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_bershka_col",
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
                print(f"Bershka {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"Bershka...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
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
from settings import AERIE_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser




class aerieSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_arie = open_browser()
            with WebDriver(driver_arie) as driver:
                self.open_page(driver)
                self.select_categories(driver)

            end = time.time()
            logging.info(f"Excution Aerie Time: {end-start} s")
            

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_AERIE.csv"), index=False)
        # return self.records

    def open_page(self, driver: Firefox):
        try:
            driver.get(url=AERIE_URL)
            modal_window = driver.find_elements(By.XPATH, "//button/span[text()='X']")
            if len(modal_window):
                driver.execute_script("arguments[0].click()",modal_window[0])
            cookies_window = driver.find_elements(By.XPATH, "//button[text()='No aceptar']")
            if len(cookies_window):
                driver.execute_script("arguments[0].click()",cookies_window[0])

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)


    def select_categories(self, driver: Firefox):
        try:
            modal_window = driver.find_elements(By.XPATH, "//button/span[text()='X']")
            if len(modal_window):
                driver.execute_script("arguments[0].click()",modal_window[0])
            cookies_window = driver.find_elements(By.XPATH, "//button[text()='No aceptar']")
            if len(cookies_window):
                driver.execute_script("arguments[0].click()",cookies_window[0])
            categories = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//div[contains(@class,'americaneagle-americaneagle-5-x-menud_container_Aerie')]//li//div/a")))
            categories = [c.get_attribute("href") for c in categories if "new-arrivals" not in c.get_attribute("href") and "ver todo" not in c.get_attribute("innerText").lower() and "offline" not in c.get_attribute("href")]

            categories = list(set(categories))
            # categories = [f"{AE_URL}/mujer", f"{AE_URL}/hombre"]
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
        modal_window = driver.find_elements(By.XPATH, "//button/span[text()='X']")
        if len(modal_window):
            driver.execute_script("arguments[0].click()",modal_window[0])
        cookies_window = driver.find_elements(By.XPATH, "//button[text()='No aceptar']")
        if len(cookies_window):
            driver.execute_script("arguments[0].click()",cookies_window[0])
        start = time.time()
        end = 0
        items = list()
        while (end - start) < 800:
            try:
                # driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.75)")
                products = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class,'vtex-flex-layout-0-x-flexCol--content-search-catalogo')]//script")))
                content = products.get_attribute("innerText")
                content = json.loads(content)
                _items = [c["item"]  for c in content["itemListElement"] if not c["item"] in items]
                items.extend(_items)
            
                print(len(items))

                scroll = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                        (By.XPATH, "//div[contains(@class,'vtex-search-result-3-x-buttonShowMore vtex-search-result-3-x-buttonShowMore--plp-showmore')]//a")))
                
                driver.execute_script("arguments[0].scrollIntoView();", scroll)
                time.sleep(1)

                
                end = time.time()
                

            except TimeoutException:
                break
            except Exception as e:
                logging.error(f"Exception while scrolling page:  {e}")
                logging.info("Reloading page...")
                driver.refresh()


        self.get_product_details(driver, items)


    def retry_exception(self):
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
        
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, items: list[dict]):
        for i, item in enumerate(items):
            try:
                modal_window = driver.find_elements(By.XPATH, "//button/span[text()='X']")
                if len(modal_window):
                    driver.execute_script("arguments[0].click()",modal_window[0])
                cookies_window = driver.find_elements(By.XPATH, "//button[text()='No aceptar']")
                if len(cookies_window):
                    driver.execute_script("arguments[0].click()",cookies_window[0])
                start = time.time()
                href = item["@id"]

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                if len(duplicate_flag):
                    continue
                # for record in self.records:
                #     if href == record["url item"]:
                #         continue
                driver.get(href)

                _item = item["name"]
                sku = item["sku"]


                object_categories = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[contains(@class, 'vtex-flex-layout-0-x-flexRow--product-breadcrumb')]//script")))
                content = object_categories.get_attribute("innerText")
                content = json.loads(content)
                content["itemListElement"].pop(-1)
                # drop Aerie word of the categories...
                categories = [ c.get("name")  for c in content["itemListElement"]][:4]
                category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]

                image = item["image"]

                marca = item["offers"]["offers"][0]["seller"]["name"]

                price = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                            (By.XPATH, "//span[contains(@class, 'vtex-product-price-1-x-sellingPriceValue')]"))).get_attribute("innerText").replace("$\xa0","")
                
                price = int(price.replace(".",""))

                saving = driver.find_elements(By.XPATH, "//span[contains(@class, 'vtex-product-price-1-x-savingsPercentage')]")
                
                final_price = price

                if len(saving):
                    saving = saving[0].get_attribute("innerText").replace("\xa0"," ")
                    sale_price = price
                    final_price = price
                    # Update the price value
                    price = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-product-price-1-x-listPrice')]").get_attribute("innerText").replace("$\xa0","")
                    price = int(price.replace(".",""))
                    
                else:
                    sale_price, saving = None, None


                item_specifications = driver.find_element(By.XPATH, "//template[contains(@data-varname,'__STATE__')]")
                item_specifications = driver.execute_script("return arguments[0].content.textContent;", item_specifications)
                item_specifications = json.loads(item_specifications)

                color, materials, cares, fit, made_in = None, None, None, None, None
                for key, value in item_specifications.items():
                    if "properties" in key:
                        if "Color" in value["name"]:
                            color = value["values"]["json"][0]

                        elif "Materiales y Cuidado" in value["name"]:
                            cares = value["values"]["json"][0]
                            materials = cares.split("•")
                            materials = materials[1].replace("\n", "").replace("\r", "") if len(materials) > 2 else None

                        elif "Talla y Fit" in value["name"]:
                            fit = value["values"]["json"][0]

                        elif "País de Fabricación" in value["name"]:
                            made_in = value["values"]["json"][0]
                            made_in = made_in.replace("Hecho en ", "").replace("HECHO EN ", "")
                
                description = item["description"]

                item_characteristics = f"Descripción: {description} || Materiales y Cuidados: {cares} || Fit y Talla: {fit}"
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
                                "canal": "Aerie Colombia",
                                "category": "Mujer",
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": "Aerie",
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size}",
                                "item": _item,
                                "item_characteristics": item_characteristics,
                                "url sku": AERIE_URL,
                                "image": image,
                                "price": price,
                                "sale_price": sale_price,
                                "shipment cost": stock,
                                "sales flag": saving,
                                "store id": f"9999_aerie_col",
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
                # print(f"Aerie item {i+1}/{len(items)}\t{round(time.time()-start, 3)} s")
                print(f"Aerie {category} {subcategory} {subcategory_2}  {subcategory_3} item {i+1}/{len(items)}\t{round(time.time()-start, 3)} s")
                
            except Exception as e:
                print(e)
                logging.error(f"Aerie...Error get product details {category} {subcategory} {subcategory_2}: {e}")
                # logging.info("Refresh page...")
                driver.refresh()
        

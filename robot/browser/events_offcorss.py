import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests
import threading
from bs4 import BeautifulSoup

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import OFFCORSS_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class offcorssSession():
    def __init__(self):
        self.records = list()
        self.semaphore = threading.Semaphore(20)
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_offcors= open_browser()
            with WebDriver(driver_offcors) as driver:
                self.open_page(driver)
                time.sleep(5)
                ids = self.select_categories(driver_offcors)
            
            #TODO
            # ids = ["7"]
            self.scan_items(ids)
            # driver_pullbear.quit()
            
            end = time.time()
            logging.info(f"Excution Offcorss Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_OFFCORSS.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=OFFCORSS_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            # categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            #             (By.XPATH, "//li[contains(@class,'category level-2') and contains(@class,'has-subitems')]")))
            
            # categories = [{"name": c.get_attribute("innerText"), "object":c} for c in categories]


            url_category = "https://offcorss.vteximg.com.br/arquivos/scriptWebExtend.min.js"
            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
            response = requests.get(url_category, headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                source_code = response.content.decode()
                categories = driver.execute_script(source_code+"return categoryTree")
                ids = list()

                ids = [c.get("id") for c in categories]
                # for c in categories:
                #     _ = [ i.get('id') for i in c.get('children')]
                #     ids.extend(_)
                    # _ = [ id["id"] for id in _]
                    # category_ids.extend(_)
                
                return ids
                
                
                    
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def scan_items(self, category_ids):
        try:
            ids_items = list()
            for subcategory_id in category_ids:
                # url_category = f"https://www.offcorss.com/api/catalog_system/pub/products/search?fq=categoriesId:{subcategory_id}"
                # url_category = f"https://www.offcorss.com/api/catalog_system/pub/products/search/{subcategory_id}"
                page = 1
                quantity_items = 50
                count  = 0
                retry = 0
                start = time.time()
                end = 0
                while True and (end - start) < 600:
                    url_category = f"https://www.offcorss.com/buscapagina?fq=C{subcategory_id}&O=OrderByScoreDESC&PS={quantity_items}&sl=04cc23a1-a6fe-42d1-a751-c24fdeaa541b&cc=1&sm=0&PageNumber={page}"
                    # params = {"languageId":-5, "showProducts": "false", "appId":1}
                    headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                    
                    response = requests.get(url_category, headers=headers)

                    if response.status_code == 200 or response.status_code == 206:
                        # data = json.loads(response.content)
                        html_text = response.content.decode()

                        if not len(html_text):
                            retry += 1
                        # Parsear el HTML
                        soup = BeautifulSoup(html_text, 'html.parser')
                        # Encontrar todas las etiquetas 'p' con la clase 'hiddenId hide' y obtener su texto
                        p_tags = soup.find_all('p', class_='hiddenId hide')

                        ids = [p_tag.text for p_tag in p_tags]
                        ids = [i for i in ids if not i in ids_items]

                        ids_items.extend(ids)

                        self.get_products(ids)

                        page += 1
                    elif response.status_code == 404:
                        break
                    elif response.status_code == 500:
                        count += 1
                    
                        print(f"code 500: {count}")
                        time.sleep(10)
                    
                    print(f"subcategory: {subcategory_id}")
                    print(f"page {page}")

                    time.sleep(5)
                    end = time.time()
                    if retry >= 3:
                        break

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory2"))
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
        threads = list()
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            # self.get_product_details(count_product, item)
            thread = threading.Thread(target=self.get_product_details, args=([count_product, item]))
            threads.append(thread)
            thread.start()
            time.sleep(1) 

        for thread in threads:
            thread.join()


        # for i, item in enumerate(items):
        #     count_product = f"{int(i+1/len(items))}"
        #     # self.get_product_details(count_product, item)
        #     self.get_product_details(count_product, item)
    
            


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item_id):
        with self.semaphore:
            try:
                    
                    start = time.time()

                    url_item = f"https://www.offcorss.com/api/catalog_system/pub/products/search?fq=productId:{item_id}"
                    # params = {"languageId":-5, "showProducts": "false", "appId":1}
                    headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                    
                    response = requests.get(url_item, headers=headers)
                    response.raise_for_status()

                    if response.status_code == 200 or response.status_code == 206:
                        data = json.loads(response.content)
                        data = data[0]
                        name = data.get("productName")

                        href = data.get("link")
                        
                        duplicate_flag = [True for record in self.records if href == record["url item"]]
                    # for record in self.records:
                        if len(duplicate_flag):
                            return

                        categories = data.get("categories")[0].split("/")

                        categories = [i for i in categories if i != ""]

                        if len(categories) >= 4:
                            category, subcategory, subcategory_2, subcategory_3 = categories[0], categories[1], categories[2], categories[3]
                        elif len(categories) == 3:
                            category, subcategory, subcategory_2, subcategory_3 = categories[0], categories[1], categories[2], None
                        elif len(categories) == 2:
                            category, subcategory, subcategory_2, subcategory_3 = categories[0], categories[1], None, None
                        elif len(categories) == 1:
                            category, subcategory, subcategory_2, subcategory_3 = categories[0], None, None, None
                    

                        
                        sku = data.get("productId")

                        marca = data.get("brand")
                        
                        # ------------------------------------- descripción ----------------------------------------------------------- #
                        
                        composition_items = data.get("description")

                        description = data.get("description").replace("•\t", "").replace("\r", "|").replace("\n","")
                        materials = ""
                        
                        if "Composición" in composition_items:
                            materials = composition_items[composition_items.find("Composición:"):]
                            materials = materials[:materials.find("\n")]
                            materials = materials[:materials.find("¡Compra en OFFCORSS!")]
                            materials = materials.strip("Composición:").strip()
                            
                        elif "Material" in composition_items:
                            materials = composition_items[composition_items.find("Material"):]
                            materials = materials[:materials.find("\n")]
                            materials = materials[:materials.find("¡Compra en OFFCORSS!")]
                            materials = materials[:materials.find("Crea tu mejor outfit")]
                            materials = materials.strip("Materiales:").strip("Materiales:").strip()


                        cares_items = data.get("cuidados", ["No indicados"])

                        cares = ', '.join(cares_items)

                        made_in = [o.split(": ")[-1] for o in data.get("origen", []) if "País de origen" in o]
                        made_in = made_in[0] if len(made_in) else None

                        item_characteristics = f"Descripción: {description} | Cuidados: {cares}"
                        
                        color = data.get("Color")
                        color = data.get("items")[0].get("name").split(" ")[0] if color is None else color[0]

                        for i in data.get("items"):

                            image_url = i.get("images")[0].get("imageUrl")
                            

                            # ------------------------------------------------------------------------------------------------ #
                            #                                              prices                                              #
                            # ------------------------------------------------------------------------------------------------ #
                            offers = i.get("sellers")[0].get("commertialOffer")
                            price = offers.get("PriceWithoutDiscount")
                            
                            price_value = int(price)
                            final_price = price_value

                            sale_price = offers.get("Price")
                            sale_value = int(sale_price)

                            if sale_value < price_value:
                                final_price = sale_value
                                saving_value = f"-{round(100-sale_value*100/price_value)}%"

                            else:
                                sale_value, saving_value = None, None

                            size_value = i.get("Talla")
                            size_value = i.get("name").split(" ")[-1] if size_value is None else size_value[0]
                            stock_value = offers.get("IsAvailable")
                            stock = "available" if stock_value is True else "not available"
                            # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                            self.records.append(
                                    {
                                        "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                        "canal": "Offcorss Colombia",
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
                                        "url sku": OFFCORSS_URL,
                                        "image": image_url,
                                        "price": price_value,
                                        "sale_price": sale_price,
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
                            print(f"Offcorss {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
                
                    time.sleep(0.2)   
            except Exception as e:
                print(e)
                logging.error(f"Offcorss&Bear...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
                logging.info("Refresh page...")
                # driver.refresh()
                raise(e)
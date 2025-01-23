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

from settings import MANGO_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class mangoSession():
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
            logging.info(f"Excution Mango Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_MANGO.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=MANGO_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try: 
            # categories Mango
            # https://shop.mango.com/services/menu/v1.0/shop/desktop/CO/es

            # subcategories Mango
                # usar ID del primer submenu
            # https://shop.mango.com/ws-product-lists/v1/channels/shop/countries/co/catalogs/accesorios_she?language=es
                
            # product mango
            # https://shop.mango.com/services/garments/480/es/S/67063693

            url_category = "https://shop.mango.com/services/menu/v1.0/shop/desktop/CO/es"

            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
            response = requests.get(url_category, headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                data = json.loads(response.content)
                # category_ids = list()
                for i in data["menus"]:
                    category_menus = i["menus"]
                    self.scan_items(category_menus)
                    
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category"))
            logging.error(
                (f"details: {e}"))
        
# ------------------------------------------------------------------------------------------------ #
    
    def scan_items(self, category_menus):
        try:
            for subcategory in category_menus:
                url_category = f"https://shop.mango.com/ws-product-lists/v1/channels/shop/countries/co/catalogs/{subcategory['id']}?language=es"
                # params = {"languageId":-5, "showProducts": "false", "appId":1}
                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                
                response = requests.get(url_category, headers=headers)
                # response.raise_for_status()

                if response.status_code == 200:
                    data = json.loads(response.content)
                    ids = [item["id"].split(":")[0] for item in data["groups"][0]["items"]]
                    self.get_products(ids)
                elif response.status_code == 404:
                    if subcategory.get("menus") is not None:
                        self.scan_items(subcategory["menus"])
                    
                # driver.get(subcategory["href"])

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


# ------------------------------------------------------------------------------------------------ #
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
                    start = time.time()
                    category_dict = {"she": "Mujer", "he":"Hombre", "kids": "Ninos", "teen":"Teen"}
                    url_item= f"https://shop.mango.com/services/garments/480/es/S/{item}"
                    # params = {"languageId":-5, "showProducts": "false", "appId":1}
                    headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                    
                    response = requests.get(url_item, headers=headers)
                    response.raise_for_status()
                    
                    if response.status_code == 200:
                        data = json.loads(response.content)
                    
                        name = data.get("name")

                        href = data.get("canonicalUrl")
                        href = f"https://shop.mango.com{href}"
                        
                        duplicate_flag = [True for record in self.records if href == record["url item"]]
                    # for record in self.records:
                        if len(duplicate_flag):
                            return

                        category = data.get("brandId")
                        category = category_dict.get(category)

                        if category is None:
                            return
                        
                        subcategories = data.get("dataLayer").get("ecommerce").get("detail").get("products")[0].get("categories")
                        subcategories = [subcategory["name"].replace("-"," ") for subcategory in subcategories]
                        if len(subcategories) >= 3:
                            subcategory, subcategory_2, subcategory_3 = subcategories[0], subcategories[1], subcategories[2]
                        elif len(subcategories) == 2:
                            subcategory, subcategory_2, subcategory_3 = subcategories[0], subcategories[1], None
                        elif len(subcategories) == 1:
                            subcategory, subcategory_2, subcategory_3 = subcategories[0], None, None
                        else:
                            subcategory, subcategory_2, subcategory_3 = None, None, None

                        item_details = data.get("details")
                        
                        sku = data.get("refInfo").replace("REF. ","")

                        marca = "Mango"
                        
                        # ------------------------------------- descripción ----------------------------------------------------------- #
                        
                        composition_items = item_details.get("composition")

                        materials = composition_items.get("composition", "materiales no mostrados.")

                        cares_items = composition_items.get("washingRules")

                        if cares_items is not None:
                            cares = [care.get("text") for care in cares_items]

                            cares = ', '.join(cares)
                        else:
                            cares = "sin indicaciones de lavado."

                        made_in = item_details.get("manufacturingCountryName")
                        
                        description = item_details.get("descriptions")

                        text_description = description.get("bullets") 

                        text_description = description.get("capsules", ["Sin descripción"]) if text_description is None else text_description
                                                            
                        description = f'{", ".join(text_description)}. Medidas: {", ".join(description.get("measures", "medidas no indicadas."))}'

                        item_characteristics = f"Descripción: {description} || Composición: {materials} || Cuidados: {cares}"

                        for detail in data.get("colors").get("colors"):
                            
                            images = detail.get("images")

                            if images is None:
                                id_colors = detail.get("id")
                                photos = detail.get("productDataLayer").get("ecommerce").get("detail").get("products")[0].get("photosColor")
                                url = photos.get(id_colors).get("outfit")
                            else:
                                images = images[0]
                                url = [i.get("url") for i in images if "Plano general" in i.get("altText")]

                                if not len(url):
                                    url = images[0]["url"]
                                else:
                                    url = url[0]

                            image_url = f"https://st.mngbcn.com/rcs/pics/static{url}"
                            # Execute the command for make apear the detail bar
                            color = detail.get("label")

                            # ------------------------------------------------------------------------------------------------ #
                            #                                              prices                                              #
                            # ------------------------------------------------------------------------------------------------ #
                            price = detail.get("price").get("price")
                            
                            price_value = int(price)
                            final_price = price_value

                            sale_price = detail.get("crossedOutNumericPrices")

                            if sale_price is not None:
                                sale_price_value = price_value
                                # final_price = price_value
                                price_value = int(sale_price["0"])
                                saving_value = f"-{round(100-sale_price_value*100/price_value)}%"

                            else:
                                sale_price_value, saving_value = None, None

                            # ------------------------------------------------------------------------------------------------ #
                            #                                               Sizes                                              #
                            # ------------------------------------------------------------------------------------------------ #

                            sizes = detail.get("sizes")

                            if sizes is None:
                                sizes_available = detail.get("dataLayer").get("sizeAvailability")
                                sizes_stock = sizes_available.split(",") if not "ninguno" in sizes_available else list()
                                sizes_stock = [{"label": size, "stock":stock} for size, stock in zip(sizes_stock, ["stock"]*len(sizes_stock))]

                                sizes_notavailable = detail.get("dataLayer").get("sizeNoAvailability")
                                sizes_notstock = sizes_notavailable.split(",") if not "ninguno" in sizes_notavailable else list()
                                sizes_notstock = [{"label": size, "stock":stock} for size, stock in zip(sizes_notstock, [None]*len(sizes_notstock))]

                                sizes = sizes_stock + sizes_notstock
                                

                            for size in sizes:

                                size_value = size.get("label")
                                stock = size.get("stock")
                                stock = "available" if stock is not None else "not available"
                                # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                                self.records.append(
                                        {
                                            "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                            "canal": "Mango Colombia",
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
                                            "url sku": MANGO_URL,
                                            "image": image_url,
                                            "price": price_value,
                                            "sale_price": sale_price_value,
                                            "shipment cost": stock,
                                            "sales flag": saving_value,
                                            "store id": f"9999_mango_col",
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
                        print(f"Mango {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
                
                    time.sleep(0.2)   
            except Exception as e:
                print(e)
                logging.error(f"Mango...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
                logging.info("Refresh page...")
                # driver.refresh()
                raise(e)
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
from settings import KOAJ_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser




class koajSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_ae = open_browser()
            with WebDriver(driver_ae) as driver:
                self.open_page(driver)
                self.select_categories(driver)
            
            end = time.time()
            logging.info(f"Excution Koaj Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_KOAJ.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=KOAJ_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            categories = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(@class,'ma_level_1')]")))
            
            categories = [c.get_attribute("href") for c in categories if "precios especiales" not in c.get_attribute("innerText").lower()]

            categories = list(set(categories))

            for href_category in categories:
                try:
                    # Get and click on category button
                    driver.get(href_category)
                    
                    self.select_subcategory(driver, href_category)
                except Exception as e:
                    logging.error(f"An error ocurred: {e}")
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during report selection: {e}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_subcategory(self, driver, href_category: str):

        category_tree = driver.find_elements(By.XPATH,"//li[@itemprop='itemListElement']/a")
        if len(category_tree):
            category_tree.pop(0)
            category_tree = [c.get_attribute("title") for c in category_tree]
            category, subcategory = (category_tree[0], category_tree[1]) if len(category_tree)>1 else (category_tree[0], None)
            subcategory_2 = driver.find_element(By.XPATH,"//span[@class='navigation_page']").get_attribute("innerText")
            if subcategory is None:
                subcategory = subcategory_2
                subcategory_2 = None

        else:
            category_tree = href_category.replace(KOAJ_URL, "").split("/")
            if len(category_tree) >= 4:
                category, subcategory, subcategory_2 = category_tree[0:3]
                subcategory_2 = subcategory_2.replace("-", " ").title()
            elif len(category_tree) >= 3:
                category, subcategory = category_tree[0:2]
                subcategory = subcategory.replace("-", " ")
                subcategory_2 = None
            category, subcategory = category.title(), subcategory.title()
            

        subcategories_3 = driver.find_elements(By.XPATH,"//ul[@id='ul_layered_category_0']/li//a")
        subcategories_3 = [sub.get_attribute("innerText") for sub in subcategories_3]
        if len(subcategories_3):
            root_url= f"{href_category}#/categorias-"
            try:
                for subcategory_3 in subcategories_3:
                    
                    subcategory_3 = subcategory_3
                    if subcategory_3.lower() == category.lower():
                        continue
                    else:
                        url_sub = f"{root_url}{subcategory_3.lower().replace(' ', '_')}"
                        
                        driver.get(url_sub)
                        colors = driver.find_elements(By.XPATH,"//label[contains(@class,'layered_color')]/a")
                        colors = [col.get_attribute("innerText") for col in colors]
                        for color in colors:
                            color_name = color
                            url_color = f"{url_sub}/colores-{color_name.lower().replace(' ', '_')}"
                        
                            href_items = self.pagination_items(driver, url_color)
                            if subcategory_2 is None:
                                subcategory_2 = subcategory_3
                                subcategory_3 = None
                            self.get_product_details(driver, href_items, color_name, category, subcategory, subcategory_2, subcategory_3)

            except TimeoutException:
                logging.error(f"Exception while scrolling page:  {e}")
                logging.info("Reloading page...")
                driver.refresh()
            except Exception as e:
                logging.error(f"An error ocurred: {e}")
        else:
            colors = driver.find_elements(By.XPATH,"//label[contains(@class,'layered_color')]/a")
            colors = [col.get_attribute("innerText") for col in colors]
            for color in colors:
                color_name = color
                url_sub = f"{href_category}#/colores-{color_name.lower().replace(' ', '_')}"
                href_items = self.pagination_items(driver, url_sub)
                self.get_product_details(driver, href_items, color_name, category, subcategory, subcategory_2, None)

# ------------------------------------------------------------------------------------------------ #
    def pagination_items(self, driver, url_sub):
        url = url_sub
        time.sleep(10)
        driver.get(url)
        pagination = driver.find_elements(By.XPATH, "//div[@id='pagination_bottom']/ul/li")

        last_page = pagination[-2].get_attribute("innerText") if len(pagination) else 1
        
        href_items = list()
        page = 1
        while page <= int(last_page):
            products = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@id,'product_list')]/li//a[contains(@class,'product_img_link')]")))
            
            _items = [c.get_attribute("href") for c in products if not c.get_attribute("href") in href_items]
            href_items.extend(_items)

            page += 1
            url = f"{url_sub}/page-{page}"
            driver.get(url)
            
            print(len(href_items))
        return href_items
            
# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, href_items: list[str], color:str, category:str, subcategory:str, subcategory_2:str, subcategory_3:str):
        for i, href in enumerate(href_items):
            try:
                start = time.time()

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
                if len(duplicate_flag):
                    continue

                driver.get(href)

                item = driver.find_element(By.XPATH, "//div[@id='product_name_wrap']/h1").get_attribute("innerText")
                sku = driver.find_element(By.XPATH, "//span[contains(@itemprop, 'sku')]").get_attribute("innerText")

                image = driver.find_element(By.XPATH, "//div[@id='bigpic']/a/img").get_attribute("src")

                marca = "Koaj"

                price = driver.find_element(By.ID, "old_price")
                
                price_value = int(driver.find_element(By.ID, "our_price_display").get_attribute("content"))
                final_price = price_value

                if "hidden" not in price.get_attribute("class"):
                    price = price.get_attribute("innerText")
                    price = int(price.replace("$","").replace(",",""))
                    sale_price = price_value
                    saving = driver.find_elements(By.XPATH, "//span[contains(@class,'on_sale')]")
                    if len(saving):
                        saving = saving[0].get_attribute("innerText")
                    else:
                        saving = f"-{round(100-sale_price*100/price)}%"
                else:
                    price = price_value
                    sale_price, saving = None, None

                # price = int(price.replace(".",""))

                # ------------------------------------- descripción ----------------------------------------------------------- #
                description_tab = driver.find_element(By.ID, "description-tab")
                driver.execute_script("arguments[0].click()",description_tab)
                description = driver.find_element(By.ID, "product_tabs_content").get_attribute("innerText")

                features_tab = driver.find_element(By.ID, "features-tab")
                driver.execute_script("arguments[0].click()",features_tab)

                features_table = driver.find_elements(By.XPATH,"//table[contains(@class, 'table-data-sheet')]//tr")
                # rows = features_table.find_elements(By.XPATH,"//tr")

                data_table = dict()
                for row in features_table:
                    cells = row.find_elements(By.TAG_NAME,"td")
                    key = cells[0].get_attribute("innerText")
                    value = cells[1].get_attribute("innerText")
                    data_table[key] =  value
                    

                made_in = data_table.get('Pais de Origen', 'sin información')

                materials = data_table.get('Composición', 'sin información')

                item_characteristics = f"Descripción: {description} || Composición: {data_table.get('Composición', 'sin información')} || Lavado: {data_table.get('Lavado', 'sin información')}"
                # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                sizes_stock = driver.find_elements(By.XPATH, "//div[@class='sd_select_option ']")
                sizes_out_stock = driver.find_elements(By.XPATH, "//div[contains(@class, 'sd_select_option disabled')]//div[contains(@class, 'sd_select_option-name')]")

                sizes_stock = [(size.get_attribute("innerText"),"available") for size in sizes_stock]
                sizes_out_stock = [(size.get_attribute("innerText"),"not available") for size in sizes_out_stock]

                for size, stock in sizes_stock + sizes_out_stock:
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    size = size.split("\n")[0]
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Koaj Colombia",
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
                                "url sku": KOAJ_URL,
                                "image": image,
                                "price": price,
                                "sale_price": sale_price,
                                "shipment cost": stock,
                                "sales flag": saving,
                                "store id": f"9999_koaj_col",
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
                print(f"Koaj {category} {subcategory} {subcategory_2}  {subcategory_3} item {i+1}/{len(href_items)}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
            except Exception as e:
                print(e)
                logging.error(f"Koaj...Error get product details {category} {subcategory} {subcategory_2}: {e}")
                # logging.info("Refresh page...")
                driver.refresh()
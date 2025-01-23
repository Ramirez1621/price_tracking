import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests


from os.path import join
from base64 import b64encode
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import ARTURO_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["hombre", "colore", "freedom", "mujer", "kids", "viaje"]

class arturocalleSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            # driver_arturo = open_browser()
            # with WebDriver(driver_bershka) as driver:
            # self.open_page(driver_arturo)
            time.sleep(5)
            self.select_categories()
            # driver_arturo.quit()
            
            end = time.time()
            logging.info(f"Excution ArturoCalle Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_ARTURO.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=ARTURO_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self):
        try:
            
            for category in INCLUSION_LIST:
                start = 0
                end = 49
                while True:
                    query_string = '{"hideUnavailableItems":false,"skusFilter":"ALL_AVAILABLE","installmentCriteria":"MAX_WITHOUT_INTEREST","category":"%s","collection":"","specificationFilters":[],"orderBy":"","from":%d,"to":%d,"shippingOptions":[],"variant":""}' % (category, start, end)
                    query_b64  = query_string.encode()

                    query = b64encode(query_b64)

                    url_category = 'https://www.arturocalle.com/_v/segment/graphql/v1?workspace=master&maxAge=short&appsEtag=remove&domain=store&locale=es-CO&operationName=Products&variables={}&extensions={"persistedQuery":{"version":1,"sha256Hash":"9b475e0aef97f309715db0071b1c7430f237580f86ce06a53e946ca823ec24bd","sender":"vtex.store-resources@0.x","provider":"vtex.search-graphql@0.x"},"variables":"%s"}' % query.decode()

                    headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
                    
                    response = requests.get(url_category, headers=headers)

                    if response.status_code == 200:
                        data = json.loads(response.content)

                        items = data.get('data').get('products')
                        if len(items) == 0:
                            break
                        self.get_products(items)
                        start += 50
                        end += 50
                    elif response.status_code == 400:
                        break

            # categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
            #             (By.XPATH, "//a[contains(@id,'menu-item-category-')]")))
            
            # categories = [{"href": c.get_attribute("href")} for c in categories]

            # for category in categories:
            #     try:
            #         self.select_subcategory(driver, category)
            #     except Exception as e:
            #         logging.error(f"An error ocurred: {e}")
            #         continue
        
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category: {category}"))
            logging.error(
                (f"details: {e}"))

    def select_subcategory(self, driver, category):
        try:
            href = category["href"]
            
            driver.get(href)

            items = self.pagination_items(driver, href)
            self.get_products(driver, items)
            pass
            # for subcategory in subcategories:
            #     self.select_subcategory2(driver, category, subcategory)

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan category: {href}"))
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

        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategory3: {items['subcategory3']}"))
            logging.error(
                (f"details: {e}"))

# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, items):
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            self.get_product_details(count_product, item)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item):
        try:
                start = time.time()

                href = ARTURO_URL + item.get('link')

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
                if len(duplicate_flag):
                    return

                name = item.get('productName').replace('\n', '')

                marca = item.get('brand')

                # ------------------------------------------------------------------------------------------------ #
                #                                    categories and name details                                   #
                # ------------------------------------------------------------------------------------------------ #
                
                categories = item.get('categories', ['/'])[0].split('/')
                categories = [i for i in categories if i != ""]

                # categories = content_cat["itemListElement"]
                # categories.pop(-1)
                # if len(categories) >= 4:
                #     category, subcategory, subcategory_2, subcategory_3 = categories[0].get("name"), categories[1].get("name"), categories[2].get("name"), categories[3].get("name")
                # elif len(categories) == 3:
                #     category, subcategory, subcategory_2, subcategory_3 = categories[0].get("name"), categories[1].get("name"), categories[2].get("name"), None
                # elif len(categories) == 2:
                #     category, subcategory, subcategory_2, subcategory_3 = categories[0].get("name"), categories[1].get("name"), None, None
                # elif len(categories) == 1:
                #     category, subcategory, subcategory_2, subcategory_3 = categories[0].get("name"), None, None, None
                # else:
                #     return
                category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]

                # ------------------------------------------------------------------------------------------------ #
                #                                 descipción, materiales y cuidados                                #
                # ------------------------------------------------------------------------------------------------ #
                # WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH,"//button[contains(text(),'Composición')]"))).click()
                
                composition_items = item.get("properties")

                item_characteristics = ""

                for comp in composition_items:
                    item_characteristics += f"{comp.get('name')} "
                    item_characteristics += comp.get("values")[0]
                    item_characteristics += " | "


                patron = r'\b(?:Composici[oó]n).*?</li>'
                patron_2 = r'\b(?:Pa[ií]s de Origen).*?</li>'

                made_in = re.findall(patron_2, item_characteristics, re.IGNORECASE)
                materials = re.findall(patron, item_characteristics, re.IGNORECASE)

                patron_3 = r'\b(?:>).*?<'
                made_in = re.findall(patron_3, made_in[0], re.IGNORECASE)[0].strip("><") if len(made_in) else None
                materials = re.findall(patron_3, materials[0], re.IGNORECASE)[0].strip("><") if len(materials) else None

                item_characteristics = re.sub('<[^<]+?>', '', item_characteristics)

                item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                for i in item.get("items"):
                            
                    image_url = i.get("images", [{}])[0].get("imageUrl")
                    
                    sku = i.get('ean')
                    # ------------------------------------------------------------------------------------------------ #
                    #                                              prices                                              #
                    # ------------------------------------------------------------------------------------------------ #
                    offers = i.get("sellers", [{}])[0].get("commertialOffer")
                    price = offers.get("PriceWithoutDiscount")
                    
                    price_value = int(price)
                    final_price = price_value

                    sale_price = offers.get("Price")
                    sale_price_value = int(sale_price)

                    if sale_price_value < price_value:
                        final_price = sale_price_value
                        saving_value = f"-{round(100-sale_price_value*100/price_value)}%"

                    else:
                        sale_price_value, saving_value = None, None

                    # ------------------------------------------------------------------------------------------------ #
                    #                                               Sizes                                              #
                    # ------------------------------------------------------------------------------------------------ #

                    variations = i.get("variations")
                    variations_value = {v.get("name"):v.get("values") for v in variations}

                    color_name = variations_value.get("Colores", [""])[0]
                    size_value = variations_value.get("Talla", [""])[0]

                    # stock_value = offers.get("IsAvailable")
                    stock = "available"

                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Arturo Calle Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": marca,
                                "modelo": color_name,
                                "sku": sku,
                                "upc": f"{sku}_{color_name}_{size_value}",
                                "item": name,
                                "item_characteristics": item_characteristics,
                                "url sku": ARTURO_URL,
                                "image": image_url,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_arturocalle_col",
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
                print(f"ArturoCalle {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"ArturoCalle...Error get product details {category} {subcategory} {subcategory_2}... {type(e)} Message: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
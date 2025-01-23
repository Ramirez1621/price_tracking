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
from settings import ARTURO_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["party", "new", "colaboraciones®", "special prices", "gift ideas", "lo más vendido", "nuevo esta semana", "ver todo", "total look"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class arturocalleSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_arturo = open_browser()
            # with WebDriver(driver_bershka) as driver:
            self.open_page(driver_arturo)
            time.sleep(5)
            self.select_categories(driver_arturo)
            driver_arturo.quit()
            
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
    def select_categories(self, driver):
        try: 
            categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(@id,'menu-item-category-')]")))
            
            categories = [{"href": c.get_attribute("href")} for c in categories]

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
    def pagination_items(self, driver, href):
        
        items = list()
        page = 1
        time.sleep(2)
        start = time.time()
        end = 0
        while (end - start) < 1800:
            try: 
                _items = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//section/a")))

                _items = [c.get_attribute("href") for c in _items if not c.get_attribute("href") in items]

                items.extend(_items)
                
                page += 1
                url_next = f"{href}?layout=grid&page={page}"
                driver.get(url_next)
                time.sleep(3)

                no_content = driver.find_elements(By.XPATH, '//div[contains(@class,"vtex-search-result-3-x-searchNotFound")]')

                if len(no_content):
                    break
                    
                end = time.time()
            
            except TimeoutException:
                no_content = driver.find_elements(By.XPATH, '//div[contains(@class,"vtex-search-result-3-x-searchNotFound")]')

                if len(no_content):
                    break
            # scroll_position = driver.execute_script("return window.scrollY+document.documentElement.clientHeight;")
            # scroll_end = driver.execute_script("return document.body.scrollHeight;")

            # if scroll_position != scroll_end:
            #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # else:
            #     break

        print(len(items))
        return items
            
# ------------------------------------------------------------------------------------------------ #
    def retry_exception(self):
        print("retrying...")
        return

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
# ------------------------------------------------------------------------------------------------ #
    # @timeout(60, use_signals=False, timeout_exception=TimeoutError)  # 10 segundos de timeout
    def get_products(self, driver: Firefox, href_items):
        for i, href in enumerate(href_items):
            count_product = f"{int(i+1/len(href_items))}"
            self.get_product_details(driver, count_product, href)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, count_product, href):
        try:
                start = time.time()

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                # for record in self.records:
                if len(duplicate_flag):
                    return
                
                driver.get(href)

                # content //div[contains(@class,'vtex-product')]//script[contains(@type,'application/ld+json')]
                # marca = "Arturo Calle"

                # ------------------------------------------------------------------------------------------------ #
                #                                 descipción, materiales y cuidados                                #
                # ------------------------------------------------------------------------------------------------ #
                # WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH,"//button[contains(text(),'Composición')]"))).click()
                
                composition_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//td[contains(@class,'vtex-store-components-3-x-specificationItemSpecifications--especificacionesdeta')]//li")))

                materials = ""
                made_in = None
                for comp in composition_items:
                    type_comp = comp.get_attribute("innerText")
                    if "composición" in type_comp.lower():
                        materials = type_comp
                    elif "origen" in type_comp.lower():
                        made_in = type_comp.split(": ")[-1]

                cares_items = driver.find_elements(By.XPATH,"//td[contains(@class,'vtex-store-components-3-x-specificationItemSpecifications--especificacionesapli')]//li")

                cares = ", ".join([ c.get_attribute("innerText") for c in cares_items]) if len(cares_items) else "No especificado"
                
                description = driver.find_elements(By.XPATH,"//div[contains(@class,'vtex-store-components-3-x-productDescriptionText')]")
                
                description_button = driver.find_element(By.XPATH,"//div[contains(@class,'trigger--pdp-details')]")
                driver.execute_script("arguments[0].click();", description_button)

                description = description[0].get_attribute("innerText") if len(description) > 0 else ""

                item_characteristics = f"Descripción: {description} || {materials} || Lavado: {cares}"

                item_characteristics = item_characteristics.replace(";",",")
                item_characteristics = item_characteristics.replace("\n","")
                materials = materials.replace("\n","")


                # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                # ------------------------------------------------------------------------------------------------ #
                #                                              precio                                              #
                # ------------------------------------------------------------------------------------------------ #

                patron = r"[^0-9 ]"
                
                price = driver.find_element(By.XPATH, "//div[contains(@class,'flexRow--contenedorP')]//span[contains(@class,'vtex-product-price-1-x-sellingPriceValue')]")
                
                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                final_price = price_value

                sale_price = driver.find_elements(By.XPATH, "//div[contains(@class,'flexRow--contenedorP')]//span[contains(@class,'vtex-product-price-1-x-listPrice')]")

                if len(sale_price):
                    sale_price_value = price_value
                    price_value = int(re.sub(patron, "", sale_price[0].get_attribute("innerText") ))
                    final_price = sale_price_value
                    
                    saving = abs(round(100-sale_price_value*100/price_value))
                    if saving == 0 :
                        sale_price_value, saving_value = None, None
                    else:
                        saving_value = f"-{saving}%"
                else:
                    sale_price_value, saving_value = None, None

                # ------------------------------------------------------------------------------------------------ #
                #                                              tallas                                              #
                # ------------------------------------------------------------------------------------------------ #

                try:
                    colors_button = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class,'skuSelectorSubcontainer--colores')]//div[contains(@class,'skuSelectorOptionsList')]/div[contains(@class,'skuSelectorItem--selectorPrimario')]")))
                except TimeoutException:
                    colors_button = driver.find_elements(By.XPATH, "//div[contains(@class,'skuSelectorSubcontainer--colores')]//div[contains(@class,'skuSelectorOptionsList')]/div[contains(@class,'skuSelectorItem--selectorPrimario')]")


                if not len(colors_button):
                    colors_button = ["Unicolor"]


                for i in range(len(colors_button)):
                    if not isinstance(colors_button[i],str):
                        driver.execute_script("arguments[0].click();", colors_button[i])
                        colors_button = driver.find_elements(By.XPATH, "//div[contains(@class,'skuSelectorSubcontainer--colores')]//div[contains(@class,'skuSelectorOptionsList')]/div[contains(@class,'skuSelectorItem--selectorPrimario')]")
                        color_name = colors_button[i].get_attribute("innerText")
                        
                    else:
                        color_name = colors_button[i]

                    # ------------------------------------------------------------------------------------------------ #
                    #                                    categories and name details                                   #
                    # ------------------------------------------------------------------------------------------------ #

                    name_json = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[contains(@class,'flex-column')]/script[contains(@type, 'json')]")))
                    
                    content = name_json.get_attribute("innerText")
                    content = json.loads(content)

                    name = content.get("name", "S/N").replace("\n", "")
                    image = content.get("image")
                    # description = content.get("description")
                    sku = content.get("mpn")

                    marca = content.get("brand").get("name")
                    categories_json = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                                    (By.XPATH, "//div[contains(@class,'stretchChildrenWidth')]/script[contains(@type, 'json')]")))
                    
                    content_cat = categories_json.get_attribute("innerText")
                    content_cat = json.loads(content_cat)

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
                    
                    categories = [ c.get("name")  for c in content_cat["itemListElement"]][:4]
                    category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]

                    sizes_stock = driver.find_elements(By.XPATH, "//div[contains(@class,'skuSelectorSubcontainer--talla')]//div[contains(@class,'vtex-store-components-3-x-skuSelectorItem--selectorPrimario') and not(contains(@class,' vtex-store-components-3-x-unavailable'))]")
                    sizes_out_stock = driver.find_elements(By.XPATH, "//div[contains(@class,'skuSelectorSubcontainer--talla')]//div[contains(@class,'vtex-store-components-3-x-skuSelectorItem--selectorPrimario') and contains(@class,' vtex-store-components-3-x-unavailable')]")

                    if len(sizes_stock) == 0 and len(sizes_out_stock) == 0:
                        sizes_stock = [("Talla única", "available")]
                    else:
                    # elif len(sizes_stock) == 1 and len(sizes_out_stock) == 0:
                        sizes_stock = [(size.get_attribute("innerText"),"available") for size in sizes_stock]
                        sizes_out_stock = [(size.get_attribute("innerText"),"not available") for size in sizes_out_stock]
                    # Execute the command for make apear the detail bar

                    for size, stock in sizes_stock + sizes_out_stock:
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
                                    "upc": f"{sku}_{color_name}_{size}",
                                    "item": name,
                                    "item_characteristics": item_characteristics,
                                    "url sku": ARTURO_URL,
                                    "image": image,
                                    "price": price_value,
                                    "sale_price": sale_price_value,
                                    "shipment cost": stock,
                                    "sales flag": saving_value,
                                    "store id": f"9999_arturocalle_col",
                                    "store name": "ONLINE",
                                    "store address": "ONLINE",
                                    "stock": size,
                                    "upc wm": sku,
                                    "final_price": final_price,
                                    "upc wm2": sku,
                                    "comp": None,
                                    "composition": materials,
                                    "made_in": made_in,
                                    "url item": driver.current_url,
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
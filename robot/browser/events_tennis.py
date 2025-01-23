import logging
import datetime as dt
import time
import pandas as pd
import json
import re

from os.path import join

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import TENNIS_URL, TENNIS_CATEGORIES
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
from .web_driver import WebDriver, open_browser


class tennisSession():
    def __init__(self):
        self.records = list()
    
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            driver_tennis = open_browser()
            # with WebDriver(driver_bershka) as driver:
            self.open_page(driver_tennis)
            time.sleep(5)
            self.select_categories(driver_tennis)
            driver_tennis.quit()
            
            end = time.time()
            logging.info(f"Excution Tennis Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_TENNIS.csv"), index=False)

    def open_page(self, driver: Firefox):
        try:
            driver.get(url=TENNIS_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)


    def select_categories(self, driver: Firefox):
        try:
            for category in TENNIS_CATEGORIES:
                # Get and click on category button
                driver.get(category)
                
                self.select_subcategory(driver, category)
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))

    def select_subcategory(self, driver: Firefox, category: str):
        href_items = list()
        i = 2
        while True:
            try:
                items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//a[contains(@class,'vtex-product-summary-2-x-clearLink')]")))
            except TimeoutException:
                break
            else:
                _ = [item.get_attribute('href') for item in items if item.get_attribute('href') is not None]
                href_items.extend(_)
                
                page_url = f"{category}?page={i}"
                driver.get(page_url)
                i += 1

        self.get_product_details(driver, href_items)

    def select_subcategories2(self, driver: Firefox):
        try:
            subcategories2 = WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                    (By.XPATH, "//a[contains(@class,'category-topbar-related-categories__category-link link')]")))
        
            for i in range(1, len(subcategories2)):
                    subcategories2 = WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                        (By.XPATH, "//a[contains(@class,'category-topbar-related-categories__category-link link')]")))
                    self.record["subcategory_2"] = subcategories2[i].get_attribute("innerText")
                    # Click on subcategory 2
                    subcategories2[i].click()
                    self.select_product(driver)
                    time.sleep(4)    
        except TimeoutException:
            self.record["subcategory_2"] = None
            self.select_product(driver)

    def retry_exception(self):
        return

    @retry(wait=wait_random_exponential(min=2, max=20), stop=stop_after_attempt(4), reraise=False, retry_error_callback=retry_exception)
    def select_product(self, driver: Firefox):
        try:
            # Switch to grid view
            grid_selector = driver.find_elements(By.XPATH, "//button[contains(@class,'view-option-selector-button')]")
            grid_selector[-1].click()
        except IndexError:
            return
        else:
            # Scan the page for the products
            items =  WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")))
            href_items = list()
            new_items = items

            try:
                while len(new_items):
                
                    href = [item.get_attribute('href') for item in new_items if item.get_attribute('href') is not None]
                    href_items.extend(href)
                    
                    # Scroll to the finish of the page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    # Wait for load new content
                    time.sleep(1)
                    ref_items = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                        (By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")))
                    
                    new_items = [item for item in ref_items if item not in items]
                    items.extend(new_items)

            except Exception as e:
                print(e)
                logging.error(f"Exception selecting product: {e}")
            
            href_items = list(set(href_items))
            # Open a new Window on the browser
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            # get the products details
            self.get_product_details(driver, href_items)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            driver.execute_script("window.scrollTo(0, 0)")
            print(self.records)

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
        
    @retry(wait=wait_random_exponential(min=2, max=20), stop=stop_after_attempt(4), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, href_items: list[str]):
        for href in href_items:
            try:
                driver.get(href)

                json_item = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                    By.XPATH, "//div[not(@class='')]/script[contains(@type,'json')]"
                    )))
                content_item = json_item.get_attribute("innerText")
                content_item = json.loads(content_item)
                # content_item = content_item["itemListElement"]

                json_categories = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                    By.XPATH, "//div[@class='']/script[contains(@type,'json')]"
                    )))
                content = json_categories.get_attribute("innerText")
                content = json.loads(content)
                content = content["itemListElement"]

                # item = self.get_attribute(driver, "//h1[contains(@class,'vtex-store-components-3-x-productNameContainer')]", wait_time=10)
                item = content_item["name"]
                sku = self.get_attribute(driver, "//span[contains(@class, 'vtex-product-identifier-0-x-product-identifier__value')]")
                # category = self.get_attribute(driver, "//span[contains(@class, 'vtex-breadcrumb-1-x-arrow vtex-breadcrumb-1-x-arrow--1')]")
                # subcategory = self.get_attribute(driver, "//span[contains(@class, 'vtex-breadcrumb-1-x-arrow vtex-breadcrumb-1-x-arrow--2')]")
                if len(content) > 3:
                    category, subcategory, subcategory_2 = content[0].get("name"), content[1].get("name"), content[2].get("name")
                elif len(content) > 2:
                    category, subcategory, subcategory_2 = content[0].get("name"), content[1].get("name"), None
                else:
                    category, subcategory, subcategory_2 = content[0].get("name"),None, None

                # subcategory_2 = driver.find_elements(By.XPATH, "//span[contains(@class, 'vtex-breadcrumb-1-x-arrow vtex-breadcrumb-1-x-arrow--3')]")
                
                # subcategory_2 = subcategory_2[0].get_attribute("innerText") if len(subcategory_2) else None

                # image = self.get_attribute(driver, "//img[contains(@class, 'tennis-store-4-x-productImageTag tennis-store-4-x-productImageTag--main')]", type_checking="visibility_of_element_located", attribute="src")
                image = content_item["image"]
                marca = content_item["brand"]["name"]
                # WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                #     (By.XPATH, "//section[contains(@class, 'vtex-product-summary-2-x-container vtex-product-summary-2-x-containerNormal overflow-hidden')]")))
                # Click and open item characteristics
                WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@id, 'headlessui-disclosure-button-1')]")))

                buttons = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@id, 'headlessui-disclosure-button')]")))

                for button in buttons: driver.execute_script("arguments[0].click();", button)
                
                description = self.get_attribute(driver, "//div[contains(@class, 'tennis-store-4-x-itemSpecificationValue')]")

                description_items = description.split("\n")
                
                index_color = description.lower().find("color:")

                patron = "\.|\,|\•|\n|\:|\!| "

                color = description[index_color:].split(" ")[1].split("\n")[0] if index_color > 0 else None #.replace("\n","").replace("•","")

                color = re.sub(patron, "", color)
                
                materials = [item.split(": ")[-1] for item in description_items if "material" in item.lower()]

                materials = materials[0].split("Sobre el fit")[0] if len(materials) else None

                # _ = description.split("\n")
                
                # color = _[_.index("Características")+1].split(": ")[-1]

                description = description.replace("\n", " | ")
                # description = content_item["description"]
                
                care_instructions = self.get_attribute(driver, "//div[contains(@id,'headlessui-disclosure-panel-6')]")

                item_characteristics = f"DESCRIPCIÓN: {description} | INSTRACCUIONES DE CUIDADO: {care_instructions}"
                
                price = driver.find_element(By.XPATH, "//span[contains(@class,'vtex-product-price-1-x-sellingPriceValue') and not(ancestor::ul)]").get_attribute("innerText").replace("$\xa0","")
                price = int(price.replace(".",""))
                final_price = price

                saving = driver.find_elements(By.XPATH, "//span[contains(@class,'vtex-product-price-1-x-savingsPercentage') and not(ancestor::ul)]")

                if len(saving):
                    saving = saving[0].get_attribute("innerText").replace("\xa0"," ")
                    sale_price = driver.find_element(By.XPATH, "//span[contains(@class,'vtex-product-price-1-x-listPriceValue strike') and not(ancestor::ul)]").get_attribute("innerText").replace("$\xa0","")
                    sale_price = int(sale_price.replace(".","").replace("$",""))
                    price = sale_price
                    sale_price = final_price
                else:
                    sale_price, saving = None, None
                
                
                sizes_available = driver.find_elements(By.XPATH, "//div[contains(@class, 'vtex-store-components-3-x-skuSelectorItemTextValue') and not(contains(@class,' vtex-store-components-3-x-valueWrapper--unavailable')) and not(ancestor::ul)]")

                sizes_unavailable = driver.find_elements(By.XPATH, "//div[contains(@class, 'vtex-store-components-3-x-valueWrapper--unavailable vtex-store-components-3-x-skuSelectorItemTextValue') and not(ancestor::ul)]")
        
                for _size in sizes_available:
                    size = _size.get_attribute("innerText").replace("\n", "")
                    # stock = "not available" if "vtex-store-components-3-x-diagonalCross" in _size.get_attribute("innerText")

                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Tennis Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": None,
                                "marca": marca,
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size}",
                                "item": item,
                                "item_characteristics": item_characteristics,
                                "url sku": TENNIS_URL,
                                "image": image,
                                "price": price,
                                "sale_price": sale_price,
                                "shipment cost": "available",
                                "sales flag": saving,
                                "store id": f"9999_tennis_col",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": materials,
                                "made_in": None,
                                "url item":href,
                            }
                        )
                for _size in sizes_unavailable:
                    size = _size.get_attribute("innerText")
                    # stock = "not available" if "vtex-store-components-3-x-diagonalCross" in _size.get_attribute("innerText")

                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "Tennis Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": None,
                                "marca": "Tennis",
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size}",
                                "item": item,
                                "item_characteristics": item_characteristics,
                                "url sku": TENNIS_URL,
                                "image": image,
                                "price": price,
                                "sale_price": sale_price,
                                "shipment cost": "not available",
                                "sales flag": saving,
                                "store id": f"9999_tennis_col",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": materials,
                                "made_in": None,
                                "url item":href,
                            }
                        )

                
            except Exception as e:
                logging.error(f"Exception getting details: {e}")
                print(e)

    def get_details(self, driver):
        sku = self.get_attribute(driver, "//html", attribute="id").replace("product-","")

        
        
        price = self.get_attribute(driver, "//div[contains(@class,'product-detail-info__price-amount')]//descendant::span[contains(@class,'money-amount__main')]", type_checking="visibility_of_element_located").replace(" COP","")

        price = int(price.replace(".",""))

        color = self.get_attribute(driver, "//p[contains(@class,'product-color-extended-name')]").split(" | ")[0].replace("Color: ","")

        image = self.get_attribute(driver, "//img[contains(@class,'media-image__image media__wrapper--media') and contains(@src,'6_1_1.jpg')]", attribute="src")

        made_in = self.get_attribute(driver, "//div[contains(@class,'product-detail-extra-detail__section')]/div/span[contains(@class,'structured-component-text zds-paragraph-m')]/span", type_checking="presence_of_all_elements_located").replace("Hecho en ", "")

        materials = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@data-observer-key,'materials')]/div[contains(@class,'structured-component-text')]")))
        materials.pop(0), materials.pop(0)
        materials = " ".join([line.get_attribute("innerText") for line in materials])

        stock_sizes = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@class,'size-selector__size-list')]/li")))
        sizes = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//child::div[contains(@class,'product-size-info__main-label')]")))

        for _size, in_stock in zip(sizes, stock_sizes):
            stock = "available" if in_stock.get_attribute("data-qa-action") == "size-in-stock" else "not available"
            size = _size.get_attribute("innerText")
            

    def get_attribute(self, driver, xpath_string, wait_time=5, attribute="innerText", type_checking="presence_of_element_located", index=-1):
        try:
            if type_checking == "presence_of_element_located":
                element =  WebDriverWait(driver, wait_time).until(EC.presence_of_element_located(
                    (By.XPATH, xpath_string)))
            elif type_checking == "presence_of_all_elements_located":
                element = WebDriverWait(driver, wait_time).until(EC.presence_of_all_elements_located(
                    (By.XPATH, xpath_string)))[index]
            elif type_checking == "visibility_of_element_located":
                element = WebDriverWait(driver, wait_time).until(EC.visibility_of_element_located(
                    (By.XPATH, xpath_string)))
            
            return element.get_attribute(attribute)
        
        except TimeoutException:
            return None
        except Exception as e:
            print(e)
            logging.error(f"Exception getting attributes: {e}")
        

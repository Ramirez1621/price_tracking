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
from settings import HM_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["Rebajas", "Sostenibilidad", "Ofertas"]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class hmSession():
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
            logging.info(f"Excution H&M Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_HM.csv"), index=False)
        # return self.records

    def open_page(self, driver):
        try:
            driver.get(url=HM_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

# ------------------------------------------------------------------------------------------------ #
    def select_categories(self, driver):
        try: 
            categories = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//ul[contains(@class,'brandlive-menu-generator')]/li[contains(@class,'brandlive-menu-generator')]")))
            
            sub_sections = [ 
                            category.find_elements(By.XPATH, ".//ul[contains(@class,'brandlive-menu-generator-0-x-subLevel--level1')]/li")
                            for category in categories
                            if category.find_element(By.XPATH, "./a").get_attribute("innerText") not in EXCLUSION_LIST
                            ]
            
            subcategories_list = []
            for sub_section in sub_sections:
                for _ in sub_section:
                    sub_section_name = _.find_element(By.XPATH, "./a").get_attribute("innerText")
                    if sub_section_name not in EXCLUSION_LIST:
                        subcategories = _.find_elements(By.XPATH, ".//ul/li/a")
                        href_list = [
                                    subcategory.get_attribute("href")
                                    for subcategory in subcategories 
                                    if subcategory.get_attribute("innerText") == "Ver todo"
                                    ]
                        subcategories_list.extend(href_list)

            for subcategory in subcategories_list:
                    print(subcategory)
                    self.select_subcategory(driver, subcategory)
        
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan categories"))
            logging.error(
                (f"details: {e}"))

    def select_subcategory(self, driver, href_subcategory):
        try:
            driver.get(href_subcategory)
            # filter_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH,f"//div[contains(@class,'pointer') and @role='button']")))

            # for button in filter_buttons:
            #     button_name = button.find_element(By.XPATH, './/span[contains(@class,"filterTitleSpan")]')
            #     if "Tipo de producto" in button_name:
            #         driver.execute_script("arguments[0].click();", button_name)

            type_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located(
                    (By.XPATH,"//div[contains(@class,'item_filters_primary')]//div[contains(@class, 'filterContent')]//input[contains(@id,'tipo-de-producto')]")))
            
            time.sleep(1)
            buttons_map = []
            for button in type_buttons:
                button_name = button.get_attribute("name")
                # print(button_name)
                duplicate_object = [True for _ in buttons_map if button_name == _.get("name")]
                if duplicate_object:
                    continue
                buttons_map.append({"object": button, "name": button_name})
# //div[contains(@class, 'item_filters_primary')]//input[contains(@id,'tipo-de-producto')]

            for button in buttons_map:
                time.sleep(2)
                driver.execute_script("arguments[0].click();", button["object"])
                if not button["object"].is_selected():
                    driver.execute_script("arguments[0].click();", button["object"])
                time.sleep(2)
                items = self.pagination_items(driver)
                items = list({d["@id"]: d for d in items}.values())
                self.get_products(driver,items, subcategory_3=button["name"])
                driver.execute_script("arguments[0].click();", button["object"])


        except Exception as e:
            logging.error(
                (f"An error has ocurred during scan subcategories"))
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
    def pagination_items(self, driver):
        
        start = time.time()
        end = 0
        items = list()
        while (end - start) < 800:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH, "//div[contains(@class,'selectedFilterItem')]"
                )))
            
            json_items = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                By.XPATH, "//body//div[contains(@class,'items-stretch')]/script[contains(@type,'json')]"
                )))

            content = json_items.get_attribute("innerText")
            content = json.loads(content)
            content = content["itemListElement"]

            _items = [c["item"]  for c in content if not c["item"] in items]

            items.extend(_items)
            
            
            
            # _items = [
            #             {
            #                 "name":c["item"]["name"], 
            #                 "href":c["item"]["@id"],
            #                 "image": c["item"]["image"],
            #                 "sku": c["item"]["sku"]
            #             } 
            #             for c in content 
            #             if not c.get_attribute("href") in items
            #         ]

            
            scroll_position = driver.execute_script("return window.scrollY+document.documentElement.clientHeight;")
            scroll_end = driver.execute_script("return document.body.scrollHeight;")

            if scroll_position != scroll_end:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            load_more = driver.find_elements(By.XPATH, "//div[contains(@class, 'vtex-search-result-3-x-buttonShowMore')]/button")

            if len(load_more):
                driver.execute_script("arguments[0].click();", load_more[0])
                end = 0
            else:
                break

            
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
    def get_products(self, driver: Firefox, items, category=None, subcategory=None, subcategory_2=None, subcategory_3=None):
        for i, item in enumerate(items):
            count_product = f"{int(i+1/len(items))}"
            self.get_product_details(driver, count_product, item, category, subcategory, subcategory_2, subcategory_3)


    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver: Firefox, count_product, item, category, subcategory, subcategory_2, subcategory_3):
        try:
                start = time.time()

                
                
                name = item["name"]
                href = item["@id"]
                image = item["image"]
                sku = item["@id"].replace("https://co.hm.com/", "").replace("/p","")

                duplicate_flag = [True for record in self.records if href == record["url item"]]
                if len(duplicate_flag):
                    return

                driver.get(href)
                
                # time.sleep(1)
                # load_flag = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='size-help']")))
                # if not len(load_flag):
                #     print("Reloading...")
                #     driver.refresh()
                #     time.sleep(5)
                #     load_flag = driver.find_elements(By.XPATH, "//div[@class='size-help']")
                #     if not len(load_flag):
                #         return

                json_categories = WebDriverWait(driver, 10).until(EC.presence_of_element_located((
                    By.XPATH, "//div[contains(@class,'stretchChildrenWidth')]/script[contains(@type,'json')]"
                    )))
                content = json_categories.get_attribute("innerText")
                content = json.loads(content)
                content = content["itemListElement"]

                if len(content) > 2:
                    category, subcategory, subcategory_2 = content[0].get("name"), content[1].get("name"), content[2].get("name")
                elif len(content) > 1:
                    category, subcategory = content[0].get("name"), content[1].get("name")
                else:
                    category = content[0].get("name")

                marca = "H&M"

                patron = r"[^0-9 ]"
                price = driver.find_element(By.XPATH, "//span[contains(@class, 'price_sellingPrice--pricePDP')]")

                price_value = int(re.sub(patron, "", price.get_attribute("innerText") ))
                final_price = price_value

                sale_price = driver.find_elements(By.XPATH, "//span[contains(@class, 'price_listPrice--pricePDP')]")

                if len(sale_price):
                    sale_price_value = price_value
                    price_value = int(re.sub(patron, "", sale_price[0].get_attribute("innerText") ))
                    # final_price = sale_price_value
                    saving = driver.find_elements(By.XPATH, "//p[contains(@class, 'hmchile-catalog-discount')]")
                    if len(saving):
                        saving_value = saving[0].get_attribute("innerText")
                    else:
                        saving_value = f"-{round(100-sale_price*100/price)}%"
                else:
                    sale_price_value, saving_value = None, None
                
                # ------------------------------------- descripción ----------------------------------------------------------- #
                # 
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight*0.4);")

                composition = driver.find_element(
                    By.XPATH, "//div[contains(@class,'hmperu-hmcomponents-0-x-TabMaterials')]//p[contains(@class,'specification-value')]"
                    ).get_attribute("innerText")
                

                component_buttons = driver.find_elements(By.XPATH, "//div[contains(@class,'hmperu-hmcomponents-0-x-collapsiblepdp-container')]//div[contains(@class,'items-center pointer')]")
                [driver.execute_script("arguments[0].click();", component) for component in component_buttons if "Materiales" in component.get_attribute("innerText")]

                materials_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH,"//button[contains(@class, 'hmperu-hmcomponents-0-x-btnStyle')]")))
                driver.execute_script("arguments[0].click();", materials_button)
                

                composition_items = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//div[contains(@class, 'productSpecification items-stretch')]")))

                color = driver.find_elements(By.XPATH, "//span[contains(@data-specification-name, 'Color') and @data-specification-value]")
                
                color = color[0].get_attribute("data-specification-value") if len(color) else None

                materials = ""
                for comp in composition_items:
                    materials += comp.get_attribute("innerText").replace("\n",": ") + ' | '

                made_in = driver.find_elements(
                    By.XPATH,"//p[contains(@class, 'hmperu-hmcomponents-0-x-specification-name') and contains(text(),'Pais')]/following-sibling::p[contains(@class, 'hmperu-hmcomponents-0-x-specification-value')]"
                    )

                made_in = made_in[0].get_attribute("innerText") if len(made_in) else None

                description = item["description"]

                item_characteristics = f"Descripción: {description} || {materials}"
                # item_characteristics = item_characteristics.replace("\n", "").replace("\r", "")

                sizes_stock = driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'hmperu-product-image-modal-0-x-image__list')]//div[@class='absolute absolute--fill']/following-sibling::div[contains(@class, 'skuSelectorItemTextValue')]"
                    )
                sizes_out_stock = driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'hmperu-product-image-modal-0-x-image__list')]//div[contains(@class,'diagonalCross--skuselectorpdp')]/following-sibling::div[contains(@class, 'skuSelectorItemTextValue')]"
                    )

                sizes_stock = [(size.get_attribute("innerText"),"available") for size in sizes_stock]
                sizes_out_stock = [(size.get_attribute("innerText"),"not available") for size in sizes_out_stock]

                # Execute the command for make apear the detail bar
                
                
                for size, stock in sizes_stock + sizes_out_stock:
                    # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                    self.records.append(
                            {
                                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                "canal": "H&M Colombia",
                                "category": category,
                                "subcategory": subcategory,
                                "subcategory_2": subcategory_2,
                                "subcategory_3": subcategory_3,
                                "marca": marca,
                                "modelo": color,
                                "sku": sku,
                                "upc": f"{sku}_{color}_{size}",
                                "item": name,
                                "item_characteristics": item_characteristics,
                                "url sku": HM_URL,
                                "image": image,
                                "price": price_value,
                                "sale_price": sale_price_value,
                                "shipment cost": stock,
                                "sales flag": saving_value,
                                "store id": f"9999_hm_col",
                                "store name": "ONLINE",
                                "store address": "ONLINE",
                                "stock": size,
                                "upc wm": sku,
                                "final_price": final_price,
                                "upc wm2": sku,
                                "comp": None,
                                "composition": composition,
                                "made_in": made_in,
                                "url item": href,
                            }
                        )
                print(f"H&M {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
                time.sleep(0.2)   
        except Exception as e:
            print(e)
            logging.error(f"H&M...Error get product details {category} {subcategory} {subcategory_2}: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
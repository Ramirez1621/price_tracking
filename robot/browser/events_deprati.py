import logging
import datetime as dt
import time
import json
import pandas as pd
import re
# import requests
# import cloudscraper
# import httpx


from os.path import join
from bs4 import BeautifulSoup
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import DEPRATI_URL
from settings import BASE_DIR
from tenacity import retry, wait_random_exponential, stop_after_attempt
# from robot.browser import open_browser
from .web_driver import WebDriver, open_browser

# An list with exclusion subcategories names
EXCLUSION_LIST = ["rebajas", "sostenibilidad", "ver todo", "regalos"]
CATEGORY_IDS = {"ninos":"03", "zapatos":"12" } #"ninos":"03", "zapatos":"12" [{"MUJERES":101}, {"HOMBRES":102}, {"INFANTIL":104}, {"CALZADO":105}] # mujer: 101, hombre: 102, infantil: 103, calzado: 105

class depratiSession():
    def __init__(self):
        self.records = list()
        
    def start_scrapping(self, semaphore):
        with semaphore:
            start = time.time()
            # driver_deprati = open_browser()
            # with WebDriver(driver_deprati) as driver:
            time.sleep(5)
            self.select_categories()
            
            end = time.time()
            logging.info(f"Excution DePrati Time: {end-start} s")

            backup_dataset = join(BASE_DIR,"Backup")
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(join(backup_dataset, f"dataset_DEPRATI.csv"), index=False)

    def open_page(self, driver, page, category_name, category_id):
        try:
            # headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
            url = f"https://www.deprati.com.ec/es/{category_name}/c/{category_id}/results?q=%3AwhatIsNew&page={page}"
            driver.get(url)
            source_code = driver.page_source
            # response = requests.get(url, headers=headers)

            # headers = {
            #             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
            #             'Accept-Language': 'en-US,en;q=0.5',
            #             }
            html_code = BeautifulSoup(source_code, 'html.parser')
            response = html_code.find('pre')
            

            if response is not None:
                data = json.loads(response.text)

                items = data.get('results', [])

                return items
            else:
                return ""
        except Exception as e:
            logging.error(
                (f"DePrati An error has ocurred during report selection: {type(e)}"))
            raise(e)
        
    # def get_colors(self, name, id):
    #     url = f"https://www.etafashion.com/{name}/es_EC/c/{id}"

    #     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'}
    #     response = requests.get(url, headers=headers)

    #     if response.status_code == 200:
    #         html_code = BeautifulSoup(response.text, 'html.parser')
    #         color_list = html_code.find('ul', id='Color')

    #         colors = list()
    #         for color in color_list.find_all('li'):
    #             color_code = color.find('input', type='checkbox')
    #             if color_code is None:
    #                 continue
    #             color_code = color_code.get("data-facet-code")

    #             color_name = color.find('img')
    #             color_name = color_name.get("title")

                
    #             colors.append({"name": color_name, "code": color_code})
    #         return colors
    #     else:
    #         return []
    def retry_exception(self):
        print("retrying...")
        return
    
# ------------------------------------------------------------------------------------------------ #
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def select_categories(self):
        try:
            for name, id in CATEGORY_IDS.items():
                driver_deprati = open_browser()
                with WebDriver(driver_deprati) as driver:
                # colors_code = self.get_colors(name, id)

                # for color in colors_code:
                    page_number = 0
                    while True:
                        # https://www.etafashion.com//es_EC/product-search/101/category?q=%3Amodifiedtime&page=2
                        items = self.open_page(driver = driver, page = page_number, category_id = id, category_name = name)

                        if len(items):
                            self.get_items(items, driver, name)
                            page_number += 1
                            print("-----------------page: " + str(page_number) + "-------------------")
                            time.sleep(40)
                        else:
                            break
            # url_items = list()
            
            # for item in items_data:
            #     url = item.get("url")
            #     url_items.append(url)
        
            
        except Exception as e:
            time.sleep(60)
            logging.error(
                (f"DePrati An error has ocurred during scan categories"))
            logging.error(
                (f"details: {e}"))
            raise(e)

    # async def fetch_data(url):
    #     headers = {
    #         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    #         'Accept-Language': 'en-US,en;q=0.5',
    #     }

    #     async with httpx.AsyncClient() as client:
    #         response = await client.get(url, headers=headers)

    #     return response

# ------------------------------------------------------------------------------------------------ #
    
    
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_items(self, items, driver, category):
        try:
            for i, item in enumerate(items):
                
                url = item["url"]
                complete_url = f"{DEPRATI_URL}{url}"

                duplicate_flag = [True for record in self.records if complete_url == record["url item"]]
                if len(duplicate_flag):
                    continue
                
                # headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
                #             'host': 'www.deprati.com.ec'}
                
                # item_raw = requests.get(complete_url, headers=headers)

                # response = httpx.run(self.fetch_data(complete_url))

                # scraper = cloudscraper.create_scraper()
                # item_raw = scraper.get(complete_url).text

                driver.get(complete_url)
                html_content = driver.page_source

                html_item = BeautifulSoup(html_content, 'html.parser')
                

                if len(html_item):
                    count_product = f"{int(i+1/len(items))}"
                    self.get_product_details(driver, count_product, html_item, category=category)


        except Exception as e:
            time.sleep(60)
            logging.error(
                (f"DePrati An error has ocurred during scan subcategories"))
            logging.error(
                (f"details: {e}"))
            raise(e)
        



# ------------------------------------------------------------------------------------------------ #
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=False, retry_error_callback=retry_exception)
    def get_product_details(self, driver, count_product, html_item, category = None, subcategory = None, subcategory_2 = None, subcategory_3 = None):
        try:    
                # usar beautiful soap para extraer toda la info del producto
                start = time.time()
                time.sleep(0.7)

                hidden_data = html_item.find_all('input', {"name":"producthidden"})

                if len(hidden_data):
                    json_data = json.loads(hidden_data[0]["value"])
                else:
                    return


                # categories_comp = html_item.find('ul', class_="breadcrumb")
                # categories_comp = categories_comp.find_all('li')
                # categories = [ c.text.replace("\n","").strip() for c in categories_comp]
                # categories.pop(0)
                # categories.pop(-1)
                
                raw_categories = json_data.get("sectionCategories")
                raw_categories = [c.get("name").lower() for c in raw_categories]

                subcategory = json_data.get("levelTwoCategory").get("name")

                if "marca" in subcategory.lower():
                    subcategory = json_data.get("mainCategory").get("name")
                    
                else:
                    subcategory = subcategory

                categories = [c for c in raw_categories if  c not in json_data.get("brandCategory").get("name").lower() and c not in subcategory.lower()]
                categories.reverse()
                subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(2)]
                
                
                raw_data = html_item.find('script', type="application/ld+json").text

                sizes = html_item.find_all('option')#, attrs={'disabled': False})
                if len(sizes):
                    sizes.pop(0)
                else:
                    size_html = '<option>S/T</option>'
                    soup = BeautifulSoup(size_html, 'html.parser')
                    sizes = soup.find_all('option')
                    raw_data = raw_data.replace("\n","").replace("\t","")
                    raw_data = re.sub('"size": "sku":', '"size":"", "sku":', raw_data)

                
                data = json.loads(raw_data)

                name = data.get("name")
                
                sku = data.get("sku")

                # color = data.get("color")

                marca = data.get("brand")

                # image = data.get("image")

                made_in = None
                
                # ------------------------------------- descripción ----------------------------------------------------------- #

                # item_characteristics = ""

                item_characteristics = data.get("description")

                item_characteristics = item_characteristics.replace("\n","").replace("<p>","").strip()
                # item_characteristics = re.sub('<[^<]+?>', '|', item_characteristics)
                

                patron = r'\b(?:Elaborad[oa]).*?$'
                # patron_2 = r'(\b\d+% )?(algod[oó]n|elastano|poliéster|cuero)\b'
                # patron_2 = r'\b(?:Pa[ií]s de Origen).*?</li>'

                # materials = [re.findall(patron, comp, re.IGNORECASE) for comp in composition_details]

                materials = re.findall(patron, item_characteristics, re.IGNORECASE)
                materials = ".".join(materials) if len(materials) else None

                # ------------------------------------------------------------------------------------------------ #
                #                                              precio                                              #
                # ------------------------------------------------------------------------------------------------ #
                prices_container = html_item.find('div', class_="price--cont")
                prices = prices_container.find('div', class_="price")

                if prices is not None:

                    sale_price = prices_container.find('div', class_="disccount")
                    sale_price_value = sale_price.text.replace(",", ".").replace("\n", "").strip().strip("$")
                    final_price = sale_price_value

                    price = prices.text
                    price_value = price.replace(",", ".").replace("\n", "").strip().strip("$")
                    saving_value = f"-{round(100-float(sale_price_value)*100/float(price_value))}%"

                else:
                    prices = prices_container.find('div', class_="disccount")
                    price_value = prices.text.replace(",", ".").replace("\n", "").strip().strip("$")
                    final_price = price_value
                    sale_price_value, saving_value = None, None
                
                colors = driver.find_elements(By.XPATH, "//a[@class='swatchVariant' or contains(@class,'selected')]")
                
                for col in colors:
                    driver.execute_script("arguments[0].click()", col)
                    color = col.get_attribute("name")

                    # Refresh de source code to update sizes vaule list
                    html_sizes = driver.page_source
                    html_sizes = BeautifulSoup(html_sizes, 'html.parser')

                    href = driver.current_url
                    image = html_sizes.find('img', class_="zoom")
                    image = image.get('src')

                    sizes = html_sizes.find_all('option')#, attrs={'disabled': False})
                    if len(sizes):
                        sizes.pop(0)
                    else:
                        size_html = '<option>S/T</option>'
                        soup = BeautifulSoup(size_html, 'html.parser')
                        sizes = soup.find_all('option')
                # colors = json_data.get("variantMatrix")
                # for col in colors:
                #     color = col.get('variantValueCategory').get('name')
                #     url = col.get('variantOption').get('url')
                #     href = f"{DEPRATI_URL}{url}"
                #     image = col.get('variantOption').get('variantOptionQualifiers')[0].get('image').get('url')



                    for size in sizes:
                        size_value = size.text.replace("\n","").strip()
                        stock = "not available" if size.get("disabled") else "available"
                        # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                        self.records.append(
                                {
                                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                                    "canal": "De Prati Ecuador",
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
                                    "url sku": DEPRATI_URL,
                                    "image": image,
                                    "price": price_value,
                                    "sale_price": sale_price_value,
                                    "shipment cost": stock,
                                    "sales flag": saving_value,
                                    "store id": f"9999_deprati_ec",
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
                print(f"DePrati {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")

        except Exception as e:
            print(e)
            logging.error(f"DePrati...Error get product details {category} {subcategory} {subcategory_2}: {e}")
            logging.info("Refresh page...")
            # driver.refresh()
            raise(e)
        

        # {"@context": "http://schema.org/","@type": "Product","name": "Billetera H&Co","image":  "https://images.deprati.com.ec/sys-master/images/h0f/h2f/12184377917470/17184639-0_product_300Wx450H","description": "Con la billetera H&Co., puedes llevar tus tarjetas de manera segura y accesible. Sus ranuras están diseñadas para facilitar el acceso a tus tarjetas mientras mantienes todo organizado en un solo lugar.  Detalles:    Billetera H&Co  Diseño combinado  Modelo Flap  Características:     4 ranuras      Medidas: 12 cm alto x 21 cm ancho x 4.3 cm profundidad (medidas aproximadas)  Elaborado en sintético   \xa0  \xa0 ","brand": "H&CO","color":  "NEGRO","size": "sku": "17184639","productID": "659B97857905945002","url": "https://www.deprati.com.ec/-billetera-h-co/p/659B97857905945002","category": "0112-Carteras","pattern": "PN","offers": {"@type": "Offer","priceCurrency": "USD","price": "25.66","availability": "http://schema.org/InStock","itemCondition": "http://schema.org/NewCondition"}}



        # categories_comp = html_item.find('ul', class_="breadcrumb")
                # categories_comp = categories_comp.find_all('li')
                # categories = [ c.text.replace("\n","").strip() for c in categories_comp]
                # categories.pop(0)
                # categories.pop(-1)
                

                # category, subcategory, subcategory_2, subcategory_3 = [categories[i] if i < len(categories) else None for i in range(4)]
                # raw_data = html_item.find('script', type="application/ld+json").text

                # sizes = html_item.find_all('option')#, attrs={'disabled': False})
                # if len(sizes):
                #     sizes.pop(0)
                # else:
                #     sizes = [{'text':'S/T'}]
                #     raw_data = raw_data.replace("\n","").replace("\t","")
                #     raw_data = re.sub('"size": "sku":', '"size":"", "sku":', raw_data)

                
                # data = json.loads(raw_data)

                # name = data.get("name")
                
                # sku = data.get("sku")

                # color = data.get("color")

                # marca = data.get("brand")

                # image = data.get("image")

                # made_in = None
                
                # # ------------------------------------- descripción ----------------------------------------------------------- #

                # # item_characteristics = ""

                # item_characteristics = data.get("description")

                # item_characteristics = item_characteristics.replace("\n","").replace("<p>","").strip()
                # # item_characteristics = re.sub('<[^<]+?>', '|', item_characteristics)
                

                # patron = r'\b(?:Elaborad[oa]).*?$'
                # # patron_2 = r'(\b\d+% )?(algod[oó]n|elastano|poliéster|cuero)\b'
                # # patron_2 = r'\b(?:Pa[ií]s de Origen).*?</li>'

                # # materials = [re.findall(patron, comp, re.IGNORECASE) for comp in composition_details]

                # materials = re.findall(patron, item_characteristics, re.IGNORECASE)
                # materials = ".".join(materials) if len(materials) else None

                # # ------------------------------------------------------------------------------------------------ #
                # #                                              precio                                              #
                # # ------------------------------------------------------------------------------------------------ #
                # prices_container = html_item.find('div', class_="price--cont")
                # prices = prices_container.find('div', class_="price")

                # if prices is not None:

                #     sale_price = prices_container.find('div', class_="disccount")
                #     sale_price_value = sale_price.text.replace(",", ".").replace("\n", "").strip().strip("$")
                #     final_price = sale_price_value

                #     price = prices.text
                #     price_value = price.replace(",", ".").replace("\n", "").strip().strip("$")
                #     saving_value = f"-{round(100-float(sale_price_value)*100/float(price_value))}%"

                # else:
                #     prices = prices_container.find('div', class_="disccount")
                #     price_value = prices.text.replace(",", ".").replace("\n", "").strip().strip("$")
                #     final_price = price_value
                #     sale_price_value, saving_value = None, None
                
                # # sizes_not_stock = html_item.find_all('option', disabled="disabled")
                

                # for size in sizes:
                #     size_value = size.text.replace("\n","").strip()
                #     stock = "not available" if size.get("disabled") else "available"
                #     # date	canal	category	subcategory	subcategory2	subcategory3	marca	modelo	sku	upc	item	item characteristics	url sku	image	price	sale price	shipment cost	sales flag	store id	store name	store address	stock	upc wm	final price	upc wm2	comp	composition
                #     self.records.append(
                #             {
                #                 "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                #                 "canal": "De Prati Ecuador",
                #                 "category": category,
                #                 "subcategory": subcategory,
                #                 "subcategory_2": subcategory_2,
                #                 "subcategory_3": subcategory_3,
                #                 "marca": marca,
                #                 "modelo": color,
                #                 "sku": sku,
                #                 "upc": f"{sku}_{color}_{size_value}",
                #                 "item": name,
                #                 "item_characteristics": item_characteristics,
                #                 "url sku": DEPRATI_URL,
                #                 "image": image,
                #                 "price": price_value,
                #                 "sale_price": sale_price_value,
                #                 "shipment cost": stock,
                #                 "sales flag": saving_value,
                #                 "store id": f"9999_deprati_ec",
                #                 "store name": "ONLINE",
                #                 "store address": "ONLINE",
                #                 "stock": size_value,
                #                 "upc wm": sku,
                #                 "final_price": final_price,
                #                 "upc wm2": sku,
                #                 "comp": None,
                #                 "composition": materials,
                #                 "made_in": made_in,
                #                 "url item": href,
                #             }
                #         )
                # print(f"DePrati {category} {subcategory} {subcategory_2}  {subcategory_3} item {count_product}\t{round(time.time()-start, 3)} s")
            
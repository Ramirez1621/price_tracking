import logging
import datetime as dt
import time
import json
import pandas as pd
import re
import requests
import threading
import os

# Si deseas usar Firefox vía Selenium, podrías descomentar e implementar
# from selenium.webdriver import Firefox
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait, Select
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException

from tenacity import retry, wait_random_exponential, stop_after_attempt

# En lugar de settings.py, definimos aquí la URL y la ruta donde guardaremos el CSV.
ZARA_URL = "https://www.zara.com/ec/"  
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DATASET = os.path.join(BASE_DIR, "Backup")  # Carpeta local "Backup"

# Listas de exclusión e inclusión
EXCLUSION_LIST = [
    "party", "new", "colaboraciones®", "special prices", "gift ideas",
    "lo más vendido", "nuevo esta semana", "ver todo", "total look"
]
INCLUSION_LIST = ["ropa", "zapatos", "accesorios"]

class zaraSession:
    def __init__(self):
        # Donde guardamos todos los registros de productos
        self.records = []
        # Semáforo para controlar hilos simultáneos (máximo 20 en este ejemplo)
        self.semaphore = threading.Semaphore(20)
        
    def start_scrapping(self, semaphore):
        """Método principal para iniciar el scraping."""
        with semaphore:
            start = time.time()

            # (Si usaras Selenium, podrías abrir tu navegador aquí)
            # driver = tu_open_browser()

            # Damos un tiempo de espera inicial (por si necesitas que algo cargue)
            time.sleep(5)

            # Llamamos al método que obtiene categorías (mediante requests)
            self.select_categories()

            # (Si usaras Selenium)
            # driver.quit()

            end = time.time()
            logging.info(f"Execution Zara Time: {end - start} s")

            # Crea la carpeta Backup si no existe
            os.makedirs(BACKUP_DATASET, exist_ok=True)

            # Pasa los registros a DataFrame y los guarda en CSV
            df = pd.DataFrame.from_records(self.records)
            df.to_csv(os.path.join(BACKUP_DATASET, "dataset_ZARA.csv"), index=False)

    def select_categories(self):
        """
        Llama al endpoint de Zara para obtener las categorías,
        filtra subcategorías y llama a `scan_items` para cada una.
        """
        try:
            # Endpoint para obtener categorías en JSON
            url_category = "https://www.zara.com/ec/es/categories?ajax=true"
            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
            
            response = requests.get(url_category, headers=headers)
            if response.status_code == 200:
                data = json.loads(response.content)
                category_ids = []

                for category_data in data["categories"]:
                    # 'subcategories' típicamente es una lista
                    subcats = category_data.get("subcategories", [])
                    # Filtramos solo donde "grid" aparezca en "contentType" y el "name" no sea "NEW"
                    valid_subcats = [
                        {"id": sub["id"], "subcategory": sub["name"]}
                        for sub in subcats
                        if ("grid" in sub.get("contentType", "")) and ("NEW" not in sub["name"])
                    ]
                    category_ids.extend(valid_subcats)
                
                # Llamamos a `scan_items` para cada subcategoría válida
                self.scan_items(category_ids)
                    
        except Exception as e:
            logging.error("An error has occurred during scan category")
            logging.error(f"details: {e}")

    def scan_items(self, category_ids):
        """
        Para cada subcategoría, obtiene los productos
        y lanza hilos para procesarlos en `get_products`.
        """
        for subcat in category_ids:
            try:
                url_category = f"https://www.zara.com/ec/es/category/{subcat['id']}/products?ajax=true"
                headers = {'User-Agent': 'PostmanRuntime/7.32.1'}

                response = requests.get(url_category, headers=headers)
                if response.status_code == 200:
                    data = json.loads(response.content)
                    product_groups = data.get("productGroups", [])

                    if not product_groups:
                        continue

                    # Normalmente productGroups[0] contiene 'elements'
                    product_list = product_groups[0].get("elements", [])
                    threads = []

                    for product in product_list:
                        cc = product.get("commercialComponents")
                        if cc is None:
                            continue
                        # Extrae la info SEO
                        data_product = [
                            i["seo"] for i in cc if "Product" in i.get("type", "")
                        ]

                        # Crea un hilo para procesar esos productos
                        t = threading.Thread(
                            target=self.get_products,
                            args=(data_product, subcat["subcategory"])
                        )
                        threads.append(t)
                        t.start()
                        time.sleep(0.3)

                        # Juntamos los hilos para que esperen su ejecución
                        for t in threads:
                            t.join()

                time.sleep(2)

            except Exception as e:
                logging.error("An error has occurred during scan subcategory")
                logging.error(f"details: {e}")

    def get_extra_details(self, url):
        """
        Llama a un endpoint que da detalles extra (materiales, cuidados, etc.)
        y retorna un diccionario con esa info.
        """
        headers = {'User-Agent': 'PostmanRuntime/7.32.1'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data_details = json.loads(response.content)

            item_details = {}
            materials = ""
            recycled_materials = ""
            certified_materials = ""
            cares = ""
            made_in = ""

            for part in data_details:
                section = part.get("sectionType", "")

                # Sección de materiales
                if "materials" in section:
                    # A veces ignora los primeros 4 'components'
                    part["components"] = part["components"][4:]
                    for comp in part["components"]:
                        d_type = comp.get("datatype", "")
                        val = comp.get("text", {}).get("value", "")
                        if "subtitle" in d_type:
                            materials += f"{val}: "
                        elif "paragraph" in d_type:
                            materials += f"{val}. "

                # Sección de materiales reciclados
                elif "recycledMaterials" in section:
                    for comp in part["components"]:
                        d_type = comp.get("datatype", "")
                        val = comp.get("text", {}).get("value", "")
                        if "subtitle" in d_type:
                            recycled_materials += f"{val}: "
                        elif "paragraph" in d_type:
                            recycled_materials += f"{val}. "

                # Sección de materiales certificados
                elif "certifiedMaterials" in section:
                    for comp in part["components"]:
                        d_type = comp.get("datatype", "")
                        val = comp.get("text", {}).get("value", "")
                        if "subtitle" in d_type:
                            certified_materials += f"{val}: "
                        elif "paragraph" in d_type:
                            certified_materials += f"{val}. "

                # Sección de cuidados
                elif "care" in section:
                    for comp in part["components"]:
                        d_type = comp.get("datatype", "")
                        val = comp.get("text", {}).get("value", "")
                        if "subtitle" in d_type:
                            cares += f"{val}: "
                        elif "paragraph" in d_type:
                            # A veces hay "<br>" que queremos eliminar
                            cares += f"{val}. ".split("<br>")[0]

                # Sección de origen
                elif "origin" in section:
                    for comp in part["components"]:
                        d_type = comp.get("datatype", "")
                        val = comp.get("text", {}).get("value", "")
                        if "paragraph" in d_type and "Hecho en" in val:
                            made_in = val.replace("Hecho en ", "")

            materials = materials.replace("<br>", " ")
            item_details = {
                "materials": materials + recycled_materials + certified_materials,
                "cares": cares,
                "made_in": made_in
            }
            return item_details

        return {}

    def retry_exception(self):
        """Callback para tenacity en caso de fallos."""
        print("retrying...")
        return

    def get_products(self, items, subcategory):
        """
        Procesa la lista de productos (items) y llama a get_product_details
        para obtener la información de cada uno.
        """
        with self.semaphore:
            for i, item in enumerate(items):
                count_product = f"{int(i+1 / len(items))}"
                self.get_product_details(count_product, item, subcategory)

    @retry(wait=wait_random_exponential(min=2, max=6),
           stop=stop_after_attempt(3),
           reraise=False,
           retry_error_callback=retry_exception)
    def get_product_details(self, count_product, item, subcategory):
        """
        Llama a la URL específica de un producto y guarda sus detalles en self.records.
        """
        try:
            start = time.time()
            category_dict = {"WOMAN": "Mujer", "MAN": "Hombre", "KID": "Niños"}

            # Ejemplo de URL de producto con "keyword" y "seoProductId"
            url_item = f"https://www.zara.com/ec/es/{item['keyword']}-p{item['seoProductId']}.html?ajax=true"
            headers = {'User-Agent': 'PostmanRuntime/7.32.1'}

            response = requests.get(url_item, headers=headers)
            if response.status_code == 200:
                data = json.loads(response.content)
                data_product = data.get("product", {})

                name = data_product.get("name", "")
                # Construimos la url final del producto (no JSON)
                href = f"https://www.zara.com/ec/es/{item['keyword']}-p{item['seoProductId']}.html"

                # Evita duplicar registros si la url ya existe
                if any(r["url item"] == href for r in self.records):
                    return

                # Mapea la categoría de inglés a español
                raw_cat = data_product.get("sectionName", "")
                category = category_dict.get(raw_cat, raw_cat)

                subcategory_2 = data_product.get("familyName", "")
                subcategory_3 = data_product.get("subfamilyName", "")

                # Llama a get_extra_details
                url_details = f"https://www.zara.com/ec/es/product/{data_product['id']}/extra-detail?ajax=true"
                item_details = self.get_extra_details(url_details)

                marca = "Zara"
                sku = data_product.get("detail", {}).get("reference", "")
                
                # Descripción
                raw_colors = data_product.get("detail", {}).get("colors", [])
                if raw_colors:
                    description = raw_colors[0].get("rawDescription", "")
                else:
                    description = ""

                materials = item_details.get("materials", "")
                cares = item_details.get("cares", "")
                made_in = item_details.get("made_in", "")

                item_characteristics = f"Descripción: {description} || Composición: {materials} || Cuidados: {cares}"

                # Itera sobre cada color disponible
                for detail in raw_colors:
                    image_list = detail.get("mainImgs", [])
                    if image_list:
                        image_url = image_list[0].get("url", "")
                    else:
                        image_url = ""

                    color = detail.get("name", "")
                    sizes = detail.get("sizes", [])

                    for size in sizes:
                        price = size.get("price", 0)
                        price_value = price / 100
                        final_price = price_value

                        sale_price = size.get("oldPrice")
                        if sale_price is not None:
                            sale_price_value = price_value
                            final_price = price_value
                            price_value = sale_price / 100
                            saving_value = f"-{round(100 - sale_price_value * 100 / price_value)}%"
                        else:
                            sale_price_value = None
                            saving_value = None

                        size_value = size.get("name", "")
                        availability = size.get("availability", "")
                        stock_str = "available" if availability == "in_stock" else "not available"

                        # Guarda el registro
                        self.records.append({
                            "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                            "canal": "Zara Ecuador",
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
                            "url sku": ZARA_URL,
                            "image": image_url,
                            "price": price_value,
                            "sale_price": sale_price_value,
                            "shipment cost": stock_str,
                            "sales flag": saving_value,
                            "store id": "9999_zara_ec",
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
                        })
                
                print(f"Zara {category} {subcategory} {subcategory_2} {subcategory_3} item {count_product}\t"
                      f"{round(time.time() - start, 3)} s")

            time.sleep(0.2)
        except Exception as e:
            print(e)
            logging.error(f"Zara...Error get product details {subcategory_2} => {type(e)} Message: {e}")
            logging.info("Refresh page...")
            raise e


if __name__ == "__main__":
    # Aquí instancias la clase y la llamas manualmente:
    logging.basicConfig(level=logging.INFO)
    # Creamos un semáforo global
    global_semaphore = threading.Semaphore(1)

    # Instanciamos la sesión de Zara
    zara_bot = zaraSession()
    # Iniciamos el scraping
    zara_bot.start_scrapping(global_semaphore)

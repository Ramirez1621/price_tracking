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
from selenium.common.exceptions import TimeoutException

from tenacity import retry, wait_random_exponential, stop_after_attempt

# Aquí debes importar o definir tu método para abrir el navegador
# from .web_driver import WebDriver, open_browser

# Constante con la URL
SEKONO_URL = "https://www.tiendasekono.com/"

# Ajusta según tus necesidades
BASE_DIR = "./"
EXCLUSION_LIST = ["Promociones", "Sale", "Ofertas", "Rebajas"]  # Ejemplo
INCLUSION_LIST = ["Ropa", "Zapatos", "Accesorios"]             # Ejemplo

class SekonoSession():
    def __init__(self):
        self.records = []

    def start_scrapping(self, semaphore):
        """
        Método principal para lanzar todo el proceso de scraping.
        """
        with semaphore:
            start = time.time()
            driver = self.open_browser()  # Ajusta a tu método real de abrir browser
            self.open_page(driver)

            # Espera opcional por si carga un pop-up o splash inicial
            time.sleep(5)

            # Seleccionar categorías principales
            self.select_categories(driver)

            driver.quit()
            end = time.time()
            logging.info(f"Ejecución Sekono: {end - start} s")

            backup_dataset = join(BASE_DIR, "Backup")
            df = pd.DataFrame.from_records(self.records)
            print("Voy a guardar el CSV en:", join(backup_dataset, "dataset_HM.csv"))
            print("Número de registros en self.records:", len(self.records))
            df.to_csv(join(backup_dataset, f"dataset_SEKONO.csv"), index=False)

    def open_browser(self):
        """
        Retorna la instancia del navegador con las configuraciones que requieras.
        Por ejemplo, usando Firefox:
        """
        from selenium.webdriver import Firefox
        from selenium.webdriver.firefox.options import Options

        options = Options()
        # options.add_argument("--headless") # Quita el comentario si deseas sin interfaz
        driver = Firefox(options=options)
        driver.maximize_window()
        return driver

    def open_page(self, driver):
        try:
            driver.get(SEKONO_URL)
        except Exception as e:
            logging.error(f"Error al abrir {SEKONO_URL}: {type(e)} - {e}")
            raise e

    # ----------------------------------------------------------------------------------------
    def select_categories(self, driver):
        """
        Método para capturar las categorías principales y navegar sus subcategorías.
        Ajusta los XPATH / selectores para que encajen con la estructura de tiendasekono.com.
        """
        try:
            # Ejemplo: localizador para el menú principal
            categories = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    "//nav[contains(@class, 'navigation')]//ul[@class='menu']//li/a"
                ))
            )

            subcategories_links = []
            for cat in categories:
                cat_name = cat.get_attribute("innerText").strip()
                
                # Filtramos categorías que NO queremos (EXCLUSION_LIST), 
                # o que sí queremos (INCLUSION_LIST) según tu propia lógica.
                # if cat_name in EXCLUSION_LIST:
                #     continue
                # if cat_name not in INCLUSION_LIST:
                #     continue

                # Guardamos el href y nombre
                href = cat.get_attribute("href")
                subcategories_links.append((cat_name, href))

            # Recorre cada categoría principal
            for cat_name, cat_href in subcategories_links:
                logging.info(f"Abriendo categoría principal: {cat_name} => {cat_href}")
                self.select_subcategory(driver, cat_name, cat_href)

        except Exception as e:
            logging.error("Error al obtener categorías principales")
            logging.error(f"Detalles: {e}")

    # ----------------------------------------------------------------------------------------
    def select_subcategory(self, driver, category_name, category_href):
        """
        Visita la URL de una categoría y busca posibles subcategorías o directamente 
        la paginación de productos. Ajusta según la estructura de tiendasekono.com
        """
        try:
            driver.get(category_href)
            time.sleep(3)

            # Si hay subcategorías, puedes capturarlas de forma similar:
            # sub_cats = driver.find_elements(
            #     By.XPATH, 
            #     "//div[@class='some-subcat-block']//a"
            # )
            # if sub_cats:
            #     for sc in sub_cats:
            #         sc_name = sc.text.strip()
            #         sc_href = sc.get_attribute("href")
            #         self.select_subcategory_2(driver, category_name, sc_name, sc_href)
            # else:
            #     # Si no hay subcategorías, extraemos productos directamente
            #     self.extract_products_from_listing(driver, category_name, None, None)

            # Para simplificar este ejemplo, asumo que ya estamos en la vista de productos
            self.extract_products_from_listing(driver, category_name, None, None)

        except Exception as e:
            logging.error(f"Error al navegar subcategoría de {category_name}")
            logging.error(f"Detalles: {e}")

    # ----------------------------------------------------------------------------------------
    def extract_products_from_listing(self, driver, category, subcategory, subcategory_2):
        """
        Desde la página de listado de productos, hace scrolling/paginación y
        obtiene el link de cada producto.
        """
        try:
            items = []
            # Ejemplo: repetimos scroll/paginación hasta que no haya más productos
            while True:
                # Hacemos scroll hasta el final
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

                # Capturamos productos en la grilla (ajusta XPATH)
                product_cards = driver.find_elements(
                    By.XPATH, "//div[contains(@class,'product-item')]//a[contains(@class,'product-item-link')]"
                )
                # Se guardan href de cada producto
                for card in product_cards:
                    href = card.get_attribute("href")
                    if href not in items:
                        items.append(href)

                # Verificamos si hay un botón "Ver más" o "Cargar más"
                load_more = driver.find_elements(
                    By.XPATH, 
                    "//button[contains(text(), 'Ver más') or contains(text(), 'Cargar más')]"
                )
                if load_more:
                    try:
                        driver.execute_script("arguments[0].click();", load_more[0])
                        time.sleep(2)
                    except:
                        break
                else:
                    break

            logging.info(f"Se encontraron {len(items)} productos en la categoría {category}")

            # Ahora recorremos cada link de producto y extraemos su detalle
            for i, prod_href in enumerate(items):
                self.get_product_details(
                    driver, i, prod_href,
                    category, subcategory, subcategory_2
                )

        except Exception as e:
            logging.error(f"Error en la extracción de productos para {category}: {e}")

    # ----------------------------------------------------------------------------------------
    @retry(wait=wait_random_exponential(min=2, max=6), stop=stop_after_attempt(3), reraise=True)
    def get_product_details(self, driver, i, prod_href, category, subcategory, subcategory_2):
        """
        Accede a la página de detalle de un producto y extrae la información requerida.
        """
        start = time.time()
        subcategory_3 = None  # Por si llegases a manejar más niveles

        try:
            driver.get(prod_href)
            time.sleep(2)

            # -------------
            # 1. Nombre del producto
            # -------------
            product_name_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//h1[contains(@class,'page-title')]"
                ))
            )
            product_name = product_name_elem.text.strip()

            # -------------
            # 2. Marca (puede que en Sekono no haya marca específica, podrías usar 'Sekono')
            # -------------
            marca = "Sekono"  # Ajusta según el sitio si es que aparece la marca.

            # -------------
            # 3. Precio y/o precio descuento
            # -------------
            # Ajusta XPATH según la estructura real
            try:
                price_elem = driver.find_element(
                    By.XPATH,
                    "//span[contains(@id,'product-price')]"
                )
                raw_price = price_elem.text.strip()  # Ej: "₡6,500"
                patron = r"[^0-9]"
                price_value = int(re.sub(patron, "", raw_price)) if raw_price else None
            except:
                price_value = None

            # Precio original (si hay descuento)
            try:
                sale_price_elem = driver.find_element(
                    By.XPATH,
                    "//span[contains(@class,'old-price')]"
                )
                raw_sale_price = sale_price_elem.text.strip()  # Ej: "₡8,000"
                sale_price_value = int(re.sub(r"[^0-9]", "", raw_sale_price))
                # Si existe sale_price, assumimos price_value es el precio final con descuento
                final_price = price_value
                price_value = sale_price_value
                # Calcula porcentaje de ahorro
                saving_value = f"-{round(100 - (final_price * 100 / price_value))}%"
            except:
                sale_price_value = None
                final_price = price_value
                saving_value = None

            # -------------
            # 4. SKU / Modelo (Depende de si lo publica la página)
            # -------------
            try:
                sku_elem = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'sku-wrapper')]"
                )
                sku = sku_elem.text.strip()  # Ej: "SKU: 12345"
                sku = sku.replace("SKU:", "").strip()
            except:
                sku = None

            # Modelo podría ser, por ejemplo, un color o referencia. Ajusta según sea tu caso:
            modelo = None

            # -------------
            # 5. Descripción / Características
            # -------------
            try:
                desc_elem = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'product attribute description')]"
                )
                description = desc_elem.text.strip()
            except:
                description = ""

            # Aquí podrías buscar composición, país de fabricación y demás, 
            # pero en muchos e-commerce estos datos no están tan detallados como en H&M.
            composition = ""
            made_in = ""

            # -------------
            # 6. Stock / Tallas disponibles
            # -------------
            # Para Sekono, si es que manejan tallas y stock, habrá que ver su estructura en la página:
            sizes_stock = []
            sizes_out_stock = []

            # Ejemplo si hay un selector de tallas:
            # tallas = driver.find_elements(By.XPATH, "//div[@class='swatch-attribute-options']//div[contains(@class,'swatch-option text')]")
            # for t in tallas:
            #     talla = t.get_attribute("aria-label")  # O lo que corresponda
            #     # Chequear si está "disabled" para saber si no hay stock
            #     if "disabled" in t.get_attribute("class"):
            #         sizes_out_stock.append((talla, "not available"))
            #     else:
            #         sizes_stock.append((talla, "available"))

            # Si no hay tallas, puedes asumir un stock "available" genérico
            if not sizes_stock and not sizes_out_stock:
                sizes_stock = [("Única", "available")]

            # -------------
            # 7. Armar registros en self.records
            # -------------
            for size, stock_status in (sizes_stock + sizes_out_stock):
                # upc => Concatena lo que necesites. Ej: "{sku}_{color}_{size}"
                upc = f"{sku}_{size}" if sku else None

                record = {
                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                    "canal": "Sekono",
                    "category": category,
                    "subcategory": subcategory,
                    "subcategory_2": subcategory_2,
                    "subcategory_3": subcategory_3,
                    "marca": marca,
                    "modelo": modelo,
                    "sku": sku,
                    "upc": upc,
                    "item": product_name,
                    "item_characteristics": description,   # o "Descripción: {} || {}".format(...)
                    "url sku": SEKONO_URL,                 # o la home, si quieres
                    "image": None,                         # Ajusta para capturar la URL de la imagen principal
                    "price": price_value,
                    "sale_price": sale_price_value,
                    "shipment cost": stock_status,         # A veces lo usamos para 'available' o 'not available'
                    "sales flag": saving_value,
                    "store id": "9999_sekono",
                    "store name": "ONLINE",
                    "store address": "ONLINE",
                    "stock": size,                         # Talla o "no aplica"
                    "upc wm": sku,
                    "final_price": final_price,
                    "upc wm2": sku,
                    "comp": None,
                    "composition": composition,
                    "made_in": made_in,
                    "url item": prod_href
                }
                self.records.append(record)

            print(f"SEKONO {category} {subcategory} {subcategory_2} item {i+1}\t"
                  f"{round(time.time() - start, 3)} s")

        except Exception as e:
            logging.error(f"Error al extraer detalles de producto en Sekono: {e}")
            raise e

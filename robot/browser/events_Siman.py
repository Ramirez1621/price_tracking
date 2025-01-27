import logging
import datetime as dt
import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = "https://cr.siman.com"
OUTPUT_DIR = "Backup"
CSV_FILENAME = "siman_data.csv"

# URL de la categoría
TARGET_URL = "https://cr.siman.com/moda/ropa-de-hombre"

class SimanScraper:
    def __init__(self):
        self.records = []
        self.all_product_urls = set()
        self.browser = None

    def scrape(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            self.browser = browser
            page = browser.new_page()

            page.goto(TARGET_URL, timeout=60000)
            logging.info(f"Navegando a la categoría: {TARGET_URL}")

            page.wait_for_load_state("networkidle", timeout=60000)

            # LÓGICA: BOTÓN "Mostrar más" (puedes cambiar a scroll_infinite_logic)
            self.process_products_show_more(page)

            self.save_to_csv()
            browser.close()

    def process_products_show_more(self, page):
        """
        Realiza la paginación usando el botón "Mostrar más".
        Verifica que haya productos nuevos antes de continuar.
        """
        max_clicks = 20
        num_clicks = 0

        while True:
            page.wait_for_load_state("networkidle", timeout=60000)
            soup = BeautifulSoup(page.content(), "html.parser")
            products = soup.select("section.vtex-product-summary-2-x-container")

            logging.info(f"Se encontraron {len(products)} productos en el DOM actual.")
            new_products_count = 0

            for prod in products:
                link_tag = prod.find("a", href=True)
                if not link_tag:
                    continue
                product_url = urljoin(BASE_URL, link_tag["href"])
                if product_url not in self.all_product_urls:
                    self.all_product_urls.add(product_url)
                    new_products_count += 1
                    self.process_product_detail_in_new_page(
                        product_url,
                        canal_category="Siman (CR)",
                        category="Ropa de mujer",
                        subcategory="",
                        subcategory_2=""
                    )

            logging.info(f"Nuevos productos encontrados en esta iteración: {new_products_count}")

            if new_products_count == 0:
                logging.info("No se encontraron nuevos productos. Se asume fin de paginación.")
                break

            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

                next_button = page.query_selector('button:has-text("Mostrar más")')
                if next_button and next_button.is_visible():
                    logging.info("Clic en 'Mostrar más' para cargar más productos.")
                    next_button.click(force=True)
                    page.wait_for_timeout(3000)
                    num_clicks += 1
                    if num_clicks >= max_clicks:
                        logging.info(f"Se alcanzó la cantidad máxima de {max_clicks} clics.")
                        break
                else:
                    logging.info("No se encontró o ya no aparece 'Mostrar más'. Fin de paginación.")
                    break
            except Exception as e:
                logging.info("No se pudo hacer clic en 'Mostrar más'. Fin de paginación.")
                break

    def process_product_detail_in_new_page(self, product_url, canal_category, category, subcategory, subcategory_2):
        try:
            new_context = self.browser.new_context()
            detail_page = new_context.new_page()

            detail_page.goto(product_url, timeout=120000, wait_until="domcontentloaded")
            detail_page.wait_for_load_state("domcontentloaded", timeout=120000)
            self.extract_product_details(detail_page, product_url,
                                         canal_category, category,
                                         subcategory, subcategory_2)

            detail_page.close()
            new_context.close()
        except Exception as e:
            logging.error(f"Error al procesar la página de detalle {product_url}: {e}")

    def extract_product_details(self, page, product_url,
                                canal_category, category,
                                subcategory, subcategory_2):
        """
        Extrae datos del producto:
          - Actualiza categorías usando el breadcrumb.
          - Extrae marca, nombre, SKU, precio, imagen, descripción, especificaciones, color.
          - Extrae tallas disponibles (si no se encuentran, usa "default").
          - Asigna descuento en "sales flag" con el porcentaje real (y vacío si no hay descuento).
          - Limpia la composición removiendo ":: ".
        """
        try:
            soup = BeautifulSoup(page.content(), "html.parser")

            # BREADCRUMB
            breadcrumb_div = soup.find("div", {"data-testid": "breadcrumb"})
            if breadcrumb_div:
                links = breadcrumb_div.find_all("a")
                if len(links) >= 2:
                    category = links[1].get_text(strip=True)
                if len(links) >= 3:
                    subcategory = links[2].get_text(strip=True)
                if len(links) >= 4:
                    subcategory_2 = links[3].get_text(strip=True)

            # MARCA
            brand_tag = soup.find("span", class_="vtex-store-components-3-x-productBrandName")
            marca = brand_tag.get_text(strip=True) if brand_tag else "Sin Marca"

            # NOMBRE
            name_tag = soup.find("p", class_="nombreProducto")
            nombre_producto = name_tag.get_text(strip=True) if name_tag else "Sin Nombre"

            # SKU
            sku_tag = soup.find("span", class_="vtex-product-identifier-0-x-product-identifier__value")
            sku = sku_tag.get_text(strip=True) if sku_tag else "SinSKU"

            # PRECIO ACTUAL
            price_val = 0.0
            price_tag = soup.select_one("span.vtex-product-price-1-x-sellingPriceValue")
            if price_tag:
                price_str = re.sub(r"[^\d,\.]", "", price_tag.get_text().strip()).replace(",", ".")
                price_val = float(price_str) if price_str else 0.0

            # PRECIO ANTERIOR
            list_price_val = None
            list_price_tag = soup.select_one("span.vtex-product-price-1-x-listPriceValue")
            if list_price_tag:
                list_price_str = re.sub(r"[^\d,\.]", "", list_price_tag.get_text().strip()).replace(",", ".")
                list_price_val = float(list_price_str) if list_price_str else None

            # OBTENER PORCENTAJE DE DESCUENTO (SI APLICA)
            discount = ""
            if list_price_val and list_price_val > price_val:
                discount_tag = soup.find("span", class_="siman-m3-custom-1-x-tag-preview__credisiman-porcentage")
                # Si existe discount_tag, extraemos su texto (ej. "-50%"); de lo contrario, dejamos discount vacío
                discount = discount_tag.get_text(strip=True) if discount_tag else ""

            # IMAGEN
            img_tag = soup.find("img", class_=re.compile("vtex-store-components-3-x-productImageTag--main"))
            image_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else "Sin imagen"

            # DESCRIPCIÓN
            desc_tag = (soup.select_one("div.siman-m3-custom-1-x-containerDescription")
                        or soup.select_one("span.siman-m3-custom-1-x-description"))
            descripcion = desc_tag.get_text(separator=" | ", strip=True) if desc_tag else "Sin descripción"

            # ESPECIFICACIONES / COMPOSICIÓN
            spec_list = soup.select("ul.siman-m3-custom-1-x-specificationList li")
            specifications = ""
            composition = ""
            if spec_list:
                specs = []
                for li in spec_list:
                    text = li.get_text(separator=": ", strip=True)
                    specs.append(text)
                    if text.lower().startswith("materiales"):
                        composition = text.split(":", 1)[-1].strip()
                specifications = " | ".join(specs)

            # LIMPIAR ":: " EN COMPOSICIÓN
            if composition.startswith("::"):
                composition = composition[2:].strip()

            # COLOR
            color = "No especificado"
            if spec_list:
                for li in spec_list:
                    text = li.get_text(separator=" ", strip=True).lower()
                    if text.startswith("color"):
                        parts = re.split(r":\s*", li.get_text(separator=" ", strip=True), maxsplit=1)
                        if len(parts) == 2:
                            color = parts[1]
                        break

            # TALLAS
            tamanos = []
            talla_container = soup.find(
                lambda tag: tag.name == "div" and tag.get("class")
                and any("skuSelectorOptionsList" in cl for cl in tag.get("class"))
            )
            if talla_container:
                for opt in talla_container.find_all("div", recursive=True):
                    text = opt.get_text().strip()
                    if text and re.match(r"^[\w\.\-]+$", text):
                        tamanos.append(text)
            if not tamanos:
                tamanos = ["default"]

            # CREAR REGISTROS POR TALLA
            for talla in tamanos:
                record = {
                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                    "canal": canal_category,
                    "category": category,
                    "subcategory": subcategory.upper(),
                    "subcategory_2": subcategory_2,
                    "subcategory_3": None,
                    "marca": marca,
                    "modelo": color,
                    "sku": sku,
                    "upc": f"{sku}_{color}_{talla}",
                    "item": nombre_producto,
                    "item_characteristics": f"{descripcion} | {specifications}",
                    "url sku": product_url,
                    "image": image_url,
                    "price": price_val,
                    "sale_price": list_price_val,
                    "shipment cost": "available" if price_val > 0 else "not available",
                    "sales flag": discount,  # Aquí guardamos el porcentaje real (ej. "-50%")
                    "store id": "9999_siman_cr",
                    "store name": "ONLINE",
                    "store address": "ONLINE",
                    "stock": talla,
                    "upc wm": sku,
                    "final_price": price_val,
                    "upc wm2": sku,
                    "comp": None,
                    "composition": composition,
                    "made_in": None,
                    "url item": product_url
                }
                self.records.append(record)
                logging.info(f"Producto extraído: {record}")

        except Exception as e:
            logging.error(f"Error al extraer detalles del producto {product_url}: {e}")

    def save_to_csv(self):
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        df = pd.DataFrame(self.records)
        df.to_csv(file_path, index=False, encoding="utf-8-sig", float_format="%.2f")
        logging.info(f"Datos guardados exitosamente en {file_path}")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    scraper = SimanScraper()
    scraper.scrape()

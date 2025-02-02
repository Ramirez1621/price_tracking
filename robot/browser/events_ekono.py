import logging
import datetime as dt
import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = "https://www.tiendasekono.com"

# 4 URLs: 2 hombre, 2 mujer
ALL_URLS = [
    "https://www.tiendasekono.com/hombre.html?cat=1177",
    "https://www.tiendasekono.com/hombre.html?cat=1210",
    "https://www.tiendasekono.com/mujer.html?cat=1042",
    "https://www.tiendasekono.com/mujer.html?cat=976",
]

OUTPUT_DIR = "output_ekono"
CSV_FILENAME = "ekono_data.csv"

class EkonoScraper:
    def __init__(self):
        self.records = []
        self.all_product_urls = set()

    def scrape(self):
        """
        Método principal: recorre las URLs en ALL_URLS, 
        extrae productos con paginación en cada una.
        """
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()

            for url in ALL_URLS:
                # Determinar "Hombre" o "Mujer" según la URL (si deseas).
                # O puedes forzar "Hombre" para las 2 primeras y "Mujer" para las 2 últimas.
                category = "Hombre" if "hombre" in url.lower() else "Mujer"

                logging.info(f"Scrapeando URL: {url} (Categoría={category})")
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)
                except Exception as e:
                    logging.error(f"Error al navegar a la URL {url}: {e}")
                    continue

                # Extraer productos con paginación para esta URL
                self.process_products_in_page(page, category)

            self.save_to_csv()
            browser.close()

    def process_products_in_page(self, page, category):
        """
        Extrae productos de la página actual y avanza a la siguiente con "Siguiente",
        hasta agotar páginas.
        """
        while True:
            soup = BeautifulSoup(page.content(), "html.parser")

            # 1) Lista de productos en la página actual
            product_ol = soup.find("ol", class_="products list items product-items")
            if not product_ol:
                logging.info("No se encontró la lista de productos. Terminando esta URL.")
                break

            product_lis = product_ol.find_all("li", class_="item product product-item")
            logging.info(f"Se encontraron {len(product_lis)} productos en la página actual.")

            new_count = 0
            for li in product_lis:
                link_tag = li.find("a", class_="product-item-link", href=True)
                if not link_tag:
                    link_tag = li.find("a", class_="product photo product-item-photo", href=True)
                if not link_tag:
                    continue

                product_url = urljoin(BASE_URL, link_tag["href"])
                # Evitar duplicados
                if product_url not in self.all_product_urls:
                    self.all_product_urls.add(product_url)
                    new_count += 1

                    try:
                        page.goto(product_url, timeout=60000)
                        page.wait_for_load_state("networkidle", timeout=60000)
                        self.extract_product_details(page, product_url, category)
                    except Exception as e:
                        logging.error(f"Error al procesar el producto {product_url}: {e}")
                        continue

            if new_count == 0:
                logging.info("No se encontraron productos nuevos en esta página. Se asume fin de paginación.")
                break

            # 2) Botón "Siguiente" => <ul class="pages-items"><li class="item pages-item-next">...
            next_li = soup.select_one("ul.pages-items li.item.pages-item-next a.action.next")
            if not next_li or not next_li.get("href"):
                logging.info("No se encontró 'Siguiente'. Fin de paginación.")
                break

            next_url = urljoin(BASE_URL, next_li["href"])
            logging.info(f"Pasando a la siguiente página: {next_url}")

            # Ir a la siguiente página
            page.goto(next_url, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)

    def extract_product_details(self, page, product_url, category):
        """
        Extrae datos del producto:
          - Subcategoría = primera palabra del nombre
          - Resto igual a tu script actual
        """
        try:
            soup = BeautifulSoup(page.content(), "html.parser")

            # 1) Nombre => <h1 class="page-title">
            product_name = "Sin Nombre"
            name_tag = soup.find("h1", class_="page-title")
            if name_tag:
                product_name = name_tag.get_text(strip=True)

            # 2) Subcategoría = primera palabra
            subcategory = product_name.split()[0] if product_name else ""

            # 3) SKU
            sku = "SinSKU"
            sku_div = soup.find("div", class_="product attribute sku")
            if sku_div:
                sku_val_div = sku_div.find("div", id="sku-value")
                if sku_val_div:
                    sku = sku_val_div.get_text(strip=True)

            # 4) Precio
            price_val = 0.0
            price_span = soup.select_one("span.price")
            if price_span:
                price_str = re.sub(r"[^\d,\.]", "", price_span.get_text(strip=True)).replace(",", ".")
                if price_str:
                    try:
                        price_val = float(price_str)
                    except:
                        price_val = 0.0

            # 5) Imagen => <img class="fotorama__img" ...
            image_url = "Sin imagen"
            img_tag = soup.find("img", {"class": "fotorama__img"})
            if img_tag and img_tag.has_attr("src"):
                image_url = img_tag["src"]

            # 6) Descripción => "Marca: X", "Composición", "Hecho en..."
            descripcion = "Sin descripción"
            marca = "N/D"
            composition = ""
            made_in = None

            desc_div = soup.find("div", id="description")
            if desc_div:
                desc_attr = desc_div.find("div", class_="product attribute description")
                if desc_attr:
                    desc_value = desc_attr.find("div", id="description-value")
                    if desc_value:
                        descripcion = desc_value.get_text(separator=" | ", strip=True)

                        # Marca => "Marca: X"
                        match_marca = re.search(r"Marca:\s*([^\.,|]+)", descripcion, re.IGNORECASE)
                        if match_marca:
                            marca = match_marca.group(1).strip()

                        # Composición => "Composición material: 100% Algodón"
                        match_comp = re.search(r"Composición(?: material)?:\s*([^\.,|]+)", descripcion, re.IGNORECASE)
                        if match_comp:
                            composition = match_comp.group(1).strip()

                        # Hecho en => "Hecho en X" o "País de producción"
                        match_madein = re.search(r"(?:Hecho en|País de producción):\s*([^\.,|]+)", descripcion, re.IGNORECASE)
                        if match_madein:
                            made_in = match_madein.group(1).strip()

            # 7) Color => "modelo"
            color = "No especificado"
            color_div = soup.select_one("div.swatch-attribute.color")
            if color_div:
                selected_span = color_div.select_one("span.swatch-attribute-selected-option")
                if selected_span:
                    color_txt = selected_span.get_text(strip=True)
                    if color_txt:
                        color = color_txt
                if color == "No especificado":
                    sel_opt = color_div.find("div", class_="swatch-option color selected")
                    if sel_opt and sel_opt.has_attr("data-option-label"):
                        color = sel_opt["data-option-label"].strip()

            # 8) Tallas => "stock"
            tamanos = []
            talla_div = soup.find("div", class_="swatch-attribute talla_calzado")
            if not talla_div:
                talla_div = soup.find("div", class_="swatch-attribute talla_ropa")
            if talla_div:
                # a) <select class="swatch-select">
                select_tag = talla_div.find("select", class_="swatch-select")
                if select_tag:
                    for opt in select_tag.find_all("option"):
                        val = opt.get_text(strip=True)
                        if val and "Elegir" not in val:
                            tamanos.append(val)
                # b) <div class="swatch-option text">
                text_options = talla_div.find_all("div", class_="swatch-option text")
                for opt in text_options:
                    size_txt = opt.get_text(strip=True)
                    if size_txt and "Elegir" not in size_txt:
                        tamanos.append(size_txt)

            if not tamanos:
                tamanos = ["default"]

            # 9) Generar registros (uno por talla)
            for talla in tamanos:
                upc_val = f"{sku}_{color}_{talla}"
                record = {
                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                    "canal": "EKONO (CR)",
                    "category": category,
                    "subcategory": subcategory,
                    "subcategory_2": "",
                    "subcategory_3": None,
                    "marca": marca,
                    "modelo": color,
                    "sku": sku,
                    "upc": upc_val,
                    "item": product_name,
                    "item_characteristics": descripcion,
                    "url sku": product_url,
                    "image": image_url,
                    "price": price_val,
                    "sale_price": None,
                    "shipment cost": "available" if price_val > 0 else "not available",
                    "sales flag": "",
                    "store id": "9999_ekono_cr",
                    "store name": "ONLINE",
                    "store address": "ONLINE",
                    "stock": talla,
                    "upc wm": sku,
                    "final_price": price_val,
                    "upc wm2": sku,
                    "comp": None,
                    "composition": composition,
                    "made_in": made_in,
                    "url item": product_url
                }
                self.records.append(record)
                logging.info(f"Producto extraído: {record}")

        except Exception as e:
            logging.error(f"Error al extraer detalles del producto {product_url}: {e}")

    def save_to_csv(self):
        """
        Genera el CSV con las mismas columnas que tu script actual.
        """
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        columns = [
            "fecha", "canal", "category", "subcategory", "subcategory_2", "subcategory_3",
            "marca", "modelo", "sku", "upc", "item",
            "item_characteristics", "url sku", "image", "price",
            "sale_price", "shipment cost", "sales flag", "store id",
            "store name", "store address", "stock", "upc wm",
            "final_price", "upc wm2", "comp", "composition",
            "made_in", "url item"
        ]
        df = pd.DataFrame(self.records, columns=columns)
        df.to_csv(file_path, index=False, encoding="utf-8-sig", float_format="%.2f")
        logging.info(f"Datos guardados exitosamente en {file_path}")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    scraper = EkonoScraper()
    scraper.scrape()

import logging
import datetime as dt
import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Configuración global
BASE_URL = "https://dianeandgeordi.cr"
OUTPUT_DIR = "output"
CSV_FILENAME = "diane_geordi_data.csv"

class DianeGeordiScraper:
    def __init__(self):
        self.records = []
        self.processed_categories = set()  # Seguimiento de categorías procesadas
        self.processed_subcategories = set()  # Seguimiento de subcategorías procesadas

    def scrape(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page()
            page.goto(BASE_URL)
            logging.info(f"Navegando a la página principal: {BASE_URL}")

            try:
                page.wait_for_selector("li.h2m-main-menu-item", timeout=60000)
            except Exception as e:
                logging.error(f"Error al cargar la página principal: {e}")
                return

            html_content = page.content()
            self.process_categories(html_content, page)

            # Guardar datos en CSV
            self.save_to_csv()
            browser.close()

    def process_categories(self, html_content, page):
        soup = BeautifulSoup(html_content, "html.parser")
        categories = soup.select("li.h2m-main-menu-item")

        if not categories:
            logging.error("No se encontraron categorías principales en la página.")
            return

        for category in categories:
            category_name = category.find("a").text.strip()
            category_url = urljoin(BASE_URL, category.find("a")["href"])

            if category_url in self.processed_categories:
                logging.info(f"Categoría ya procesada: {category_name}")
                continue

            if category_name.lower() not in ["mujer"]:
                continue

            logging.info(f"Procesando la categoría: {category_name}")
            self.processed_categories.add(category_url)

            subcategory_blocks = category.select("div.h2m-block--title_text")
            for subcategory_block in subcategory_blocks:
                subcategory_name = subcategory_block.text.strip()

                subcategory_2_links = subcategory_block.find_next("ul").find_all("a", class_="h2m-megamenu__link_clickable")
                for subcategory_2_link in subcategory_2_links:
                    subcategory_2_name = subcategory_2_link.text.strip()
                    subcategory_2_url = urljoin(BASE_URL, subcategory_2_link["href"])

                    if subcategory_2_url in self.processed_subcategories:
                        logging.info(f"Subcategoría ya procesada: {subcategory_2_name}")
                        continue

                    logging.info(f"Procesando subcategoría_2: {subcategory_2_name}")
                    self.processed_subcategories.add(subcategory_2_url)
                    self.process_products(subcategory_2_url, category_name, subcategory_name, subcategory_2_name, page)

    def process_products(self, url, category, subcategory, subcategory_2, page):
        try:
            page.goto(url, timeout=90000)
            page.wait_for_load_state("networkidle", timeout=90000)

            while True:
                soup = BeautifulSoup(page.content(), "html.parser")
                products = soup.select("a.product-link")

                if not products:
                    logging.warning(f"No se encontraron productos en: {url}")
                    break

                logging.info(f"Se encontraron {len(products)} productos en: {url}")
                for product in products:
                    product_url = urljoin(BASE_URL, product["href"])
                    self.extract_product_details(product_url, category, subcategory, subcategory_2, page)

                next_button = page.query_selector("a.next-pagination")
                if next_button:
                    next_url = urljoin(BASE_URL, next_button.get_attribute("href"))
                    logging.info(f"Navegando a la siguiente página: {next_url}")
                    page.goto(next_url, timeout=60000)
                else:
                    break
        except Exception as e:
            logging.error(f"Error al procesar productos en {url}: {e}")

    def extract_product_details(self, product_url, category, subcategory, subcategory_2, page):
        """
        Extraer detalles de un producto.
        """
        try:
            page.goto(product_url, timeout=60000)  # Aumentar timeout
            page.wait_for_load_state("networkidle")
            soup = BeautifulSoup(page.content(), "html.parser")

            # Extraer información básica del producto
            name = soup.find("h1", class_="product__title").text.strip() if soup.find("h1", class_="product__title") else "Sin nombre"
            description = (
                soup.select_one(".accordion-content__entry")
                .get_text(separator=" ", strip=True)
                .replace("\n", " ")  # Eliminar saltos de línea
                if soup.select_one(".accordion-content__entry")
                else "Sin descripción"
            )

            # Extraer SKU del nombre del producto (entre paréntesis)
            sku = re.search(r"\((.*?)\)", name).group(1) if re.search(r"\((.*?)\)", name) else "NoSKU"

            # Extraer colores (modelos)
            colors = []
            color_elements = soup.select("input[name='options[Color]']")
            for color in color_elements:
                if "disabled" not in color.attrs:
                    colors.append(color["value"])

            if not colors:
                colors = ["Sin modelo"]

            # Extraer tallas disponibles
            sizes = []
            size_elements = soup.select("input[name='options[Talla]']")
            for size in size_elements:
                if "disabled" not in size.attrs:
                    sizes.append(size["value"])

            # Extraer precio desde el elemento HTML
            price_element = soup.select_one("[data-product-price]")
            if price_element:
                price_text = re.sub(r"[^\d,]", "", price_element.text)  # Remover caracteres no numéricos excepto comas
                price = float(price_text.replace(",", "."))  # Convertir a número decimal
            else:
                price = 0.0

            # Extraer imagen del producto
            image_element = soup.find("meta", {"property": "og:image"})
            image_url = image_element["content"] if image_element else "No image URL"

            # Extraer composición desde la descripción
            # Extraer composición desde la última palabra "TELA" hasta "Diseñado"
            try:
                # Encontrar todas las coincidencias de "TELA" hasta "Diseñado"
                matches = list(re.finditer(r"TELA\s*(.*?)Diseñado", description, re.IGNORECASE))
                
                if matches:
                    # Tomar la última coincidencia
                    composition = matches[-1].group(1).strip()
                else:
                    composition = "No composition"
            except Exception as e:
                logging.warning(f"Error al extraer la composición: {e}")
                composition = "No composition"


            # Extraer "made_in" desde la descripción
            made_in = "Not specified"  # Valor predeterminado
            try:
                made_in_match = re.search(
                    r"(Diseñado y producido en\s+[^\.\n]+|Fabricado en\s+[^\.\n]+)", description, re.IGNORECASE
                )
                if made_in_match:
                    made_in = made_in_match.group(0).strip()
            except Exception as e:
                logging.error(f"Error al extraer 'made_in': {e}")

            # Generar registros para cada combinación de color y talla
            for color in colors:
                for size in sizes:
                    upc = f"{sku}_{color}_{size}"
                    record = {
                        "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                        "canal": "Diane & Geordi (CR)",
                        "category": category,
                        "subcategory": subcategory,
                        "subcategory_2": subcategory_2,
                        "subcategory_3": None,
                        "marca": "Diane & Geordi",
                        "modelo": color,
                        "sku": sku,
                        "upc": upc,
                        "item": name,
                        "item_characteristics": description,
                        "url sku": product_url,
                        "image": image_url,
                        "price": price,
                        "sale_price": None,
                        "shipment cost": "available" if price > 0 else "not available",
                        "sales flag": "regular",
                        "store id": "9999_dg_cr",
                        "store name": "ONLINE",
                        "store address": "ONLINE",
                        "stock": size,
                        "upc wm": sku,
                        "final_price": price,
                        "upc wm2": sku,
                        "comp": None,
                        "composition": composition,
                        "made_in": made_in,
                        "url item": product_url,
                    }
                    self.records.append(record)
                    logging.info(f"Producto extraído: {record}")

        except Exception as e:
            logging.error(f"Error al extraer detalles del producto {product_url}: {e}")


    def save_to_csv(self):
        """
        Guardar los datos en un archivo CSV.
        """
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        df = pd.DataFrame(self.records)
        df.to_csv(file_path, index=False, encoding="utf-8-sig", float_format="%.2f")  # Formatear floats
        logging.info(f"Datos guardados exitosamente en {file_path}")



if __name__ == "__main__":
    scraper = DianeGeordiScraper()
    scraper.scrape()

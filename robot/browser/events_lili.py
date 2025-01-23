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

BASE_URL = "https://lilipink.cr"
OUTPUT_DIR = "output"
CSV_FILENAME = "lili_pink_data.csv"

class LiliPinkScraper:
    def __init__(self):
        self.records = []

    def scrape(self):
        with sync_playwright() as p:
            # 1. Iniciar el navegador
            browser = p.firefox.launch(headless=False)

            # 2. Crear contexto con user_agent
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            )

            # 3. Crear página a partir del contexto
            page = context.new_page()

            try:
                # Navegar a la página principal
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
                logging.info(f"Navegando a la página principal: {BASE_URL}")

                # Si aparece popup, cerrar
                popup_close_selector = "button.popup-close"
                if page.query_selector(popup_close_selector):
                    popup_button = page.query_selector(popup_close_selector)
                    if popup_button.is_visible():
                        logging.info("Popup detectado. Cerrando...")
                        popup_button.click()
                        page.wait_for_timeout(2000)

                # Procesar categorías
                self.process_categories(page.content(), page)

            except Exception as e:
                # Capturamos screenshot si hay un error
                page.screenshot(path="error_screenshot.png")
                logging.error(f"Error al cargar la página principal: {e}")

            finally:
                # Guardamos los resultados en CSV
                self.save_to_csv()
                context.close()
                browser.close()

    def process_categories(self, html_content, page):
        # Parsear HTML actual
        soup = BeautifulSoup(html_content, "html.parser")
        categories = soup.select("nav.header__inline-menu summary")

        if not categories:
            logging.error("No se encontraron categorías en el menú.")
            return

        for category in categories:
            category_name = category.text.strip()
            # Ajustar para BRASIERES Y TOPS, CALZONES, TRAJES DE BAÑO
            if category_name not in ["BRASIERES Y TOPS", "CALZONES", "TRAJES DE BAÑO"]:
                continue

            logging.info(f"Procesando categoría: {category_name}")

            subcategory_ul = category.find_next("ul")
            if not subcategory_ul:
                logging.warning(f"No se encontró <ul> para la categoría: {category_name}")
                continue

            subcategory_links = subcategory_ul.select("a")
            for subcat in subcategory_links:
                subcat_name = subcat.text.strip()
                subcat_url = urljoin(BASE_URL, subcat["href"])
                logging.info(f"Procesando subcategoría: {subcat_name} - {subcat_url}")
                self.process_products(subcat_url, category_name, subcat_name, page)

    def process_products(self, url, category, subcategory, page):
        """
        Abre la subcategoría y busca productos. Maneja paginación si existe.
        """
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_load_state("networkidle", timeout=90000)

            while True:
                soup = BeautifulSoup(page.content(), "html.parser")
                products = soup.select("div.card__content > h3 > a")

                if not products:
                    logging.warning(f"No se encontraron productos en: {url}")
                    break

                logging.info(f"Se encontraron {len(products)} productos en: {url}")
                for product in products:
                    product_url = urljoin(BASE_URL, product["href"])
                    self.extract_product_details(product_url, category, subcategory, page)

                # Manejo de paginación
                next_button = page.query_selector("a.pagination__next")
                if next_button:
                    next_url = urljoin(BASE_URL, next_button.get_attribute("href"))
                    logging.info(f"Navegando a la siguiente página: {next_url}")
                    page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
                else:
                    break
        except Exception as e:
            logging.error(f"Error al procesar productos en {url}: {e}")

    def extract_product_details(self, product_url, category, subcategory, page):
        """
        Extrae detalles de un producto y los guarda en self.records.
        """
        try:
            page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("networkidle")
            soup = BeautifulSoup(page.content(), "html.parser")

            # Nombre
            name_tag = soup.find("h1", class_="product__title")
            name = name_tag.get_text(strip=True) if name_tag else "Sin nombre"

            # Descripción
            desc_tag = soup.find("div", class_="product__description")
            description = desc_tag.get_text(" ", strip=True) if desc_tag else "Sin descripción"

            # SKU (opcional: buscar entre paréntesis en el nombre)
            match_sku = re.search(r"\((.*?)\)", name)
            sku = match_sku.group(1) if match_sku else "NoSKU"

            # Precio
            price_val = 0.0
            price_tag = soup.find("span", class_="price-item")
            if price_tag:
                price_str = price_tag.get_text(strip=True).replace("₡", "").replace(",", "")
                if price_str.isdigit():
                    price_val = float(price_str)

            # Imagen
            img_meta = soup.find("meta", {"property": "og:image"})
            image_url = img_meta["content"] if img_meta else "No image URL"

            # Asignar valores por defecto
            color = "Sin modelo"
            talla = "Sin talla"

            # Registro
            record = {
                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                "canal": "Lili Pink",
                "category": category,
                "marca": "Lili Pink",
                "modelo": color,
                "sku": sku,
                "upc": f"{sku}_{color}_{talla}",
                "item": name,
                "item_characteristics": description,
                "url sku": product_url,
                "image": image_url,
                "price": price_val,
                "sale_price": None,
                "shipment cost": "available" if price_val > 0 else "not available",
                "sales flag": "regular",
                "store id": "9999_lp_cr",
                "store name": "ONLINE",
                "store address": "ONLINE",
                "stock": talla,
                "comp": None,
                "composition": "No composition",
                "made_in": "Not specified",
                "url item": product_url,
            }
            self.records.append(record)
            logging.info(f"Producto extraído: {record}")

        except Exception as e:
            logging.error(f"Error al extraer detalles del producto {product_url}: {e}")

    def save_to_csv(self):
        """
        Guarda los datos recolectados en un archivo CSV.
        """
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        df = pd.DataFrame(self.records)
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        logging.info(f"Datos guardados exitosamente en {file_path}")


if __name__ == "__main__":
    scraper = LiliPinkScraper()
    scraper.scrape()

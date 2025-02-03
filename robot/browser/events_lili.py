import logging
import datetime as dt
import os
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

COLLECTION_URLS = [
    "https://lilipink.cr/collections/conjunto",
    "https://lilipink.cr/collections/brasier",
    "https://lilipink.cr/collections/calzon",
    "https://lilipink.cr/collections/fajas",
]

OUTPUT_DIR = "output_lilipink"
CSV_FILENAME = "lili_pink_data.csv"

class LiliPinkScraper:
    def __init__(self):
        self.records = []
        self.processed_urls = set()

    def remove_popup_forcefully(self, page):
        """Intenta eliminar por la fuerza el popup #pop-convert-app si existe."""
        try:
            page.wait_for_selector("#pop-convert-app", state="attached", timeout=3000)
            logging.info("El popup #pop-convert-app está en el DOM. Intentando eliminarlo...")

            page.evaluate("""
                () => {
                    const popup = document.querySelector('#pop-convert-app');
                    if (popup) {
                        popup.remove();
                    }
                }
            """)
            # Esperar a que el popup ya no exista
            page.wait_for_selector("#pop-convert-app", state="detached", timeout=2000)
            logging.info("Popup #pop-convert-app eliminado con éxito.")
        except Exception as e:
            logging.warning(f"No se pudo eliminar #pop-convert-app (posiblemente no existe): {e}")

    def scrape(self):
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            context = browser.new_context(viewport={"width":1280, "height":720})
            page = context.new_page()

            for url in COLLECTION_URLS:
                # La "categoría" la sacamos de la parte final de la URL
                # Ejemplo: https://lilipink.cr/collections/conjunto => "conjunto"
                category_name = url.rsplit("/collections/", 1)[-1].strip().lower()
                logging.info(f"[COLLECTION] Navegando a {url} (Category: {category_name})")

                try:
                    page.goto(url, timeout=60000)

                    # Eliminar popup si aparece
                    self.remove_popup_forcefully(page)

                    # Esperar a que cargue la lista de productos (ajustar selector)
                    page.wait_for_selector("div.card-wrapper.product-card-wrapper", timeout=30000)

                except Exception as e:
                    logging.error(f"Error al cargar la colección {url}: {e}")
                    continue

                self.process_collection_pages(page, category_name)

            self.save_to_csv()
            context.close()
            browser.close()

    def process_collection_pages(self, page, category_name):
        """Recorre la paginación de la colección y extrae productos."""
        while True:
            soup = BeautifulSoup(page.content(), "html.parser")

            # Extraer los productos
            product_cards = soup.select("div.card-wrapper.product-card-wrapper h3.card__heading a")
            logging.info(f"Se encontraron {len(product_cards)} productos en esta página: {page.url}")

            for link_tag in product_cards:
                href = link_tag.get("href")
                if not href:
                    continue
                product_url = urljoin(page.url, href)

                if product_url in self.processed_urls:
                    continue
                self.processed_urls.add(product_url)

                self.extract_product_detail(page, product_url, category_name)

            # Buscar la paginación
            pagination_nav = soup.find("nav", class_="pagination")
            if not pagination_nav:
                logging.info("No hay <nav class='pagination'>. Fin de esta colección.")
                break

            # 1) Intenta localizar específicamente el enlace de "página siguiente"
            next_a = pagination_nav.select_one("a[aria-label='Página siguiente']")
            
            if not next_a:
                logging.info("No se encontró el link con aria-label='Página siguiente'. Fin paginación.")
                break

            # 2) Construir la URL completa y navegar
            next_url = urljoin(page.url, next_a["href"])
            logging.info(f"Siguiente página => {next_url}")

            try:
                page.goto(next_url, timeout=30000)
                self.remove_popup_forcefully(page)
                page.wait_for_selector("div.card-wrapper.product-card-wrapper", timeout=30000)
            except Exception as e:
                logging.error(f"Error al navegar a la siguiente página {next_url}: {e}")
                break

    def extract_product_detail(self, page, product_url, category_name):
        """
        Abre la página de detalle del producto, espera a que cargue,
        extrae información y genera uno o varios registros (si hay variantes).
        """
        try:
            page.goto(product_url, timeout=60000)
            self.remove_popup_forcefully(page)

            # En vez de esperar el h1, esperamos algo más estable como el contenedor principal
            # o también usar page.wait_for_load_state("networkidle").
            page.wait_for_selector("div.product__info-wrapper", timeout=40000)

            # Esperar un poco adicional por si el contenido es dinámico
            page.wait_for_timeout(1000)

            soup = BeautifulSoup(page.content(), "html.parser")

            # 1) Nombre del producto
            # A veces está en div.product__title h1
            name_tag = soup.select_one("div.product__title h1")
            if not name_tag:
                # Fallback
                name_tag = soup.select_one("div.product__title h2")
            name = name_tag.get_text(strip=True) if name_tag else "Sin nombre"

            # 2) Descripción
            desc_div = soup.select_one("div.product__description")
            description = desc_div.get_text(" ", strip=True) if desc_div else ""

            # 3) Buscar un <script type="application/json"> dentro de <variant-radios> para extraer variantes
            variants_json = []
            variant_script = soup.select_one("variant-radios script[type='application/json']")
            if variant_script:
                try:
                    variants_json = json.loads(variant_script.get_text(strip=True))
                except Exception as e:
                    logging.warning(f"No se pudo parsear JSON de variantes: {e}")

            # 4) Imagen principal (puede que og:image funcione, o parsear <div class="product-media-container">
            # Revisamos og:image primero:
            image_url = "Sin imagen"
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                image_url = og_img["content"].strip()
            else:
                # Fallback: Buscar <img class="image-magnify-lightbox">
                img_tag = soup.select_one("img.image-magnify-lightbox")
                if img_tag and img_tag.has_attr("src"):
                    image_url = img_tag["src"]

            # 5) Si hay variantes, creamos un registro por cada una
            if variants_json:
                for variant in variants_json:
                    # SKU real del backend
                    sku_real = variant.get("sku", "NoSKU").strip()
                    # OJO: el price viene en centavos => 1699000 => 16990.00 colones
                    raw_price = variant.get("price", 0)
                    price_val = raw_price / 100.0

                    # Ej: "NEGRO / M"
                    variant_title = variant.get("title", "")
                    color = variant.get("option1", "")
                    talla = variant.get("option2", "")

                    record = {
                        "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                        "canal": "Lili Pink",
                        "category": category_name,  # la categoría deducida
                        "marca": "Lili Pink",
                        "modelo": color if color else "N/D",
                        "sku": sku_real,
                        "upc": f"{sku_real}_{color}_{talla}",
                        "item": name,
                        "item_characteristics": description,
                        "url sku": product_url,
                        "image": image_url,
                        "price": price_val,
                        "sale_price": None,
                        "shipment cost": "available" if price_val > 0 else "not available",
                        "sales flag": "",
                        "store id": "9999_lp_cr",
                        "store name": "ONLINE",
                        "store address": "ONLINE",
                        "stock": talla,
                        "comp": None,
                        "composition": "",
                        "made_in": "",
                        "url item": product_url,
                    }
                    self.records.append(record)
                    logging.info(f"[DETAIL - variant] {record}")

            else:
                # Si no hay JSON de variantes, creamos un solo registro
                # (Puede darse en productos sin opciones).
                price_val = 0.0
                price_tag = soup.select_one("span.price-item.price-item--regular") \
                            or soup.select_one("span.price-item.price-item--sale")
                if price_tag:
                    text_price = re.sub(r"[^\d,\.]", "", price_tag.get_text(strip=True)).replace(",", "")
                    # Quita la posible coma de miles, etc. e intenta convertir
                    if text_price:
                        try:
                            price_val = float(text_price)
                        except:
                            pass

                record = {
                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                    "canal": "Lili Pink",
                    "category": category_name,
                    "marca": "Lili Pink",
                    "modelo": "Sin modelo",
                    "sku": "NoSKU",
                    "upc": f"NoSKU_{name}",
                    "item": name,
                    "item_characteristics": description,
                    "url sku": product_url,
                    "image": image_url,
                    "price": price_val,
                    "sale_price": None,
                    "shipment cost": "available" if price_val > 0 else "not available",
                    "sales flag": "",
                    "store id": "9999_lp_cr",
                    "store name": "ONLINE",
                    "store address": "ONLINE",
                    "stock": "N/A",
                    "comp": None,
                    "composition": "",
                    "made_in": "",
                    "url item": product_url,
                }
                self.records.append(record)
                logging.info(f"[DETAIL - single] {record}")

        except Exception as e:
            logging.error(f"Error al extraer detalle del producto {product_url}: {e}")

    def save_to_csv(self):
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        df = pd.DataFrame(self.records)
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        logging.info(f"Datos guardados en {file_path}")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    scraper = LiliPinkScraper()
    scraper.scrape()

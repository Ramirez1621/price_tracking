import logging
import datetime as dt
import os
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s] %(message)s")

# URLs de colecciones de Lili Pink
COLLECTION_URLS = [
    "https://lilipink.cr/collections/conjunto",
    "https://lilipink.cr/collections/brasier",
    "https://lilipink.cr/collections/calzon",
    "https://lilipink.cr/collections/fajas",
]

OUTPUT_DIR = "output_lilipink"
CSV_FILENAME = "lili_pink_data.csv"

def parse_to_float(price_str: str) -> float:
    """
    Convierte un string como '₡ 9.796,50' a float => 9796.50
    """
    # Quitar cualquier símbolo no numérico excepto punto y coma
    tmp = re.sub(r"[^\d,\.]", "", price_str).strip()
    # A veces viene con coma decimal => '9.796,50' => reemplazamos el '.' por '' (para miles)
    # y luego la ',' por '.' (para decimales)
    # Ej: '9.796,50' => '9796.50'
    tmp = tmp.replace(".", "").replace(",", ".")
    try:
        return float(tmp)
    except:
        return 0.0

class LiliPinkScraper:
    def __init__(self):
        # Donde guardamos todos los registros extraídos
        self.records = []
        # Para evitar procesar la misma URL de producto dos veces
        self.processed_product_urls = set()
        # Aquí guardamos (product_url, category_name) de todos los productos recopilados
        self.all_links_for_details = []

    def remove_popup_forcefully(self, page):
        """Intenta eliminar por la fuerza el popup #pop-convert-app si existe."""
        try:
            page.wait_for_selector("#pop-convert-app", state="attached", timeout=3000)
            logging.info("[POPUP] #pop-convert-app está en el DOM. Intentando eliminarlo...")

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
            logging.info("[POPUP] Eliminado con éxito.")
        except:
            pass  # Si falla, no pasa nada

    def scrape(self):
        with sync_playwright() as p:
            # 1) Lanzar el navegador en modo headless para que sea rápido
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()

            # 2) Recolectar todos los enlaces de producto de cada colección
            for url in COLLECTION_URLS:
                category_name = url.rsplit("/collections/", 1)[-1].strip().lower()
                logging.info(f"[GATHER] Colección: {url} => Categoría: {category_name}")
                try:
                    page.goto(url, timeout=30000)
                    self.remove_popup_forcefully(page)
                    page.wait_for_selector("div.card-wrapper.product-card-wrapper", timeout=30000)
                except Exception as e:
                    logging.error(f"Error al cargar la colección {url}: {e}")
                    continue

                self.gather_product_links(page, category_name)

            logging.info(f"[GATHER] Total de enlaces de producto: {len(self.all_links_for_details)}")

            # 3) Abrir cada producto y extraer detalles
            for (prod_url, cat) in self.all_links_for_details:
                if prod_url in self.processed_product_urls:
                    continue
                self.processed_product_urls.add(prod_url)

                try:
                    page.goto(prod_url, timeout=30000)
                    self.remove_popup_forcefully(page)
                    page.wait_for_selector("div.product__info-wrapper", timeout=30000)
                except Exception as e:
                    logging.error(f"Error al cargar detalle {prod_url}: {e}")
                    continue

                # Extraer info
                self.extract_product_details(page, prod_url, cat)

            # 4) Guardar CSV
            self.save_to_csv()
            browser.close()

    def gather_product_links(self, page, category_name):
        """
        Recorre la paginación y recopila todos los links de producto,
        guardándolos en self.all_links_for_details con su categoría.
        """
        while True:
            soup = BeautifulSoup(page.content(), "html.parser")

            cards = soup.select("div.card-wrapper.product-card-wrapper h3.card__heading a")
            logging.info(f"[GATHER] {len(cards)} productos en la página {page.url}")

            for link_tag in cards:
                href = link_tag.get("href")
                if not href:
                    continue
                product_url = urljoin(page.url, href)
                self.all_links_for_details.append((product_url, category_name))

            # Buscar la paginación => link con aria-label="Página siguiente"
            pagination_nav = soup.find("nav", class_="pagination")
            if not pagination_nav:
                logging.info("[GATHER] No hay más paginación, fin de esta colección.")
                break

            next_a = pagination_nav.select_one("a[aria-label='Página siguiente']")
            if not next_a or not next_a.get("href"):
                logging.info("[GATHER] No se encontró página siguiente.")
                break

            next_url = urljoin(page.url, next_a["href"])
            logging.info(f"[GATHER] Siguiente página => {next_url}")
            try:
                page.goto(next_url, timeout=30000)
                self.remove_popup_forcefully(page)
                page.wait_for_selector("div.card-wrapper.product-card-wrapper", timeout=30000)
            except Exception as e:
                logging.error(f"[GATHER] Error navegando a {next_url}: {e}")
                break

    def extract_product_details(self, page, product_url, category_name):
        """
        Extrae la información de detalle del producto, incluida la lógica
        para detectar precios con descuento (price vs. sale_price).
        """
        soup = BeautifulSoup(page.content(), "html.parser")

        # 1) Nombre del producto
        name_tag = soup.select_one("div.product__title h1") or soup.select_one("div.product__title h2")
        name = name_tag.get_text(strip=True) if name_tag else "Sin nombre"

        # 2) Descripción
        desc_div = soup.select_one("div.product__description")
        description = desc_div.get_text(separator=" ", strip=True) if desc_div else ""

        # 3) Obtener imagen principal
        image_url = "Sin imagen"
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            image_url = og_img["content"].strip()
        else:
            # Fallback: <img class="image-magnify-lightbox" ...>
            img_tag = soup.select_one("img.image-magnify-lightbox")
            if img_tag and img_tag.has_attr("src"):
                image_url = img_tag["src"]

        # 4) Ver si hay JSON de variantes
        variants_json = []
        variant_script = soup.select_one("variant-radios script[type='application/json']")
        if variant_script:
            try:
                variants_json = json.loads(variant_script.get_text(strip=True))
            except Exception as e:
                logging.warning(f"[DETAIL] No se pudo parsear JSON de variantes: {e}")

        # 5) Detectar precios y/o descuentos desde el HTML
        #    (Por si NO hay variantes.)
        #    Nota: si la tienda pone diferentes precios por variante, normalmente
        #    se reflejan en el JSON (compare_at_price, price, etc.).
        price_val = 0.0
        sale_price_val = None

        # El contenedor principal de precio
        price_container = soup.select_one("div.price__container")
        if price_container:
            # Regular = .price__regular -> .price-item--regular
            reg_span = price_container.select_one("div.price__regular span.price-item.price-item--regular")
            # Sale = .price__sale -> .price-item--sale
            sale_span = price_container.select_one("div.price__sale span.price-item.price-item--sale")
            # A veces el precio tachado aparece en <s class="price-item price-item--regular">
            crossed_span = price_container.select_one("div.price__sale s.price-item.price-item--regular")

            if sale_span and crossed_span:
                # Hay oferta => sale_span es el precio con descuento, crossed_span el precio regular
                sale_price_val = parse_to_float(sale_span.get_text(strip=True))
                price_val = parse_to_float(crossed_span.get_text(strip=True))
            else:
                # Sin oferta => parse normal
                if reg_span:
                    price_val = parse_to_float(reg_span.get_text(strip=True))

        # 6) Procesar variantes si existen
        if variants_json:
            for variant in variants_json:
                # SKU puede ser None
                sku_raw = variant.get("sku")
                # Ajustar para no romper en None
                if sku_raw is None:
                    sku = "NoSKU"
                else:
                    sku = sku_raw.strip()

                # El precio vendrá en centavos => 1699000 => 16990.00
                raw_price = variant.get("price", 0)
                variant_price = raw_price / 100.0

                # Si la tienda maneja compare_at_price en JSON => discount
                raw_compare = variant.get("compare_at_price", None)
                variant_sale = None
                if raw_compare and raw_compare > raw_price:
                    # El compare_at_price es mayor => ese es el "precio original", raw_price es la oferta
                    variant_sale = variant_price
                    variant_price = raw_compare / 100.0
                # OJO: no todas las tiendas lo rellenan.

                color = variant.get("option1", "")
                talla = variant.get("option2", "")

                # Si no hay compare_at_price, usamos la detección global de la página
                # omitir la parte "price_container" de arriba.
                final_price = variant_price if raw_price else price_val
                final_sale_price = variant_sale if variant_sale else sale_price_val

                record = {
                    "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                    "canal": "Lili Pink",
                    "category": category_name,
                    "subcategory": "",
                    "subcategory_2": "",
                    "subcategory_3": None,
                    "marca": "Lili Pink",
                    "modelo": color if color else "N/D",
                    "sku": sku,
                    "upc": f"{sku}_{color}_{talla}",
                    "item": name,
                    "item_characteristics": description,
                    "url sku": product_url,
                    "image": image_url,
                    "price": final_price,          # precio regular
                    "sale_price": final_sale_price,  # oferta
                    "shipment cost": "available" if final_price > 0 else "not available",
                    "sales flag": "on_sale" if final_sale_price else "",
                    "store id": "9999_lp_cr",
                    "store name": "ONLINE",
                    "store address": "ONLINE",
                    "stock": talla,
                    "upc wm": sku,
                    "final_price": final_sale_price if final_sale_price else final_price,
                    "upc wm2": sku,
                    "comp": None,
                    "composition": "",
                    "made_in": "",
                    "url item": product_url,
                }
                self.records.append(record)
                logging.info(f"[DETAIL-variant] {record}")

        else:
            # Sin variantes => 1 registro
            record = {
                "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                "canal": "Lili Pink",
                "category": category_name,
                "subcategory": "",
                "subcategory_2": "",
                "subcategory_3": None,
                "marca": "Lili Pink",
                "modelo": "Sin modelo",
                "sku": "NoSKU",
                "upc": f"NoSKU_{name}",
                "item": name,
                "item_characteristics": description,
                "url sku": product_url,
                "image": image_url,
                "price": price_val,       # precio regular
                "sale_price": sale_price_val,  # oferta si existe
                "shipment cost": "available" if price_val > 0 else "not available",
                "sales flag": "on_sale" if sale_price_val else "",
                "store id": "9999_lp_cr",
                "store name": "ONLINE",
                "store address": "ONLINE",
                "stock": "N/A",
                "upc wm": "NoSKU",
                "final_price": sale_price_val if sale_price_val else price_val,
                "upc wm2": "NoSKU",
                "comp": None,
                "composition": "",
                "made_in": "",
                "url item": product_url,
            }
            self.records.append(record)
            logging.info(f"[DETAIL-single] {record}")

    def save_to_csv(self):
        if not self.records:
            logging.warning("No hay datos para guardar.")
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        file_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

        # Definimos columnas en el orden que tú quieras
        columns = [
            "fecha", "canal", "category", "subcategory", "subcategory_2", "subcategory_3",
            "marca", "modelo", "sku", "upc", "item",
            "item_characteristics", "url sku", "image", "price",
            "sale_price", "shipment cost", "sales flag", "store id",
            "store name", "store address", "stock", "upc wm",
            "final_price", "upc wm2", "comp", "composition",
            "made_in", "url item"
        ]
        df = pd.DataFrame(self.records)
        
        # Asegurarnos de que existan todas las columnas
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        
        # Reordenar
        df = df[columns]

        df.to_csv(file_path, index=False, encoding="utf-8-sig", float_format="%.2f")
        logging.info(f"[CSV] Datos guardados en {file_path}")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    scraper = LiliPinkScraper()
    scraper.scrape()

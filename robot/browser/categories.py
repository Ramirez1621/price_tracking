import requests
from bs4 import BeautifulSoup

# Definimos las 5 categorías principales que nos interesan, en mayúsculas
TARGET_MAIN_CATEGORIES = ["HOMBRE", "MUJER", "FAJAS", "SALE", "NIÑOS"]

def extract_categories_and_subcategories(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Diccionario final: { "Hombre": {"url": "...", "subcats": [(subcat_name, subcat_url), ...]}, ... }
    result = {}

    # 1) Encontrar todos los <li> que parecen ser “categorías” en el menú
    #    En tu HTML, son algo como: <li class="h2m-menu-item h2m-main-menu-item ...">
    main_items = soup.select("li.h2m-menu-item.h2m-main-menu-item") 

    for li_item in main_items:
        # 2) Dentro de cada <li>, hay un <a> con la clase "h2m-menu-item-inner"
        #    y un <span class="h2m-menu-title h2m-txt-val"> con el texto de la categoría
        main_link = li_item.select_one("a.h2m-menu-item-inner")
        if not main_link:
            continue

        # Nombre de la categoría principal
        title_span = main_link.select_one("span.h2m-menu-title.h2m-txt-val")
        if not title_span:
            continue

        cat_name = title_span.get_text(strip=True).upper()  # para comparación
        cat_href = main_link.get("href", "")

        # 3) Verificamos si está en nuestra lista de interés
        if cat_name in TARGET_MAIN_CATEGORIES:
            # Ajustar href si es relativo
            if cat_href.startswith("/"):
                cat_href = "https://dianeandgeordi.cr" + cat_href

            # Creamos la entrada en nuestro diccionario
            result[cat_name] = {
                "url": cat_href,
                "subcats": []  # la lista de subcategorías
            }

            # 4) Ahora buscamos “subcategorías” dentro del mismo <li>
            #    Normalmente, si hay subcategorías, se guardan en un <div class="h2m-mega-wrapper ...">
            #    o <ul class="h2m-submenu-content ...">
            #    Vamos a buscar enlaces <a> con su texto dentro de esa sección.
            mega_wrapper = li_item.select_one("div.h2m-mega-wrapper") 
            if not mega_wrapper:
                # A veces, si no hay subcategorías, no existirá este div
                continue

            # Dentro de mega_wrapper, suelen aparecer <li class="h2m-megamenu-item link ..."><a ...>Subcat</a>
            subcat_links = mega_wrapper.select("li.h2m-megamenu-item.link a")

            # Recorremos cada subcategoría
            for s_link in subcat_links:
                subcat_name_elem = s_link.select_one("span.h2m-menu-item-title span.h2m-txt-val")
                if not subcat_name_elem:
                    # A veces puede no tener esa estructura exacta, 
                    # podrías usar s_link.get_text(strip=True)
                    continue

                subcat_name = subcat_name_elem.get_text(strip=True)
                subcat_href = s_link.get("href", "")
                
                # Ajustar URL si es relativo
                if subcat_href.startswith("/"):
                    subcat_href = "https://dianeandgeordi.cr" + subcat_href

                # Añadimos a la lista de subcategorías
                result[cat_name]["subcats"].append((subcat_name, subcat_href))

    return result


if __name__ == "__main__":
    url_home = "https://dianeandgeordi.cr/"  
    data = extract_categories_and_subcategories(url_home)

    for main_cat, info in data.items():
        print(f"Categoría principal: {main_cat} => {info['url']}")
        if info["subcats"]:
            print("  Subcategorías:")
            for (subcat_name, subcat_url) in info["subcats"]:
                print(f"    - {subcat_name} => {subcat_url}")
        else:
            print("  (No hay subcategorías o no se encontraron)")
        print()

import logging
import datetime as dt
import time

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException
# from robot.manage_directories import report_downloaded
from settings import ZARA_URL, MAX_TIME, DATE
from tenacity import retry, wait_random_exponential, stop_after_attempt


class zaraSession():
    def __init__(self, driver: Firefox):
        self.records = list()
        self.open_page(driver)
        self.select_categories(driver)
        return self.records

    def open_page(self, driver: Firefox):
        try:
            driver.get(url=ZARA_URL)

        except Exception as e:
            # print(f"The following exception has ocurred during login: {e}")
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)


    def select_categories(self, driver: Firefox):
        try:
            categories = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                    (By.XPATH, "//button[contains(@class,'slider-spot-universes-bar__ite')]")))
            for i in range(len(categories)):
                # Get and click on category button
                categories = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                    (By.XPATH, "//button[contains(@class,'slider-spot-universes-bar__ite')]")))
                category = categories[i].get_attribute("innerText")
                categories[i].click()

                self.record = dict({"canal":"Zara Colombia"})
                self.record["category"] = category

                self.select_subcategory(driver)
                
            
        except Exception as e:
            logging.error(
                (f"An error has ocurred during report selection: {type(e)}"))
            raise(e)

    def select_subcategory(self, driver: Firefox):
        subcategories = WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                (By.XPATH, "//ul[contains(@class,'layout-categories-category__subcategory-main')]/li[contains(@class,'layout-categories-category--level-2') and contains(@data-layout,'products-category-view')]/a")))
        # driver.find_elements(By.XPATH, "//ul[contains(@class,'layout-categories-category__subcategory-main')]/li[contains(@data-layout,'products-category-view')]/a")

        subcategories = [(subc.get_attribute('innerText'), subc.get_attribute('href')) for subc in subcategories if subc.get_attribute('href') is not None]

        for subcategory, href in subcategories:
                self.record["subcategory"] = subcategory
                if subcategory == "NEW":
                    continue
                self.subcategory_href = href
                driver.get(self.subcategory_href)

                self.select_subcategories2(driver)

    def select_subcategories2(self, driver: Firefox):
        try:
            subcategories2 = WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                    (By.XPATH, "//a[contains(@class,'category-topbar-related-categories__category-link link')]")))
        
            for i in range(1, len(subcategories2)):
                    subcategories2 = WebDriverWait(driver, 5).until(EC.visibility_of_any_elements_located(
                        (By.XPATH, "//a[contains(@class,'category-topbar-related-categories__category-link link')]")))
                    self.record["subcategory_2"] = subcategories2[i].get_attribute("innerText")
                    # Click on subcategory 2
                    subcategories2[i].click()
                    self.select_product(driver)
                    time.sleep(4)    
        except TimeoutException:
            self.record["subcategory_2"] = None
            self.select_product(driver)

    def retry_exception(self):
        return

    @retry(wait=wait_random_exponential(min=2, max=20), stop=stop_after_attempt(4), reraise=False, retry_error_callback=retry_exception)
    def select_product(self, driver: Firefox):
        try:
            # Switch to grid view
            grid_selector = driver.find_elements(By.XPATH, "//button[contains(@class,'view-option-selector-button')]")
            grid_selector[-1].click()
        except IndexError:
            return
        else:
            # Scan the page for the products
            items =  WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")))
            href_items = list()
            new_items = items

            try:
                while len(new_items):
                
                    href = [item.get_attribute('href') for item in new_items if item.get_attribute('href') is not None]
                    href_items.extend(href)
                    
                    # Scroll to the finish of the page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                    # Wait for load new content
                    time.sleep(1)
                    ref_items = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                        (By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")))
                    
                    new_items = [item for item in ref_items if item not in items]
                    items.extend(new_items)

            except Exception as e:
                print(e)
                raise Exception
            
            href_items = list(set(href_items))
            # Open a new Window on the browser
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            # get the products details
            self.get_product_details(driver, href_items)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            driver.execute_script("window.scrollTo(0, 0)")
            print(self.records)

        # driver.find_elements(By.XPATH, "//ul[contains(@class,'product-grid__product-list')]/li/div/a")
        

    def get_product_details(self, driver: Firefox, items: list):
        for href in items:
            try:
                driver.get(href)

                color_selector = driver.find_elements(By.XPATH, "//ul[contains(@class,'product-detail-color-selector__colors')]/li/button")

                if color_selector:
                    for selector in color_selector:
                        selector.click()
                        self.get_details(driver, href)
                else:
                    self.get_details(driver, href)
                
            except Exception as e:
                print(e)

    def get_details(self, driver: Firefox, href: str):
        sku = self.get_attribute(driver, "//html", attribute="id").replace("product-","")

        item = self.get_attribute(driver, "//h1[contains(@class,'product-detail-info__header-name')]", wait_time=10, type_checking="visibility_of_element_located")

        

        prices = driver.find_elements(By.XPATH, "//div[contains(@class,'product-detail-info__price-amount')]//descendant::span[contains(@class,'money-amount__main')]")
        prices = [int(_.get_attribute("innerText").replace(".","").replace("COP", "")) for _ in prices]

        price = prices[0]
        final_price = price
        if len(prices) > 1:	
            price_sale = prices[1]
            final_price = price_sale
            discount = driver.find_element(By.XPATH, "//div[contains(@class,'product-detail-info__price-amount')]//descendant::span[contains(@class,'price-current__discount-percentage')]").get_attribute("innerText")

        else:
            price_sale, discount = None, None

        color = self.get_attribute(driver, "//p[contains(@class,'product-color-extended-name')]").split(" | ")[0].replace("Color: ","")

        image = self.get_attribute(driver, "//img[contains(@class,'media-image__image media__wrapper--media') and contains(@src,'6_1_1.jpg')]", attribute="src")

        made_in = self.get_attribute(driver, "//div[contains(@class,'product-detail-extra-detail__section')]/div/span[contains(@class,'structured-component-text zds-paragraph-m')]/span", type_checking="presence_of_all_elements_located").replace("Hecho en ", "")

        materials = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@data-observer-key,'materials')]/div[contains(@class,'structured-component-text')]")))
        materials.pop(0), materials.pop(0)
        materials = " ".join([line.get_attribute("innerText") for line in materials])

        care_instructions = driver.find_element(By.XPATH, "//ul[contains(@class,'structured-component-icon-list')]").get_attribute("innerText")

        description = driver.find_element(By.XPATH, "//div[contains(@class,'product-detail-description product-detail-info__description')]").get_attribute("innerText").replace("\n\nVer más","")

        item_characteristics = f"COMPOSICIÓN: {materials} | DESCRIPCIÓN: {description} | CUIDADOS: {care_instructions}"

        stock_sizes = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//ul[contains(@class,'size-selector__size-list')]/li")))
        sizes = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH,"//child::div[contains(@class,'product-size-info__main-label')]")))

        for _size, in_stock in zip(sizes, stock_sizes):
            stock = "available" if in_stock.get_attribute("data-qa-action") == "size-in-stock" else "not available"
            size = _size.get_attribute("innerText")
            self.records.append(
                        {
                            "fecha": dt.datetime.now().strftime("%Y/%m/%d"),
                            "canal": "Zara Colombia",
                            "category": self.record["category"],
                            "subcategory": self.record["subcategory"],
                            "subcategory_2": self.record["subcategory_2"],
                            "sku": sku,
                            "item": item,
                            "price": price,
                            "sale_price": price_sale,
                            "discount_percent": discount,
                            "final_price": final_price,
                            "color": color,
                            "item_characteristics": item_characteristics,
                            "url_sku": href,
                            "image": image,
                            "size": size,
                            "composition": materials,
                            "availability": stock,
                            "made_in": made_in,
                        }
                    )

    def get_attribute(self, driver, xpath_string, wait_time=5, attribute="innerText", type_checking="presence_of_element_located", index=-1):
        try:
            if type_checking == "presence_of_element_located":
                element =  WebDriverWait(driver, wait_time).until(EC.presence_of_element_located(
                    (By.XPATH, xpath_string)))
            elif type_checking == "presence_of_all_elements_located":
                element = WebDriverWait(driver, wait_time).until(EC.presence_of_all_elements_located(
                    (By.XPATH, xpath_string)))[index]
            elif type_checking == "visibility_of_element_located":
                element = WebDriverWait(driver, wait_time).until(EC.visibility_of_element_located(
                    (By.XPATH, xpath_string)))
            
            return element.get_attribute(attribute)
        
        except TimeoutException:
            return None
        except Exception as e:
            print(e)
            raise e
        
from selenium.webdriver import Chrome
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from settings import FIREFOX_DRIVER_PATH, FIREFOX_BINARY


class WebDriver():
    def __init__(self, driver) -> None:
        self.driver = driver

    def __enter__(self):
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()

def open_browser():
    # Browser options
    # options = webdriver.FirefoxOptions()
    # # options.headless = False
    # options.binary_location = FIREFOX_BINARY
    # options.set_preference('devtools.jsonview.enabled', False)
    # options.set_preference("browser.startup.maximized", True)
    # driver_path = FIREFOX_DRIVER_PATH 

    # # firefox_profile = webdriver.FirefoxProfile()
    # # options.set_preference("permissions.default.image", 2)
    # # Service instance for pointing to executable path of Firefox
    # service = FirefoxService(driver_path)
    # driver = webdriver.Firefox(service=service, options=options)
    # driver.maximize_window()
    # return driver


    # Service instance for pointing to executable path of Chrome
    service = Service(ChromeDriverManager().install())
    # Browser options
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument('--headless')  
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver
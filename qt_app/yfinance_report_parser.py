from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
from pyppeteer import launch
import pandas as pd
import os
from bs4 import BeautifulSoup
from multiprocessing import Process
import csv
import re
import random
from importlib import reload
from . import utils
utils = reload(utils)


pkg_path = utils.pkg_path
filename = re.findall('(.*).py', os.path.basename(__file__)) #name excluding extension
utils.errorLog(pkg_path=pkg_path,filename=filename)


#*****************************************
# BrightData Proxy
#US
username  = utils.loadJSON(json_name='brdproxy')['us_username']
password = utils.loadJSON(json_name='brdproxy')['us_password']
port = utils.loadJSON(json_name='brdproxy')['port']
session_id = random.random()
proxy_server = f'http://{username}-country-us-mobile-session-{session_id}:{password}@brd.superproxy.io:{port}'
#*****************************************


options = webdriver.ChromeOptions()

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
options.add_argument(f'user-agent={user_agent}')
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--enable-logging --v=1')
#options.add_argument(f'--proxy-server={proxy_server}')



# Creating the class with full functionality
class ReportScraper:

    def __init__(self):
        self.config = utils.config
        self.data_path = self.config['data_path']
        self.pkg_path = 'yfinance_report_parser/'
        self.folder_path = 'grpStockReportSummary/'
        self.time_value_yfinance = self.config['time_value_yfinance'] #0 Last Week,1 Last Month,2 Last Year


    async def main(self):
        try:
            # Corrected instantiation of Chrome with options
            driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        except:
            # Set up the Selenium WebDriver with the headless option
            driver = webdriver.Chrome(options=options)
        
        # Navigate to the page
        time_value = self.time_value_yfinance[0]
        url = self.config['yfinance_report_url'] + time_value #Accessable only with U.S. IP
        driver.get(url)
        print(f'Navigating to Yahoo! Finance done.')
        await asyncio.sleep(10)


        """[Do not delete]Backup Method In Case of URL Structure Change on finance.yahoo.com
        #############################
        # Find the button using its XPath and click it
        date_range_button = driver.find_element(By.XPATH, "//div[contains(text(), 'Date Range')]")
        date_range_button.click()
        await asyncio.sleep(5)
        # Wait for the dropdown to appear
        dropdown_menu = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dropdown-menu"))
        )
        # Check if the dropdown is displayed
        if dropdown_menu.is_displayed():
            print("Dropdown menu is displayed.")
        else:
            print("Dropdown menu is not displayed.")
        # Locate the time period button using its data-value attribute and click it
        time_period_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-value='{time_value}']"))
        )
        time_period_button.click()
        await asyncio.sleep(5)
        print("Date range '" + time_value + "' selected.")
        #############################"""

        #Calc the total page count with current filters.
        

        #********************
        # Find the div tag by class and then find the span within it
        div_class = "D(ib) Va(m) Fw(500) Fz(m) Pt(5px) D(b)--sm"
        pattern = r'of (\d+) results'
        # Wait until the regex pattern is found in the div's text
        WebDriverWait(driver, 30).until(
            lambda d: re.search(pattern, BeautifulSoup(d.page_source, 'html.parser').find('div', class_=div_class).text) is not None
        )
        #********************


        # Extract the content of the page using selenium
        content = driver.page_source
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')

        
        classes = div_class.split()
        div = soup.find('div', class_=div_class)
        initial_text = div.find('span').text if div else "Div or span not found"
        # Use regex to find the pattern "of [number] results" and extract the number
        match = re.search(pattern, initial_text)





        # Extract the number from the search result if it exists
        total_result = match.group(1) if match else "Initial Text pattern not found"
        total_page = -(-int(total_result)//100) #Ceil division: reverted from a floor division

        print(f'Total page count: {total_page}')

        # Define the custom expected condition
        class TextHasChanged:
            def __init__(self, locator, initial_text):
                self.locator = locator
                self.initial_text = initial_text

            def __call__(self, driver):
                # Find the element
                element = driver.find_element(*self.locator)
                # Check if the text has changed from the initial text
                print(f'Current text: {element.text}')
                print(f'Initial text: {self.initial_text}')
                return element.text != self.initial_text


        # Finalizing the selenium function by adding data extraction and CSV writing logic
        for pagenumber in range(1,total_page + 1):
            print(f'Starting to navigate, currently on page {pagenumber}')
            if pagenumber != 1:
                # Find the 'Next' button using a more specific XPath
                next_button = driver.find_element(By.XPATH, "//button[contains(@class, 'Va(m)') and contains(@class, 'C($linkColor)')]/span/span[text()='Next']")
                next_button.click()
                await asyncio.sleep(10)  # Introduce a delay after clicking to allow the page to load
                # Locator for the <span> element containing the text
                xpath_conditions = " and ".join([f"contains(@class, '{cls}')" for cls in classes])
                locator = (By.XPATH, f"//div[{xpath_conditions}]/span")
                # Use WebDriverWait in combination with the custom expected condition
                wait = WebDriverWait(driver, 15)  # Adjust the timeout as necessary
                wait.until(TextHasChanged(locator, initial_text))
                content = driver.page_source
                soup = BeautifulSoup(content, 'html.parser')
                div = soup.find('div', class_=div_class)
                initial_text = div.find('span').text if div else "Div or span not found"
            else:
                await asyncio.sleep(3)  # Delay on the first page

            print(f'Page {pagenumber} navigation complete')
            
            # Lists to hold the extracted data
            data_list = []
            # Extract table rows
            rows = soup.find_all("tr")
            # Iterate over the rows and extract required data
            for row in rows[1:]:  # Skipping the header row
                columns = row.find_all("td")
                if len(columns) > 4:  # To ensure we have the required columns
                    report_data = columns[0].text
                    # Extracting rating and price target
                    rating = None
                    price_target = None
                    if "Rating:" in report_data:
                        rating_data = report_data.split("Rating:")[1].split("Price Target:")
                        rating = rating_data[0].strip().split('\n')[0] if len(rating_data) > 0 else None
                        price_target = rating_data[1].strip() if len(rating_data) > 1 else None
                    
                    report_name = report_data.split("Rating:")[0].strip()
                    symbols = columns[1].text.strip()
                    sector = columns[2].text.strip()
                    provider = columns[3].text.strip()
                    date = columns[4].text.strip()
                    data_list.append([report_name, symbols, sector, provider, date, rating, price_target])
            
            print('Data extraction complete')

            # Save to CSV
            # Construct the CSV file path
            path = f"{self.data_path}{self.pkg_path}{self.folder_path}"
            csv_path = f"{path}yahoofinance_{pagenumber}.csv"
            # Write the extracted data to the CSV file
            with open(csv_path, "w", newline="", encoding="GBK") as csvfile:
                writer = csv.writer(csvfile)
                # Write the headers
                writer.writerow(['report_name', 'symbols', 'sector', 'provider', 'date', 'rating', 'price_target'])
                # Write the extracted data
                for row in data_list:
                    writer.writerow(row)

            print(f'Saved as yahoofinance_{pagenumber}.csv complete')

        driver.quit()


        # Merge tables: only merge the latest downloaded tables.
        file_used = [f"yahoofinance_{i}.csv" for i in range(1,total_page+1)]
        
        all_dfs = []
        for file in file_used:
            df = pd.read_csv(path+file)
            df = df.drop(df.index[0])  # Get rid of the first row
            all_dfs.append(df)

        final_df = pd.concat(all_dfs, ignore_index=True)
        #final_df.to_excel(os.path.join(path, "yahoofinance_stock.xlsx"), index=False)
        final_df.to_csv(os.path.join(path, "yahoofinance_stock.csv"), index=False)
        print('Table merge complete')




    def run_async_code(self):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.main())

    
    def run(self):
        process = Process(target=self.run_async_code)
        process.start()
        process.join()

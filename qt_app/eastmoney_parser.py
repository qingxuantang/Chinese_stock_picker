import asyncio
from pyppeteer import launch
import pandas as pd
import os
from bs4 import BeautifulSoup
from multiprocessing import Process
from importlib import reload
from . import utils
utils = reload(utils)


# Creating the class with full functionality
class ReportScraper:

    def __init__(self):
        self.config = utils.config
        self.data_path = self.config['data_path']
        self.pkg_path = 'eastmoney_parser/'
        self.folder_path = 'grpStockReportSummary/'


    def getTotalPages(self, soup):
        """
        Retrieve the total number of pages from the page's HTML content.
        Args:
        - soup (BeautifulSoup): The parsed HTML content.
        Returns:
        - int: The total number of pages.
        """
        # CSS selector for the page numbers
        page_numbers_selector = '.pagerbox a[data-page]'
        # Extract all page numbers
        pages = soup.select(page_numbers_selector)
        # Return the second to last page number as the total number of pages
        if pages:
            return int(pages[-2].get('data-page'))
        else:
            return 0
        
        

    async def main(self,start_page,time_period_key):
        # 启动浏览器
        browser = await launch(headless=True, args=['--no-sandbox'])
        page = await browser.newPage()
        url = self.config['report_url']
        await page.goto(url)
        print('打开网站完成')
        await asyncio.sleep(5)

        # CSS selector for the dropdown menu
        dropdown_selector = '.time-box select.select-time'
        # Make sure dropdown is active
        await page.waitForSelector(dropdown_selector)      
        # Select the desired option based on the provided value
        time_period_value = self.config['time_value'][time_period_key]
        await page.select(dropdown_selector, str(time_period_value)) 
        await asyncio.sleep(5)
        print(f'成功选择研报发布周期: {time_period_key}') #eg. 选择研报发布时间范围: 一月内

        # Retrieve the total number of pages
        content = await page.content()
        soup = BeautifulSoup(content, 'lxml')
        total_page = self.getTotalPages(soup)
        print(f'当前周期总页数: {total_page}')

        pagenumber_range = range(start_page, total_page+1)
        for pagenumber in pagenumber_range:
            print(f'开始翻页，现在是第{pagenumber}页')

            # 定位输入框，清空并输入页码
            await page.type('#gotopageindex', '', {'delay': 50})
            await page.keyboard.press('Backspace')
            await page.keyboard.press('Backspace')
            await page.keyboard.press('Backspace') #Do the backspace 3rd times in case of 3 digits
            await page.type('#gotopageindex', str(pagenumber), {'delay': 50})
            await page.click('input[value="Go"]')

            print(f'翻到第{pagenumber}页完成')
            await asyncio.sleep(5)

            # 获取整个页面HTML
            content = await page.content()
            soup = BeautifulSoup(content, 'lxml')

            # 提取表格内容
            rows = []
            for rowno in range(1, 51):
                row = []
                for cono in range(1, 16):
                    cell_selector = f'#stock_table > table > tbody > tr:nth-child({rowno}) > td:nth-child({cono})'
                    cell_content = soup.select_one(cell_selector)
                    if cell_content is None:
                        print(f"没有找到选择器: {cell_selector}")
                        pass
                    else:
                        cell_content = cell_content.text.strip()
                        if cono == 2:
                            cell_content = cell_content.zfill(6) # 保留字符开头的0
                        row.append(cell_content)
                rows.append(row)

            print('数据读取完成')
            df = pd.DataFrame(rows)
            #print("df: ",df)
            
            # 保存到Excel
            path = self.data_path + self.pkg_path + self.folder_path + f"{pagenumber}.xlsx"
            #print("excel saving path: ",path)
            df.to_excel(path, index=False)
            print(f'保存为{pagenumber}.xlsx完成')

        await browser.close()

        # Merge tables: only merge the latest downloaded tables.
        path = self.data_path + self.pkg_path + self.folder_path
        file_used = [f"{i}.xlsx" for i in range(start_page,total_page+1)]
        
        all_dfs = []
        for file in file_used:
            df = pd.read_excel(path+file)
            df = df.drop(df.index[0])  # 删除第一行
            all_dfs.append(df)

        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_excel(os.path.join(path, "stock.xlsx"), index=False)
        print('所有表格合并完成') 


    
    
        

    def run_async_code(self,start_page,time_period_key):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.main(start_page=start_page,time_period_key=time_period_key))

    
    def run(self,start_page,time_period_key):
        process = Process(target=self.run_async_code, args=(start_page,time_period_key))
        process.start()
        process.join()


    



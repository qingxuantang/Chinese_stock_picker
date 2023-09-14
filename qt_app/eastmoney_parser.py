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


    async def main(self,end_page,start_page):
        # 启动浏览器
        browser = await launch(headless=True, args=['--no-sandbox'])
        page = await browser.newPage()
        url = self.config['report_url']
        await page.goto(url)
        print('打开网站完成')

        pagenumber_range = range(start_page, end_page+1)
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
        file_used = [f"{i}.xlsx" for i in range(start_page,end_page+1)]
        
        all_dfs = []
        for file in file_used:
            df = pd.read_excel(path+file)
            df = df.drop(df.index[0])  # 删除第一行
            all_dfs.append(df)

        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_excel(os.path.join(path, "stock.xlsx"), index=False)
        print('所有表格合并完成') 


    def run_async_code(self,end_page,start_page):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.main(end_page=end_page,start_page=start_page))

    
    def run(self,end_page,start_page):
        process = Process(target=self.run_async_code, args=(end_page,start_page,))
        process.start()
        process.join()


    



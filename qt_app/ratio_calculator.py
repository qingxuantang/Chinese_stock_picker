
import pandas as pd
import time
import yfinance as yf
import re
import os
from datetime import datetime, timedelta
from importlib import reload
from qt_app import utils
utils = reload(utils)

pkg_path = utils.pkg_path
filename = re.findall('(.*).py', os.path.basename(__file__)) #name excluding extension
utils.errorLog(pkg_path=pkg_path,filename=filename)

config = utils.config




class ShortTermSolvencyCalculator:
    '''This class is used to calculate short term solvency ratio for a list of stocks.'''
    def __init__(self, config, file_path):
        self.config = config
        self.file_path = file_path
        # Initialize other properties here
        self.fi_list_yfiance = config['fi_list_yfinance']
        self.data_path = config['data_path']
        self.broker_picked_stock_path = config['broker_picked_stock_path']


    def aShareSymbolIteration(self,file_path,st_column=1):
        stock_df = pd.read_excel(file_path)
        stock_df[st_column] = stock_df[st_column].astype(str)
        stock_df[st_column] = stock_df[st_column].str.zfill(6)
        return stock_df[st_column]


    def fiDataParsing(self, st):
        '''Retreive fundamental data from Yahoo Finance with yfinance package and parse it into a dataframe.'''
        e_yahooFinance = utils.listingSuffixForParsing(exchange=None,symbol=st)[1]
        if e_yahooFinance != '':
            stock = yf.Ticker(st+e_yahooFinance)
            for fi in self.fi_list_yfiance:
                try:
                    # use the getattr function to dynamically access an attribute of an object by its name
                    attribute = getattr(stock, fi)
                    df_name = attribute.reset_index()
                    utils.savingDfToCsv(path_head='tbl',exchange='',path_tail='.csv',df_name=df_name,data_path=self.data_path,mode='w',st=st,path_add=fi.lower(),folder_path='grpFiData/',pkg_path='short_term_solvency_ratio/')
                except Exception as e:
                    utils.exceptionLog(pkg_path=pkg_path,filename=filename,func_name=ShortTermSolvencyCalculator.fiDataParsing.__name__,error=e,loop_item=fi)
                    #time.sleep(10)
                    continue


    def calcShortTermSolvencyRatioYFinance(self, st, report_type='quarterly'): #quarterly or annual
        '''Calculate short term solvency ratio with fi data from Yahoo Finance.'''    
        if report_type == 'quarterly':
            balance_sheet = utils.loadDfFromCsv(path_head='tbl',exchange='',path_tail='.csv',data_path=self.data_path,st=st,path_add='quarterly_balance_sheet',folder_path='grpFiData/',pkg_path='short_term_solvency_ratio/')
            cashflow = utils.loadDfFromCsv(path_head='tbl',exchange='',path_tail='.csv',data_path=self.data_path,st=st,path_add='quarterly_cashflow',folder_path='grpFiData/',pkg_path='short_term_solvency_ratio/')
        elif report_type == 'annual':
            balance_sheet = utils.loadDfFromCsv(path_head='tbl',exchange='',path_tail='.csv',data_path=self.data_path,st=st,path_add='balance_sheet',folder_path='grpFiData/',pkg_path='short_term_solvency_ratio/')
            cashflow = utils.loadDfFromCsv(path_head='tbl',exchange='',path_tail='.csv',data_path=self.data_path,st=st,path_add='cashflow',folder_path='grpFiData/',pkg_path='short_term_solvency_ratio/')
        
        # Retrieve the latest date of the financial statement
        latest_date = balance_sheet.columns[1]
        
        # Retrieve the operating cash flow and investing cash flow from cashflow statement
        operating_cash_flow = cashflow.loc[cashflow['index'] == 'Cash Flowsfromusedin Operating Activities Direct', latest_date].values[0]
        investing_cash_flow = cashflow.loc[cashflow['index'] == 'Investing Cash Flow', latest_date].values[0]
        
        # Retrieve balance sheet items
        short_term_debt_list = ['Current Debt And Capital Lease Obligation'] # This is the combination of current debt and current portion of noncurrent debt.
        if short_term_debt_list[0] in balance_sheet['index'].values: #THIS IS ALL: current debt + current portion of noncurrent debt.
            short_term_debt = balance_sheet.loc[balance_sheet['index'] == short_term_debt_list[0], latest_date].values[0]
        else: #Alternatively, calc current debt by subtracting long term debt from total debt.
            if 'Total Debt' in balance_sheet['index'].values:
                total_debt = balance_sheet.loc[balance_sheet['index'] == 'Total Debt', latest_date].values[0]
                long_term_debt_list = ['Long Term Debt','Long Term Debt And Capital Lease Obligation','Long Term Capital Lease Obligation']
                if long_term_debt_list[0] in balance_sheet['index'].values:
                    long_term_debt = balance_sheet.loc[balance_sheet['index'] == long_term_debt_list[0], latest_date].values[0]
                elif long_term_debt_list[1] in balance_sheet['index'].values:
                    long_term_debt = balance_sheet.loc[balance_sheet['index'] == long_term_debt_list[1], latest_date].values[0]
                elif long_term_debt_list[2] in balance_sheet['index'].values:
                    long_term_debt = balance_sheet.loc[balance_sheet['index'] == long_term_debt_list[2], latest_date].values[0]
                short_term_debt = total_debt - long_term_debt
            else:
                short_term_debt = None
        
        if short_term_debt != None:
            # Calculate total cash flow
            total_cash_flow = operating_cash_flow + investing_cash_flow
            #short_term_debt = current_debt + current_portion_of_noncurrent_debt
            # Calculate short term solvency ratio
            short_term_solvency_ratio = total_cash_flow / (short_term_debt + utils.epsilon)
        else:
            short_term_solvency_ratio = None
        return short_term_solvency_ratio


    def getPriceChangeRatio(self,st,day_count=365):
        # Define the end date as today
        end_date = datetime.today()
        # Define the start date as one year from the end date
        start_date = end_date - timedelta(days=day_count)
        # Format dates
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        # Fetch the historical data
        stock_data = yf.Ticker(st)
        history = stock_data.history(period='1d', start=start_date_str, end=end_date_str)
        # Get the price one year ago and the price today
        price_one_year_ago = history['Close'].iloc[0]
        price_today = history['Close'].iloc[-1]
        # Calculate the price change
        price_change = (price_today - price_one_year_ago) / price_one_year_ago
        return price_change


    def calculate(self,solvency_ratio_margin,price_change_margin_lowerbound,price_change_margin_higherbound, progress_bar=None, progress_display=None):
        st_column = 1

        symbol_picked = self.aShareSymbolIteration(file_path=self.file_path)
        symbol_picked = list(set(symbol_picked)) # Getting rid of duplicates.
        print(utils.printoutHeader())
        print('Total Count of Broker Picked Symbols: ',len(symbol_picked))

        if progress_bar and progress_display:
            progress_bar.progress(0.30)
            progress_display.write(f"备选股票标的有 {len(symbol_picked)} 只。")
            time.sleep(5)
            progress_count = 0
            progress_range = 60
            progress_cumulative = (progress_range/len(symbol_picked))/100

        #Load in the broker picked stock dataframe generated by eastmoney_parser.
        broker_picked_stock_df = pd.read_excel(self.file_path)
        broker_picked_stock_df[st_column] = broker_picked_stock_df[st_column].astype(str)
        broker_picked_stock_df[st_column] = broker_picked_stock_df[st_column].str.zfill(6)
        broker_picked_stock_df['short_term_solvency_ratio'] = float('NaN')
        broker_picked_stock_df['price_change_ratio'] = float('NaN')

        for st in symbol_picked:
            try:
                if progress_bar and progress_display:
                    progress_count += 1
                    progress_bar.progress(0.30 + progress_cumulative*progress_count)
                    progress_display.write(f"正在计算 {st} 的短期偿债因子……")
                self.fiDataParsing(st=st)
                short_term_solvency_ratio = self.calcShortTermSolvencyRatioYFinance(st=st, report_type='quarterly')
                e_yahooFinance = utils.listingSuffixForParsing(exchange=None,symbol=st)[1]
                price_change_ratio = self.getPriceChangeRatio(st=st+e_yahooFinance)
                if short_term_solvency_ratio != None:
                    # Assign the calculated ratio to the new column for the rows where the symbol matches st
                    broker_picked_stock_df.loc[broker_picked_stock_df[st_column] == st, 'short_term_solvency_ratio'] = short_term_solvency_ratio
                if price_change_ratio != None:
                    broker_picked_stock_df.loc[broker_picked_stock_df[st_column] == st, 'price_change_ratio'] = price_change_ratio

            except Exception as e:
                utils.exceptionLog(pkg_path=pkg_path, filename=filename, func_name=ShortTermSolvencyCalculator.calculate.__name__, error=e, loop_item=st)
                continue
        
        sorted_df = broker_picked_stock_df[broker_picked_stock_df['short_term_solvency_ratio'] >= solvency_ratio_margin]
        sorted_df = sorted_df[(sorted_df['price_change_ratio'] >= price_change_margin_lowerbound) & (sorted_df['price_change_ratio'] <= price_change_margin_higherbound)]
        sorted_df = sorted_df.sort_values(by=["short_term_solvency_ratio"], ascending=False)
        utils.savingDfToCsv(path_head='tbl', exchange='', path_tail='.csv', df_name=sorted_df, data_path=self.config['data_path'], mode='w', path_add='StockPickedWithSolvencyR', suffix=utils.timestamp,pkg_path='short_term_solvency_ratio/') # If generating date is different, will save to a new file.

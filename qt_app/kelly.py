
import sys
import re
import os
import numpy as np
import pandas as pd
from cvxopt import matrix
from cvxopt import solvers
from datetime import datetime,timedelta
from cvxopt.solvers import qp
from sklearn.covariance import LedoitWolf
import yfinance as yf
import glob
from importlib import reload
from qt_app import utils
utils = reload(utils)

pkg_path = utils.pkg_path
filename = re.findall('(.*).py', os.path.basename(__file__)) #name excluding extension
utils.errorLog(pkg_path=pkg_path,filename=filename)


class KellyCriterion():

    def __init__(self):
        self.config = utils.config
        self.interval_rf = utils.interval_rf
        self.data_path = self.config['data_path']
        solvers.options['show_progress'] = False
        solvers.options['feastol'] = 1e-8
        solvers.options['abstol'] = 1e-8
        solvers.options['reltol'] = 1e-8
        solvers.options['maxiters'] = 1000
        solvers.options['refinement'] = 3
        solvers.options['kktreg'] = 1e-12
        solvers.options['max_steps'] = 1000
        solvers.options['eps'] = 1e-8
        solvers.options['alpha'] = 1.5
        solvers.options['verbose'] = False
        solvers.options['mumps_mem_percent'] = 10000


    def loadClosePrice(self,max_lookback_years):
        "load prices from web"
        start_date = (datetime.today()
                    - timedelta(days=365*max_lookback_years)).date()
        end_date = datetime.today().date() - timedelta(days=1)

        #import stock symbols from short_term_solvency_ratio's data
        #eg. tblStockPickedWithSolvencyR2023-08-19.csv
        st_column=str(1)
        folder_path = 'short_term_solvency_ratio/'
        #csv_filepath = glob.glob(self.data_path+folder_path+'*.csv')[-1]
        #test
        csv_filepath = glob.glob(self.data_path + folder_path + 'tblStockPickedWithSolvencyR*.csv')
        csv_filepath = sorted(csv_filepath, key=lambda x: datetime.strptime(x.split('tblStockPickedWithSolvencyR')[-1].rstrip('.csv'), '%Y-%m-%d'))
        csv_filepath = csv_filepath[-1]
        
        print("csv_filepath: ",csv_filepath)
        
        csv_filename = os.path.basename(csv_filepath)
        stock_df = utils.loadDfFromCsv(path_head=csv_filename,exchange='',path_tail='',data_path=self.data_path,pkg_path=folder_path)
        stock_df[st_column] = stock_df[st_column].astype(str)
        stock_df[st_column] = stock_df[st_column].str.zfill(6)
        symbol_list = list(set(stock_df[st_column].values.tolist()))

        if len(symbol_list) > 0:
            print('Downloading adjusted daily close data from Yahoo! Finance...')
            stock_picked_price_data = pd.DataFrame()
            for st in symbol_list:
                try:
                    e_yahooFinance = utils.listingSuffixForParsing(exchange=None,symbol=st)[1]
                    symbol = st+e_yahooFinance
                    price_data = yf.download(symbol, start=str(start_date), end=str(end_date),
                                            interval='1d', auto_adjust=True, threads=True)
                    utils.savingDfToCsv(path_head='tbl', exchange='', path_tail='.csv', df_name=price_data, data_path=self.data_path, mode='w', path_add=st+'TI',folder_path='grpTiData/', pkg_path='kelly/')
                    price_data = price_data['Close']
                    price_data.name = symbol
                    price_data = price_data.to_frame()
                    stock_picked_price_data = pd.concat([stock_picked_price_data, price_data], axis=1)
                except Exception as e:
                    utils.exceptionLog(pkg_path=pkg_path,filename=filename,func_name=KellyCriterion.loadClosePrice.__name__,error=e,loop_item=st)
                    continue

            stock_picked_price_data = stock_picked_price_data.sort_index()
            utils.savingDfToCsv(path_head='tbl', exchange='', path_tail='.csv', df_name=stock_picked_price_data, data_path=self.config['data_path'], mode='w', path_add='StockPickedTI', pkg_path='kelly/',index=True)
        return stock_picked_price_data


    def annualExcessReturn(self, price_df):
        '''Stock data only changes on weekdays. Crypto data is available all days.
        Compute daily returns using Monday to Friday returns for all data'''
        #holding_return = price_df[price_df.index.dayofweek < 5].pct_change(1)
        holding_return = price_df.pct_change(1) #.astype(float)
        #print(holding_return)
        excess_return = holding_return - self.interval_rf/252
        return excess_return


    def annualCovar(self, excess_return_daily):
        "annualized covariance of excess returns"
        if self.config['use_Ledoit_Wolf'] == True:
            lw = LedoitWolf().fit(excess_return_daily.dropna()).covariance_
            annual_covar = pd.DataFrame(lw, columns=excess_return_daily.columns) * 252
        else:
            annual_covar = excess_return_daily.cov() * 252
        print(utils.printoutHeader() + 'Condition number of annualized covariance matrix is:', np.linalg.cond(annual_covar))
        try:
            eigvals, __ = np.linalg.eig(annual_covar)
        except:
            print(utils.printoutHeader() + 'Error in Eigen decomposition of covariance matrix.')
            eigvals = []
            sys.exit(-1)
        if min(eigvals) <= 0:
            print(utils.printoutHeader() + 'Error! Negative eigenvalues in covariance matrix detected!')
            sys.exit(-1)
        return annual_covar


    def kellyOptimizeUnconstrained(self, M, C):
        "Calculate unconstrained kelly weights."
        result = np.linalg.inv(C) @ M
        kelly = pd.DataFrame(result.values, index=C.columns, columns=['weight'])
        return kelly


    def kellyOptimize(self, M_df, C_df):
        "Objective function to maximize is: g(F) = r + F^T(M-R) - F^TCF/2"
        r = self.interval_rf
        M = M_df.to_numpy()
        C = C_df.to_numpy()
        eigvals = np.linalg.eigvals(C)
        if np.any(eigvals < 0):
            print("Covariance matrix has negative eigenvalues:", eigvals)

        n = M.shape[0]
        A = matrix(1.0, (1, n))
        b = matrix(1.0)
        G = matrix(0.0, (n, n))
        G[::n+1] = -1.0
        h = matrix(0.0, (n, 1))
        try:
            max_pos_size = float(self.config['max_position_size'])
        except KeyError:
            max_pos_size = None
        try:
            min_pos_size = float(self.config['min_position_size'])
        except KeyError:
            min_pos_size = None
        if min_pos_size is not None:
            h = matrix(min_pos_size, (n, 1))
        if max_pos_size is not None:
            h_max = matrix(max_pos_size, (n,1))
            G_max = matrix(0.0, (n, n))
            G_max[::n+1] = 1.0
            G = matrix(np.vstack((G, G_max)))
            h = matrix(np.vstack((h, h_max)))
        S = matrix((1.0 / ((1 + r) ** 2)) * C)
        q = matrix((1.0 / (1 + r)) * (M - r))
        sol = qp(S, -q, G, h, A, b)
        #sol = coneqp(S, -q, G, h, A, b)
        kelly = np.array([sol['x'][i] for i in range(n)])
        kelly = pd.DataFrame(kelly, index=C_df.columns, columns=['weight'])
        return kelly


    def displayResult(self, df, msg, capital,kelly_fraction):
        "Display asset allocations"
        df['capital_allocation'] = df['weight'] * capital
        if kelly_fraction != 1:
            df = df.drop(columns = ['cal_timestamp'])
            df = df.drop(columns = ['symbol'])
            print(df)
            df = kelly_fraction*df
        df['symbol'] = df.index.str.split('_').str[-1]
        df['cal_timestamp'] = datetime.now()
        print(msg)
        print(df) #.round(2)
        cash = capital - df['capital_allocation'].sum()
        print('cash:', np.round(cash))
        print('*'*100)
        return df,cash


    #def kellyImplied(self, covar):
    #    "Caculate return rates implied from allocation weights: mu = C*F"
    #    F = pd.DataFrame.from_dict(config['position_sizes'], orient='index').transpose()
    #    F = F[covar.columns]
    #    implied_mu = covar @ F.transpose()
    #    implied_mu.columns = ['implied_return_rate']
    #    return implied_mu


    def correlationFromCovariance(self, covariance):
        v = np.sqrt(np.diag(covariance))
        outer_v = np.outer(v, v)
        correlation = covariance / outer_v
        correlation[covariance == 0] = 0
        return correlation
    

    def calculateKC(self,kelly_fraction,max_lookback_years,capital):
        "Load data and begin KC calculation for multivariate portfolio."
        try:
            estimation_mode = self.config['estimation_mode'][0] # hist,fixed,custom
            price_df=self.loadClosePrice(max_lookback_years=max_lookback_years)
            if 'Date' in price_df.columns:
                price_df = price_df.set_index('Date')
            excess_return_daily = self.annualExcessReturn(price_df=price_df)

            if isinstance(excess_return_daily, pd.DataFrame): #Check if excess_return_daily is DataFrame.
                covar = self.annualCovar(excess_return_daily=excess_return_daily)
                mu = pd.DataFrame(columns=covar.columns)
                if estimation_mode == 'hist':
                    mu.loc[0] = excess_return_daily.mean()*252
                elif estimation_mode == 'fixed':
                    rate = self.config['fixed_annual_excess_return_rate']
                    mu.loc[0] = rate
                elif estimation_mode == 'custom':
                    rate = self.config['expected_annual_excess_return_rates']
                    mu = pd.DataFrame.from_dict(rate, orient='index').transpose()
                else:
                    print(utils.printoutHeader() + 'Unexpected estimation mode for annual excess return rates.')
                    sys.exit(-1)
                mu = mu[covar.columns].transpose()
                #if OPTIONS.implied is not None and OPTIONS.implied.upper() == 'TRUE':
                #    implied_returns = kelly_implied(covar, config)
                #    print('*'*100)
                #    print(implied_returns.round(2))
                #    return 0
                
                print(utils.printoutHeader())
                ann_excess_return = mu
                ann_excess_return.columns = ['annualized_excess_return']
                print(ann_excess_return)
                print(utils.printoutHeader())
                print('Estimated Correlation Matrix of Annualized Excess Returns (rounded to 2 decimal places).')
                print(self.correlationFromCovariance(covariance=covar).round(2))
                print(utils.printoutHeader())
                unc_kelly_weight = self.kellyOptimizeUnconstrained(M=mu, C=covar)
                unc_kc_df,_ = self.displayResult(df=unc_kelly_weight, msg='Unconstrained Kelly Weights (no constraints on shorting or leverage)',capital=capital,kelly_fraction=kelly_fraction)
                utils.savingDfToCsv(path_head='tbl', exchange='', path_tail='.csv', df_name=unc_kc_df, data_path=self.data_path, mode='w', path_add='StockPickedKCUnconstrained',folder_path='grpKCResultData/', pkg_path='kelly/',index=True)
                print(utils.printoutHeader() + 'Begin optimization...')
                kelly_weight = self.kellyOptimize(M_df=mu, C_df=covar)
                print(utils.printoutHeader())
                kc_df,_ = self.displayResult(df=kelly_weight, msg='Allocation With Full Kelly Weights',capital=capital,kelly_fraction=kelly_fraction)
                utils.savingDfToCsv(path_head='tbl', exchange='', path_tail='.csv', df_name=kc_df, data_path=self.data_path, mode='w', path_add='StockPickedKC',folder_path='grpKCResultData/', pkg_path='kelly/',index=True)
                kelly_fraction = float(kelly_fraction)
                #partial_kelly = kelly_fraction*kelly_weight
                kc_df,_ = self.displayResult(df=kelly_weight, msg='Allocation With Partial Kelly Fraction:'+str(kelly_fraction),capital=capital,kelly_fraction=kelly_fraction)
            else:
                unc_kc_df = pd.DataFrame(columns=['weight','capital_allocation','symbol','cal_timestamp'])
                kc_df = pd.DataFrame(columns=['weight','capital_allocation','symbol','cal_timestamp'])
        except Exception as e:
            utils.exceptionLog(pkg_path=pkg_path, filename=filename, func_name=KellyCriterion.calculateKC.__name__, error=e, loop_item='Nothing(not a loop)')
            pass
        return unc_kc_df,kc_df

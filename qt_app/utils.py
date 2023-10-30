# -*- coding: UTF-8 -*-

import json
from sqlalchemy import create_engine
import urllib
import pandas as pd
import numpy as np
import math
import re
import os
from datetime import datetime
import http
import time
#from sklearn.preprocessing import MinMaxScaler
import openai
import pandas_datareader as pdr


pkg_path = 'qt_app/'
epsilon = math.exp(-10) #add a small number to avoid zerodivisionerror.
timestamp = datetime.today()
timestamp = timestamp.strftime('%Y-%m-%d')
filename = re.findall('(.*).py', os.path.basename(__file__)) #仅包括扩展名前的部分
#写入stderr模块
def errorLog(pkg_path,filename):
    import sys
    sys.stderr = open('./'+ pkg_path +'_log_/' + filename[0] + '_stderr.txt', 'w')  # redirect stderr to file

errorLog(pkg_path=pkg_path,filename=filename)

# Get the 10-year Treasury yield from FRED
ten_year_yield = pdr.get_data_fred('GS10')
interval_rf = ten_year_yield.iloc[-1].values[0] / 100 #Retreive the latest value.

def loadJSON(json_name):
    import json
    with open('./'+pkg_path+json_name+'.json', encoding='utf-8') as f:
        json_data = json.load(f)
    return json_data

config = loadJSON(json_name='config')

def printoutHeader():
    def returnTimeNow():
        return str(datetime.now())
    return "---------\n" + returnTimeNow() + "\n"

def exceptionLog(pkg_path,filename,func_name,error,loop_item): #230303update
    with open('./'+ pkg_path +'_log_/' + filename[0] + '_exceptions.txt', 'a') as f:
        # write the exception details to the file
        f.write(printoutHeader() + 'Caught exception in ' + func_name + ' during loop of ' + loop_item + ':' + '\n' + str(error) + '\n')
    return print("Caught exception in "+func_name+" during loop of "+loop_item+":", str(error))

def listingSuffixForParsing(exchange,symbol):
    '''Add corresponding suffix to the symbol for parsing via different APIs.'''
    if exchange != None and symbol == None:
        if exchange == 'hkex': #Hong Kong Stock Exchange
            e_alphaVantage = '.HKG'
            e_yahooFinance = '.HK'
        elif exchange == 'sh': #Shanghai Stock Exchange
            e_alphaVantage = '.SHH'
            e_yahooFinance = '.SS'
        elif exchange == 'sz': #Shenzhen Stock Exchange
            e_alphaVantage = '.SHZ'
            e_yahooFinance = '.SZ'
        elif exchange == 'nyse':
            e_alphaVantage = ''
            e_yahooFinance = ''
        elif exchange == 'nasdaq':
            e_alphaVantage = ''
            e_yahooFinance = ''
        elif exchange == '':
            e_alphaVantage = ''
            e_yahooFinance = ''

    if exchange == None and symbol != None:
        if symbol[0] == '0' or symbol[0] == '3':
            e_alphaVantage = '.SHZ'
            e_yahooFinance = '.SZ'
        elif symbol[0] == '6' or symbol[0] == '9':
            e_alphaVantage = '.SHH'
            e_yahooFinance = '.SS'
        elif symbol[0] == '8' or symbol[0] == '4': # Beijing Stock Exchange
            e_alphaVantage = '' # Leave blank for the moment
            e_yahooFinance = ''    

    return e_alphaVantage,e_yahooFinance


def savingDfToCsv(path_head,exchange,path_tail,df_name,data_path,mode='w',st='',interval='',i_n_str='',path_add='',suffix='',folder_path='',pkg_path=pkg_path,index=False):
    with open(data_path + pkg_path + folder_path + path_head + st + exchange + i_n_str + interval + path_add + suffix + path_tail,mode,encoding='GBK') as s:
        df_name.replace('\xa0', ' ', regex=True, inplace=True) #Replace characters that cannot be encoded by GBK.
        df_name.replace("", pd.NA, inplace=True)
        df_name.dropna(how='all', inplace=True) #Drop all nan rows.
        df_name.to_csv(s,index=index,encoding='GBK')


def loadDfFromCsv(path_head,exchange,path_tail,data_path,st='',interval='',i_n_str='',path_add='',suffix='',folder_path='',pkg_path=pkg_path):
    df = pd.read_csv(data_path + pkg_path + folder_path + path_head + st + exchange + i_n_str + interval + path_add + suffix + path_tail, encoding='GBK')
    return df




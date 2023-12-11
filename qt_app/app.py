
def main():
    '''Main function for the app.'''
    import re
    import os
    import time
    import streamlit as st 
    from langchain.llms import OpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferMemory
    from bs4 import BeautifulSoup
    import requests
    import pandas as pd
    from importlib import reload
    from . import utils #relative import
    utils = reload(utils)
    
    openai_apikey  = utils.loadJSON(json_name='openaiapi')['key']
    os.environ['OPENAI_API_KEY'] = openai_apikey
    config = utils.config

    pkg_path = utils.pkg_path
    filename = re.findall('(.*).py', os.path.basename(__file__)) #name excluding extension
    utils.errorLog(pkg_path=pkg_path,filename=filename)
    
    # App framework
    st.title('🦜🔗 A-Shares Stock Picker')
    #query = st.text_input("请输入你想了解的股票名称或股票代码:")


    #Leveraging google search results via streamlit.
    #def googleSearch(query):
    #    '''Return Google search results.'''
    #    from googlesearch import search
    #    results = []
    #    try:
    #        for j in search(query, num=5, start=0, stop=5, pause=2.0):
    #            results.append(j)
    #    except TypeError:
    #        for j in search(query, num_results=5):       
    #            results.append(j)
    #    return results


    #def queryToPrompt():
    #    results = googleSearch(query+'的股票代码')
    #    prompt = []
    #    for result in results:
    #        try:
    #            response = requests.get(result)
    #            soup = BeautifulSoup(response.text, 'html.parser')
    #            title = soup.title.string if soup.title else ""
    #            snippet = soup.find('meta', attrs={'name': 'description'})
    #            snippet = snippet['content'] if snippet else ""
    #            prompt.append(f"Title: {title}\nSnippet: {snippet}")
                #st.write(f"Title: {title}")
                #st.write(f"Snippet: {snippet}")
    #        except requests.exceptions.SSLError:
    #            pass
    #    return prompt
    
    #google_search_result = queryToPrompt()

    # Prompt templates
    #symbol_template = PromptTemplate(
    #    input_variables = ['symbol','google_search_result'], 
    #    template='''根据以下信息，告诉我 {symbol} 的股票代码是什么。 {google_search_result} 
    #                另外请根据以下提示，告诉我 {symbol} 的交易所代号。提示：如果股票代码第一位数为0或者3，则交易所代号为sz；
    #                如果股票代码第一位数为6或者9，则交易所代号为sh。
    #                最终答案请只提供股票名称，股票代码数字和交易所代号，用英文逗号将三者分隔。'''
    #)
    # Memory 
    #symbol_memory = ConversationBufferMemory(input_key='symbol', memory_key='chat_history')
    # LLMs
    #llm = OpenAI(temperature=0.9) 
    #symbol_chain = LLMChain(llm=llm, prompt=symbol_template, verbose=True, memory=symbol_memory) #, output_key='title'
    


    st.write('研报下载参数：')
    start_page = st.number_input('研报下载初始页（默认第1页）:', value=config['start_page'])
    
    market_source_key = st.text_input('股票市场选择（中国/国际）:', value=list(config['stock_market_source'].keys())[0])
    if market_source_key == '中国':
        time_period_key = st.text_input('东方财富网研报周期（一周内/一月内/半年内/一年内/两年内）:', value=list(config['time_value'].keys())[0])
    elif market_source_key == '国际':
        time_period_key = st.text_input('YFinance研报周期（Week/Month/Year）:', value=config['time_value_yfinance'][0])

    st.write('短期偿债因子参数：')
    solvency_ratio_margin = st.number_input('短期偿债因子不低于（越高越好）:', value=config['solvency_ratio_margin'])
    price_change_margin_lowerbound = st.number_input('过去一年历史收益不低于:', value=config['price_change_margin_lowerbound'])
    price_change_margin_higherbound = st.number_input('过去一年历史收益不高于:', value=config['price_change_margin_higherbound'])
    
    st.write('凯利因子参数：')
    kelly_fraction = st.number_input('凯利公式持仓比例（1为100%持仓）:', value=config['kelly_fraction'])
    max_lookback_years = st.number_input('回看历史数据年数（不足一年以小数形式体现）:', value=config['max_lookback_years'])
    capital = st.number_input('总资本:', value=config['capital'])
    
   
    

    
  



    # Button for all actions.
    if st.button('开始寻股'):

        try:
            progress_bar = st.progress(0)
            progress_display = st.empty()
            progress_display.write(f'首先开始下载研报数据……')

            if market_source_key == '中国':
                exchange=''
                from . import eastmoney_parser
                eastmoney_parser = reload(eastmoney_parser)
                scraper = eastmoney_parser.ReportScraper()
                progress_bar.progress(0.03)
                scraper.run(start_page=start_page,time_period_key=time_period_key)

                file_path = config['broker_picked_stock_path']
                st_column = str(1)
            elif market_source_key == '国际':
                exchange='us'
                from . import yfinance_report_parser
                yfinance_report_parser = reload(yfinance_report_parser)
                scraper = yfinance_report_parser.ReportScraper()
                progress_bar.progress(0.03)
                scraper.run()

                file_path = config['yfinance_picked_stock_path']
                st_column = 'symbols'

            time.sleep(10)
            progress_bar.progress(0.15)
            progress_display.write(f'研报下载完成。开始计算短期偿债因子……')

            from . import ratio_calculator
            ratio_calculator = reload(ratio_calculator)
            calculator = ratio_calculator.ShortTermSolvencyCalculator(config, file_path)
            progress_bar.progress(0.20)

            symbol_picked_num = len(calculator.pickSymbol(market_source_key=market_source_key,file_path=file_path))
            st.write(f"备选股票标的有 {symbol_picked_num} 只。")
            
            calculator.calculate(solvency_ratio_margin=solvency_ratio_margin,
                                price_change_margin_lowerbound=price_change_margin_lowerbound,
                                price_change_margin_higherbound=price_change_margin_higherbound,
                                progress_bar=progress_bar,
                                progress_display=progress_display,
                                symbol_picked=calculator.pickSymbol(market_source_key=market_source_key,file_path=file_path),
                                market_source_key=market_source_key,
                                st_column=st_column,
                                exchange=exchange)
                
            progress_bar.progress(0.90)
            progress_display.write(f'短期偿债因子计算完成。开始计算凯利持仓建议……')
            time.sleep(10)
            
            from . import kelly
            kelly = reload(kelly)
            kc = kelly.KellyCriterion()
            kc.calculateKC(kelly_fraction=kelly_fraction,max_lookback_years=max_lookback_years,capital=capital,exchange=exchange)
            progress_bar.progress(1.0)
            progress_display.write(f'凯利公式持仓比例计算完成。')

            data_path = config['data_path']
            kc_file_path = data_path+'kelly/grpKCResultData/tblStockPickedKC.csv'
            df = pd.read_csv(kc_file_path)
            st.dataframe(df)

            df2email = utils.symbolPickedToHtml(df=df)
            print(df2email)
            utils.msgToEmail(part=df2email,market_source_key=market_source_key)
            

        except Exception as e:
            print(e)
            print('程序出错，请重新运行。')




    
    #***************************************************




    
    # Show stuff to the screen if there's a user input query
    #if query:
    #    st.write(google_search_result)
    #    input = {'symbol': query, 'google_search_result': google_search_result}
    #    title = symbol_chain.run(input)
    #    st.write(title)
    #    with st.expander('Symbol History'): 
    #        st.info(symbol_memory.buffer)

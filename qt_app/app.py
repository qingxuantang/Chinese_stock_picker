
def main():
    '''Main function for the app.'''
    import os
    import streamlit as st 
    from langchain.llms import OpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain, SequentialChain 
    from langchain.memory import ConversationBufferMemory
    from bs4 import BeautifulSoup
    import requests
    from importlib import reload
    from . import utils #relative import
    utils = reload(utils)
    
    openai_apikey  = utils.loadJSON(json_name='openaiapi')['key']
    os.environ['OPENAI_API_KEY'] = openai_apikey
    config = utils.config


    # App framework
    st.title('🦜🔗 A-Shares Stock Picker')
    query = st.text_input("请输入你想了解的股票名称或股票代码:")
    

    #Leveraging google search results via streamlit.
    def googleSearch(query):
        '''Return Google search results.'''
        from googlesearch import search
        results = []
        for j in search(query, num=5, start=0, stop=5, pause=2.0):
            results.append(j)
        return results


    def queryToPrompt():
        results = googleSearch(query+'的股票代码')
        prompt = []
        for result in results:
            try:
                response = requests.get(result)
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else ""
                snippet = soup.find('meta', attrs={'name': 'description'})
                snippet = snippet['content'] if snippet else ""
                prompt.append(f"Title: {title}\nSnippet: {snippet}")
                #st.write(f"Title: {title}")
                #st.write(f"Snippet: {snippet}")
            except requests.exceptions.SSLError:
                pass
        return prompt
    
    google_search_result = queryToPrompt()

    # Prompt templates
    symbol_template = PromptTemplate(
        input_variables = ['symbol','google_search_result'], 
        template='''根据以下信息，告诉我 {symbol} 的股票代码是什么。 {google_search_result} 
                    另外请根据以下提示，告诉我 {symbol} 的交易所代号。提示：如果股票代码第一位数为0或者3，则交易所代号为sz；
                    如果股票代码第一位数为6或者9，则交易所代号为sh。
                    最终答案请只提供股票名称，股票代码数字和交易所代号，用英文逗号将三者分隔。'''
    )
    # Memory 
    symbol_memory = ConversationBufferMemory(input_key='symbol', memory_key='chat_history')
    # LLMs
    llm = OpenAI(temperature=0.9) 
    symbol_chain = LLMChain(llm=llm, prompt=symbol_template, verbose=True, memory=symbol_memory) #, output_key='title'





    # Show stuff to the screen if there's a user input query
    if query:
        st.write(google_search_result)
        input = {'symbol': query, 'google_search_result': google_search_result}
        title = symbol_chain.run(input)
        st.write(title)
        with st.expander('Symbol History'): 
            st.info(symbol_memory.buffer)


    st.write('可根据需要修改研报下载参数。')
    end_page = st.number_input('下载研报数据的页数（新报告在最前，每页50条）:', value=config['end_page'])

    # Button for executing the eastmoney_parser
    if st.button('下载最新券商研报'):
        from . import eastmoney_parser
        eastmoney_parser = reload(eastmoney_parser)
        scraper = eastmoney_parser.ReportScraper()
        scraper.run(end_page=end_page)
        st.write('Report data gathering complete.')


    st.write('可根据需要修改偿债因子参数。')
    solvency_ratio_margin = st.number_input('短期偿债因子不低于（越高越好）:', value=config['solvency_ratio_margin'])
    price_change_margin_lowerbound = st.number_input('过去一年历史收益不低于:', value=config['price_change_margin_lowerbound'])
    price_change_margin_higherbound = st.number_input('过去一年历史收益不高于:', value=config['price_change_margin_higherbound'])
    
    # Button for executing the short-term solvency ratio calculation
    if st.button('计算短期偿债因子'):
        from . import ratio_calculator
        ratio_calculator = reload(ratio_calculator)
        file_path = config['broker_picked_stock_path']
        calculator = ratio_calculator.ShortTermSolvencyCalculator(config, file_path)
        calculator.calculate(solvency_ratio_margin=solvency_ratio_margin,
                             price_change_margin_lowerbound=price_change_margin_lowerbound,
                             price_change_margin_higherbound=price_change_margin_higherbound)
        st.write('Short-term Solvency Ratio calculation complete.')


    st.write('可根据需要修改凯利因子参数。')
    kelly_fraction = st.number_input('凯利公式持仓比例（1为100%持仓）:', value=config['kelly_fraction'])
    max_lookback_years = st.number_input('回看历史数据年数（不足一年以小数形式体现）:', value=config['max_lookback_years'])
    capital = st.number_input('总资本:', value=config['capital'])
    
    if st.button('计算凯利持仓因子'):
        from . import kelly
        kelly = reload(kelly)
        kc = kelly.KellyCriterion()
        kc.calculateKC(kelly_fraction=kelly_fraction,max_lookback_years=max_lookback_years,capital=capital)
        st.write('Kelly Criterion optimization complete.')
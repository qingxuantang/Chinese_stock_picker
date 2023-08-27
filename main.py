
from importlib import reload
from qt_app import app,utils
app = reload(app)
utils = reload(utils)

config = utils.config

if __name__ == '__main__' :

    # Run app.py for streamlit app
    app.main()
    
    #from qt_app import eastmoney_parser,ratio_calculator,kelly
    #eastmoney_parser = reload(eastmoney_parser)
    #ratio_calculator = reload(ratio_calculator)
    #kelly = reload(kelly)

    #'''Run eastmoney_parser for broker reports data gathering...'''
    #scraper = eastmoney_parser.ReportScraper()
    #scraper.run()
    #'''Report data gathering complete.'''

    #'''Run ratio_calculator for Short-term Solvency Ratio calculation...'''
    #file_path = config['broker_picked_stock_path']
    #calculator = ratio_calculator.ShortTermSolvencyCalculator(config, file_path)
    #calculator.calculate()
    #'''Short-term Solvency Ratio calculation complete.'''

    #'''Run Kelly Criterion for portfolio optimization...'''
    #kc = kelly.KellyCriterion()
    #kc.calculateKC()
    #'''Kelly Criterion optimization complete.'''
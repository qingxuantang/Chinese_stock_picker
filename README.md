# Chinese Stock Picker

This streamlit-based app is a dynamic and comprehensive tool designed to assist finance professionals in identifying promising Chinese stocks for short-term or long-term trading. Utilizing technologies like Streamlit and data from EastMoney, it provides an intuitive interface and data-driven insights.


![12345](https://github.com/qingxuantang/Chinese_stock_picker/assets/18418339/8178d3cf-4c03-45c4-b4a5-83d553c59c6d)


## Features

<bold>User-Friendly Interface:</bold> Search and explore stocks with ease.

Data-Driven Insights: Analyze stocks using the Kelly Criterion, solvency ratios, and more.

Configurable: Tailor the application to your needs using the config.json file.

Data Scraping: Automated data retrieval from sources like EastMoney.

Open Source: Easily extendable and customizable to fit your specific requirements.

## Quant Functionality

### Markets

Support Chinese(A股) stock picking based on real-time collection of research reports on eastmoney.com.

Support stocks listed in the US and other markets which are visible on Yahoo! Finance research report page(UNDER CONSTRUCTION!).

### Ratio Calculator

The goal of a ratio calculator is to calculate the short-term solvency ratio (or debt ratio), and then use it as a stock-picking filter. That is to say, the better the short-term debt payment capacity a company has, the more probable it may continue or start an upper trend in the short term. The bigger the value, the better.

### Kelly Criterion

Money management strategy based on Kelly J. L.'s formula described in "A New Interpretation of Information Rate". The formula was adopted to gambling and stock market by Ed Thorp, et al., see: "The Kelly Criterion in Blackjack Sports Betting, and the Stock Market".

This program calculates the optimal capital allocation for the provided portfolio of securities with the formula:

    `f_i = m_i / s_i^2`
where

f_i is the calculated leverage of the i-th security from the portfolio
m_i is the mean of the return of the i-th security from the portfolio
s_i is the standard deviation of the return of the i-th security from the portfolio

## Quick Start

Clone the repository.

Configure the application using config.json.

Run <code>streamlit run main.py</code> to launch the Streamlit app.

Explore and analyze Chinese stocks like never before!

## Contribution

Feel free to contribute, report issues, or request features. Let's build a smarter way to pick stocks together!

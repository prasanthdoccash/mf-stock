from flask import Flask, render_template, redirect, url_for, request
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
import os

app = Flask(__name__)

CSV_FILE_PATH = 'scraped_data.csv'

def clean_text(text):
    match = re.search(r'[-+]?[0-9]*\.?[0-9]+%', text)
    if match:
        return match.group(0)
    else:
        match = re.search(r'[-+]?[0-9]*\.?[0-9]+', text)
        return match.group(0) if match else text.strip()

def scrape_data():
    url = "https://trendlyne.com/fundamentals/stock-screener/31264/mutual-funds-increased-shareholding-in-past-month/"
    driver = webdriver.Chrome()
    driver.get(url)

    time.sleep(5)  # Wait for the page to load

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    headers = []
    data = []

    data_table = soup.find('table')
    if data_table:
        header_row = data_table.find('tr')
        headers = [header.text.strip() for header in header_row.find_all('th')]

        # Remove unwanted headers
        unwanted_headers = [
            "MF holding total shares previous month",
            "Latest financial result",
            "Market Capitalization"
        ]
        for header in unwanted_headers:
            if header in headers:
                idx = headers.index(header)
                headers.pop(idx)
                for row in data_table.find_all('tr')[1:]:
                    columns = row.find_all('td')
                    if len(columns) > idx:
                        columns.pop(idx)
                break

        for row in data_table.find_all('tr')[1:]:
            columns = row.find_all('td')
            row_data = [clean_text(column.text.strip()) for column in columns]

            if row_data and row_data[0] not in headers:
                if len(row_data) < len(headers):
                    row_data.extend([''] * (len(headers) - len(row_data)))
                elif len(row_data) > len(headers):
                    row_data = row_data[:len(headers)]

                data.append(row_data)
    else:
        print("No data found")

    df = pd.DataFrame(data, columns=headers)

    df.iloc[:, -2] = df.iloc[:, -2].apply(lambda x: float(x.replace('%', '').strip()) if x else 0)
    df.iloc[:, -1] = df.iloc[:, -1].apply(lambda x: float(x.replace('%', '').strip()) if x else 0)

    df_filtered = df[(df.iloc[:, -2] > 0) & (df.iloc[:, -1] > 0)]

    df_filtered.to_csv(CSV_FILE_PATH, index=False)
    return df_filtered

def load_data():
    if os.path.exists(CSV_FILE_PATH):
        return pd.read_csv(CSV_FILE_PATH)
    else:
        return scrape_data()

@app.route('/', methods=['GET', 'POST'])
def index():
    stock_symbol = request.form.get('stock_symbol', 'INFY')
    df = load_data()

    # Remove unwanted columns before rendering
    unwanted_columns = [
        "MF holding total shares previous month",
        "Latest financial result",
        "Market Capitalization"
    ]
    for column in unwanted_columns:
        if column in df.columns:
            df = df.drop(columns=[column])

    headers = df.columns.tolist()
    data = df.values.tolist()

    return render_template('index1.html', headers=headers, data=data, stock_symbol=stock_symbol)

@app.route('/refresh', methods=['POST'])
def refresh():
    scrape_data()
    return redirect(url_for('index'))

if __name__ == '__main__':
    #app.run(debug=True)
    app.run(debug=True, host='0.0.0.0', port=82)

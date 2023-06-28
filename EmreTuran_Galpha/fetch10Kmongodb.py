from pymongo import MongoClient
from pymongo.errors import OperationFailure
from sec_api import ExtractorApi
import pandas as pd

def insert_data_to_mongodb(url_10k, ticker, date):
    # add your URL below
    url = "#"

    # Create a new client
    client = MongoClient(url, tlsAllowInvalidCertificates=True)
    #client = MongoClient("localhost", 27017)
    # Access the "financial_reports" database
    db = client["10K_Reports"]

    extractorApi = ExtractorApi("#")

    # Retrieve item texts from the API
    item_1_text = extractorApi.get_section(url_10k, "1", "text")
    item_1A_text = extractorApi.get_section(url_10k, "1A", "text")
    item_1B_text = extractorApi.get_section(url_10k, "1B", "text")
    item_2_text = extractorApi.get_section(url_10k, "2", "text")
    item_3_text = extractorApi.get_section(url_10k, "3", "text")
    item_4_text = extractorApi.get_section(url_10k, "4", "text")
    item_5_text = extractorApi.get_section(url_10k, "5", "text")
    item_6_text = extractorApi.get_section(url_10k, "6", "text")
    item_7_text = extractorApi.get_section(url_10k, "7", "text")
    item_7A_text = extractorApi.get_section(url_10k, "7A", "text")
    item_8_text = extractorApi.get_section(url_10k, "8", "text")
    item_9_text = extractorApi.get_section(url_10k, "9", "text")
    item_9A_text = extractorApi.get_section(url_10k, "9A", "text")
    item_9B_text = extractorApi.get_section(url_10k, "9B", "text")
    item_10_text = extractorApi.get_section(url_10k, "10", "text")
    item_11_text = extractorApi.get_section(url_10k, "11", "text")
    item_12_text = extractorApi.get_section(url_10k, "12", "text")
    item_13_text = extractorApi.get_section(url_10k, "13", "text")
    item_14_text = extractorApi.get_section(url_10k, "14", "text")

    # Define the collections and their respective data
    collections_data = {
        "1 - Business": {
            "ticker": ticker,
            "section1A": item_1_text,
            "date": date
        },
        "1A - Risk Factors": {
            "ticker": ticker,
            "section1A": item_1A_text,
            "date": date
        },
        "1B - Unresolved Staff Comments": {
            "ticker": ticker,
            "section1B": item_1B_text,
            "date": date
        },
        "2 - Properties": {
            "ticker": ticker,
            "section2": item_2_text,
            "date": date
        },
        "3 - Legal Proceedings": {
            "ticker": ticker,
            "section3": item_3_text,
            "date": date
        },
        "4 - Mine Safety Disclosures": {
            "ticker": ticker,
            "section4": item_4_text,
            "date": date
        },
        "5 - Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities": {
            "ticker": ticker,
            "section5": item_5_text,
            "date": date
        },
        "6 - Selected Financial Data (prior to February 2021)": {
            "ticker": ticker,
            "section6": item_6_text,
            "date": date
        },
        "7 - Management’s Discussion and Analysis of Financial Condition and Results of Operations": {
            "ticker": ticker,
            "section7": item_7_text,
            "date": date
        },
        "7A - Quantitative and Qualitative Disclosures about Market Risk": {
            "ticker": ticker,
            "section7A": item_7A_text,
            "date": date
        },
        "8 - Financial Statements and Supplementary Data": {
            "ticker": ticker,
            "section8": item_8_text,
            "date": date
        },
        "9 - Changes in and Disagreements with Accountants on Accounting and Financial Disclosure": {
            "ticker": ticker,
            "section9": item_9_text,
            "date": date
        },
        "9A - Controls and Procedures": {
            "ticker": ticker,
            "section9A": item_9A_text,
            "date": date
        },
        "9B - Other Information": {
            "ticker": ticker,
            "section9B": item_9B_text,
            "date": date
        },
        "10 - Directors, Executive Officers and Corporate Governance": {
            "ticker": ticker,
            "section10": item_10_text,
            "date": date
        },
        "11 - Executive Compensation": {
            "ticker": ticker,
            "section11": item_11_text,
            "date": date
        },
        "12 - Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters": {
            "ticker": ticker,
            "section12": item_12_text,
            "date": date
        },
        "13 - Certain Relationships and Related Transactions, and Director Independence": {
            "ticker": ticker,
            "section13": item_13_text,
            "date": date
        },
        "14 - Principal Accountant Fees and Services": {
            "ticker": ticker,
            "section14": item_14_text,
            "date": date
        }
    }

    for collection_name, data in collections_data.items():
        data["ticker_date"] = f"{data['ticker']}_{data['date'].strftime('%Y-%m-%d')}"

        try:
            collection = db[collection_name]
            collection.create_index("ticker_date", unique=True)
            collection.insert_one(data)
            print(f"Unique index created successfully and data inserted for {collection_name}.")
        except OperationFailure as e:
            print(f"Failed to create unique index and insert data for {collection_name}: {str(e)}")

# Example usage
url_10k_aapl = "https://www.sec.gov/ix?doc=/Archives/edgar/data/0001108524/000110852422000008/crm-20210131.htm"
date = pd.to_datetime("2021-01-31")
ticker = 'crm'


insert_data_to_mongodb(url_10k_aapl, ticker, date)

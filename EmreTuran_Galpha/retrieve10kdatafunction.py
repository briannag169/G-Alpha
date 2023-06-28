from pymongo import MongoClient
from datetime import datetime

url = "#"

client = MongoClient(url, tlsAllowInvalidCertificates=True)

db = client["10K_Reports"]

def get_historical_sections(ticker, section, n_records=None, start_date=None, end_date=None):
    collections = {
        "1": db["1 - Business"],
        "1A": db["1A - Risk Factors"],
        "1B": db["1B - Unresolved Staff Comments"],
        "2": db["2 - Properties"],
        "3": db["3 - Legal Proceedings"],
        "4": db["4 - Mine Safety Disclosures"],
        "5": db["5 - Market for Registrant’s Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities"],
        "6": db["6 - Selected Financial Data (prior to February 2021)"],
        "7": db["7 - Management’s Discussion and Analysis of Financial Condition and Results of Operations"],
        "7A": db["7A - Quantitative and Qualitative Disclosures about Market Risk"],
        "8": db["8 - Financial Statements and Supplementary Data"],
        "9": db["9 - Changes in and Disagreements with Accountants on Accounting and Financial Disclosure"],
        "9A": db["9A - Controls and Procedures"],
        "9B": db["9B - Other Information"],
        "10": db["10 - Directors, Executive Officers and Corporate Governance"],
        "11": db["11 - Executive Compensation"],
        "12": db["12 - Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters"],
        "13": db["13 - Certain Relationships and Related Transactions, and Director Independence"],
        "14": db["14 - Principal Accountant Fees and Services"]
    }

    collection = collections.get(section)
    if collection is not None:
        query = {"ticker": ticker}
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}

        projection = {"_id": 0, "ticker": 1, "date": 1, f"section{section}": 1}
        #projection[section] = 1

        cursor = collection.find(query, projection).sort([("date", -1)])
        
        if n_records:
            cursor = cursor.limit(n_records)

        return list(cursor)
    else:
        return []
    


ticker = "msft"
section = "1A"
n_records = 5
start_date = datetime(2015, 1, 1)
end_date = datetime(2023, 12, 31)

result = get_historical_sections(ticker, section, n_records, start_date, end_date)
#result = get_historical_sections("amzn", "1A")

for document in result:
    print(document["date"])
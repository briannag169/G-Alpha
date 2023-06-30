from pymongo import MongoClient
from sec_api import InsiderTradingApi
import pandas as pd
import math
# CHANGED THE FUCNTION TO GET RID OF KEY ERROR non derivative this wrror for tsla/
# price share error for aapl / modified the function again
# STORING DATE AS PD.DATETIME.
# ASML and GOOGL not available

client = MongoClient("localhost", 27017)
database = client["InsiderTrading"]

collection=database["NFLX"]
#ticker="tsla"
# "ticker_date": f"{ticker}_{str(filing['periodOfReport'])}",

# Initialize the InsiderTradingApi
insiderTradingApi = InsiderTradingApi("#")

# Define the function to fetch and store API data
def fetch_and_store_data():
    # Fetch data from the API
    insider_trades = insiderTradingApi.get_data({
        "query": {"query_string": {"query": "issuer.tradingSymbol:NFLX"}},
        "from": "0",
        "size": "100",
        "sort": [{"filedAt": {"order": "desc"}}]
    })
    a=[]
    for i in insider_trades["transactions"]:
        a.append(i)

        # print(" ")

    print(len(a))


    # Flatten the API response
    transactions = flatten_filings(insider_trades["transactions"])

    # Create DataFrame
    df = pd.DataFrame(transactions)

    # Get the column names
    column_names = df.columns.tolist()

    # Insert column names into MongoDB
    #collection.insert_one({'column_names': column_names})

    print("Column names inserted into MongoDB successfully.")

    # Store the API data in MongoDB
    #collection.create_index("ticker_date", unique=True)
    collection.insert_many(transactions)

    print("API data stored in MongoDB successfully.")


def flatten_filing(filing):
    transactions = []

    base_data = {
        "periodOfReport": pd.to_datetime(filing["periodOfReport"]),
        #"ticker_date": f"{ticker}_{str(filing['periodOfReport'])}",

        "issuerCik": filing["issuer"]["cik"],
        "issuerTicker": filing["issuer"]["tradingSymbol"],
        "reportingPerson": filing["reportingOwner"]["name"]
    }

    if "nonDerivativeTable" in filing:
        if "transactions" not in filing["nonDerivativeTable"]:
            return []

        for transaction in filing["nonDerivativeTable"]["transactions"]:
            entry = {
                "securityTitle": transaction["securityTitle"],
                "codingCode": transaction["coding"]["code"],
                "acquiredDisposed": transaction["amounts"]["acquiredDisposedCode"],
                "shares": transaction["amounts"]["shares"],
                "sharePrice": transaction["amounts"].get("pricePerShare", None),  # Use get method with default value
                "total": math.ceil(
                    transaction["amounts"]["shares"] * transaction["amounts"].get("pricePerShare", 0)
                ),  # Use get method with default value
                "sharesOwnedFollowingTransaction": transaction["postTransactionAmounts"][
                    "sharesOwnedFollowingTransaction"
                ],
            }

            transactions.append({**base_data, **entry})
    else:
        return []

    return transactions




# create a simplified list of all transactions per filing 
# with just a handful of data points, e.g. reporting person, shares sold, etc.
def flatten_filings(filings):
  unflattened_list = list(map(flatten_filing, filings))
  return [item for sublist in unflattened_list for item in sublist]

# Call the fetch_and_store_data function to fetch and store the API data
fetch_and_store_data()

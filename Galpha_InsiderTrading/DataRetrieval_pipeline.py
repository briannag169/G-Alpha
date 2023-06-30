

import pandas as pd
from pymongo import MongoClient
from datetime import datetime

def retrieve_transactions(ticker, person_name=None, start_date=None, end_date=None, num_transactions=None):
    # Connect to the MongoDB database
    client = MongoClient("localhost", 27017)
    database = client["InsiderTrading"]
    collection = database[ticker]

    # Build the MongoDB aggregation pipeline based on the provided choices
    pipeline = []

    if person_name:
        pipeline.append({
            "$match": {
                "reportingPerson": person_name
            }
        })

    if start_date and end_date:
        pipeline.append({
            "$match": {
                "periodOfReport": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        })

    pipeline.extend([
        {
            "$sort": {
                "periodOfReport": -1
            }
        }
    ])

    if num_transactions:
        pipeline.append({
            "$limit": num_transactions
        })

    pipeline.append({
        "$group": {
            "_id": "$reportingPerson",
            "transactions": {
                "$push": {
                    "transaction_amount": "$total",
                    "date": "$periodOfReport"
                }
            }
        }
    })

    # Query the database to retrieve the desired data
    transactions = collection.aggregate(pipeline)

    # Convert the aggregation result to a Pandas DataFrame
    df = pd.DataFrame(transactions)

    return df

# Example usage with start_date = datetime(2015, 1, 1) and end_date = datetime(2023, 12, 31)
start_date = datetime(2022, 1, 1)
end_date = datetime(2023, 5, 28)
transactions_df = retrieve_transactions("TSLA", person_name="Musk Elon", start_date=start_date, end_date=end_date)

# transactions_df = retrieve_transactions("DIS")

print(transactions_df)

# print(transactions_df["transactions"][0])
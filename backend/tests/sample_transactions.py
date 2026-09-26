import pandas as pd


def get_sample_dataframe():
    data = [
        {
            "transaction_id": "TX001",
            "sender_account": "A001",
            "receiver_account": "A002",
            "customer_id": "C001",
            "device_id": "D001",
            "ip_address": "10.0.0.1",
            "wallet_id": "W001",
            "amount": 500,
            "currency": "USD",
            "timestamp": "2026-09-01T10:00:00",
            "channel": "Mobile",
            "location_country": "India",
            "location_city": "Hyderabad",
            "is_crypto": False
        },
        {
            "transaction_id": "TX002",
            "sender_account": "A002",
            "receiver_account": "A003",
            "customer_id": "C002",
            "device_id": "D002",
            "ip_address": "10.0.0.2",
            "wallet_id": "W002",
            "amount": 800,
            "currency": "USD",
            "timestamp": "2026-09-01T10:30:00",
            "channel": "Web",
            "location_country": "India",
            "location_city": "Bangalore",
            "is_crypto": False
        },
        {
            "transaction_id": "TX003",
            "sender_account": "A003",
            "receiver_account": "A001",
            "customer_id": "C003",
            "device_id": "D003",
            "ip_address": "10.0.0.3",
            "wallet_id": "W003",
            "amount": 1200,
            "currency": "USD",
            "timestamp": "2026-09-01T11:00:00",
            "channel": "ATM",
            "location_country": "India",
            "location_city": "Chennai",
            "is_crypto": False
        },
        {
            "transaction_id": "TX004",
            "sender_account": "A001",
            "receiver_account": "A002",
            "customer_id": "C001",
            "device_id": "D001",
            "ip_address": "10.0.0.1",
            "wallet_id": "W001",
            "amount": 1500,
            "currency": "USD",
            "timestamp": "2026-09-01T12:00:00",
            "channel": "Mobile",
            "location_country": "India",
            "location_city": "Hyderabad",
            "is_crypto": False
        }
    ]

    return pd.DataFrame(data)
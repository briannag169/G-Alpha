from __future__ import annotations

from pymongo import MongoClient
from pymongo.database import Database

from galpha.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            settings.mongodb_uri,
            tlsAllowInvalidCertificates=settings.tls_allow_invalid_certs,
        )
    return _client


def get_database(db_name: str) -> Database:
    return get_client()[db_name]


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

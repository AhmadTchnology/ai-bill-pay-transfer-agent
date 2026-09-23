"""Materializes data_gen/wallet_schema.json — the schema the mock wallet data
was generated from (see prompts.md). Run: py data_gen/_make_schema.py"""

import json
from pathlib import Path

schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Mock Iraqi Wallet",
    "description": "Schema for LLM-generated mock wallet data (no real money).",
    "type": "object",
    "required": ["users", "contacts", "billers", "user_billers", "transactions"],
    "additionalProperties": False,
    "properties": {
        "_meta": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "currency": {"const": "IQD"},
            },
        },
        "users": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "phone", "balance_iqd"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string", "pattern": "^07\\d{9}$"},
                    "balance_iqd": {"type": "integer", "minimum": 0},
                },
            },
        },
        "contacts": {
            "type": "array",
            "minItems": 5,
            "description": "MUST include duplicate/similar names (e.g. أحمد, أحمد علي, أحمد حسين) to exercise disambiguation.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "user_id", "name", "phone", "bank"],
                "properties": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string", "pattern": "^07\\d{9}$"},
                    "bank": {
                        "type": "string",
                        "enum": ["زين كاش", "آسيا حوالة", "فاست باي"],
                    },
                },
            },
        },
        "billers": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name_ar", "name_en", "category"],
                "properties": {
                    "id": {"type": "string"},
                    "name_ar": {"type": "string"},
                    "name_en": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["كهرباء", "ماء", "انترنت", "موبايل", "غاز"],
                    },
                },
            },
        },
        "user_billers": {
            "type": "array",
            "description": "Linked billers per user; leave at least one biller unlinked to test honest failures.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["user_id", "biller_id", "account_number"],
                "properties": {
                    "user_id": {"type": "string"},
                    "biller_id": {"type": "string"},
                    "account_number": {"type": "string"},
                    "last_amount_iqd": {"type": "integer"},
                },
            },
        },
        "transactions": {
            "type": "array",
            "description": "Two weeks of mixed transfer/bill_payment history.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "user_id",
                    "type",
                    "counterparty",
                    "amount_iqd",
                    "status",
                    "created_at",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string"},
                    "type": {"enum": ["transfer", "bill_payment"]},
                    "counterparty": {"type": "string"},
                    "amount_iqd": {"type": "integer", "exclusiveMinimum": 0},
                    "status": {"enum": ["completed", "failed"]},
                    "note": {"type": ["string", "null"]},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
        },
    },
}

out = Path(__file__).parent / "wallet_schema.json"
out.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"written: {out}")

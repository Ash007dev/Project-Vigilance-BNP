import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, or_, select

from app.db.database import SessionLocal
from app.db.models import Transaction


router = APIRouter(prefix="/copilot", tags=["AI Copilot"])
ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class CopilotSettings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-terra"

    model_config = SettingsConfigDict(extra="ignore")


def _load_settings(env_file: Path = ROOT_ENV) -> CopilotSettings:
    return CopilotSettings(_env_file=env_file, _env_file_encoding="utf-8")


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


FILTER_PROPERTIES = {
    "account": {"type": "string"},
    "transaction_id": {"type": "string"},
    "min_amount": {"type": "number"},
    "max_amount": {"type": "number"},
    "currency": {"type": "string"},
    "channel": {"type": "string"},
    "country": {"type": "string"},
    "device_id": {"type": "string"},
    "ip_address": {"type": "string"},
    "crypto": {"type": "string", "enum": ["any", "yes", "no"]},
    "start_time": {"type": "string"},
    "end_time": {"type": "string"},
}

TOOLS = [
    {
        "type": "function",
        "name": "search_transactions",
        "description": "Find transaction-level evidence using safe filters.",
        "parameters": {
            "type": "object",
            "properties": {
                **FILTER_PROPERTIES,
                "sort_by": {
                    "type": "string",
                    "enum": ["timestamp", "amount"],
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "aggregate_transactions",
        "description": "Calculate totals, counts, averages, maxima, and rankings.",
        "parameters": {
            "type": "object",
            "properties": {
                **FILTER_PROPERTIES,
                "group_by": {
                    "type": "string",
                    "enum": [
                        "none",
                        "currency",
                        "channel",
                        "country",
                        "sender_account",
                        "receiver_account",
                        "device_id",
                        "ip_address",
                        "crypto_flag",
                    ],
                },
                "metric": {
                    "type": "string",
                    "enum": [
                        "transaction_count",
                        "total_amount",
                        "average_amount",
                        "maximum_amount",
                    ],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 25},
            },
            "additionalProperties": False,
        },
    },
]

INSTRUCTIONS = """
You are an AML Investigation Copilot. Query the dataset with the supplied
tools before answering. Use only tool evidence, cite transaction IDs for
specific claims, do not invent facts, and do not make final legal or
compliance decisions. Keep answers concise and mention missing evidence.
"""


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _build_filters(arguments: dict[str, Any]) -> list[Any]:
    filters = []

    if account := arguments.get("account"):
        filters.append(
            or_(
                Transaction.sender_account == account,
                Transaction.receiver_account == account,
            )
        )

    if transaction_id := arguments.get("transaction_id"):
        filters.append(Transaction.transaction_id == transaction_id)

    if arguments.get("min_amount") is not None:
        filters.append(Transaction.amount >= float(arguments["min_amount"]))

    if arguments.get("max_amount") is not None:
        filters.append(Transaction.amount <= float(arguments["max_amount"]))

    text_fields = {
        "currency": Transaction.currency,
        "channel": Transaction.channel,
        "country": Transaction.country,
        "device_id": Transaction.device_id,
        "ip_address": Transaction.ip_address,
    }
    for name, column in text_fields.items():
        if value := arguments.get(name):
            filters.append(func.lower(column) == value.lower())

    crypto = arguments.get("crypto", "any")
    if crypto == "yes":
        filters.append(Transaction.crypto_flag == 1)
    elif crypto == "no":
        filters.append(
            or_(
                Transaction.crypto_flag == 0,
                Transaction.crypto_flag.is_(None),
            )
        )

    if start_time := _parse_datetime(arguments.get("start_time")):
        filters.append(Transaction.timestamp >= start_time)

    if end_time := _parse_datetime(arguments.get("end_time")):
        filters.append(Transaction.timestamp <= end_time)

    return filters


def _serialize_transaction(tx: Transaction) -> dict[str, Any]:
    return {
        "transaction_id": tx.transaction_id,
        "timestamp": tx.timestamp.isoformat(),
        "sender_account": tx.sender_account,
        "receiver_account": tx.receiver_account,
        "amount": tx.amount,
        "currency": tx.currency,
        "channel": tx.channel,
        "country": tx.country,
        "city": tx.city,
        "device_id": tx.device_id,
        "ip_address": tx.ip_address,
        "crypto_flag": tx.crypto_flag,
        "crypto_wallet": tx.crypto_wallet,
    }


def _search_transactions(arguments: dict[str, Any]) -> dict[str, Any]:
    sort_column = {
        "timestamp": Transaction.timestamp,
        "amount": Transaction.amount,
    }.get(arguments.get("sort_by"), Transaction.timestamp)
    order_expression = (
        sort_column.asc()
        if arguments.get("sort_order") == "asc"
        else sort_column.desc()
    )
    limit = max(1, min(int(arguments.get("limit", 25)), 100))
    statement = (
        select(Transaction)
        .where(*_build_filters(arguments))
        .order_by(order_expression)
        .limit(limit)
    )

    with SessionLocal() as session:
        rows = session.execute(statement).scalars().all()

    transactions = []
    seen_ids = set()
    for tx in rows:
        if tx.transaction_id in seen_ids:
            continue
        seen_ids.add(tx.transaction_id)
        transactions.append(_serialize_transaction(tx))

    return {
        "returned_count": len(transactions),
        "transactions": transactions,
    }


def _aggregate_transactions(arguments: dict[str, Any]) -> dict[str, Any]:
    metric = arguments.get("metric", "transaction_count")
    group_by = arguments.get("group_by", "none")
    limit = max(1, min(int(arguments.get("limit", 10)), 25))

    metric_expression = {
        "transaction_count": func.count(
            func.distinct(Transaction.transaction_id)
        ),
        "total_amount": func.sum(Transaction.amount),
        "average_amount": func.avg(Transaction.amount),
        "maximum_amount": func.max(Transaction.amount),
    }[metric]
    group_columns = {
        "currency": Transaction.currency,
        "channel": Transaction.channel,
        "country": Transaction.country,
        "sender_account": Transaction.sender_account,
        "receiver_account": Transaction.receiver_account,
        "device_id": Transaction.device_id,
        "ip_address": Transaction.ip_address,
        "crypto_flag": Transaction.crypto_flag,
    }

    with SessionLocal() as session:
        if group_by == "none":
            value = session.execute(
                select(metric_expression.label("value")).where(
                    *_build_filters(arguments)
                )
            ).scalar_one()
            return {"metric": metric, "value": value or 0}

        group_column = group_columns[group_by]
        statement = (
            select(
                group_column.label("group"),
                metric_expression.label("value"),
            )
            .where(*_build_filters(arguments))
            .group_by(group_column)
            .order_by(metric_expression.desc())
            .limit(limit)
        )
        rows = session.execute(statement).all()

    return {
        "metric": metric,
        "group_by": group_by,
        "results": [
            {
                "group": row._mapping["group"],
                "value": row._mapping["value"] or 0,
            }
            for row in rows
        ],
    }


def _execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "search_transactions":
        return _search_transactions(arguments)
    if name == "aggregate_transactions":
        return _aggregate_transactions(arguments)
    raise ValueError(f"Unsupported tool: {name}")


def _create_client():
    from openai import OpenAI

    return OpenAI(api_key=_load_settings().openai_api_key, timeout=60)


def run_copilot(question: str) -> dict:
    client = _create_client()
    model = _load_settings().openai_model
    next_input: Any = question
    previous_response_id = None
    tools_used = []

    for turn in range(4):
        request = {
            "model": model,
            "instructions": INSTRUCTIONS,
            "input": next_input,
            "tools": TOOLS,
            "tool_choice": "required" if turn == 0 else "auto",
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = client.responses.create(**request)
        calls = [item for item in response.output if item.type == "function_call"]

        if not calls:
            answer = response.output_text.strip()
            if not answer:
                raise RuntimeError("OpenAI returned an empty answer.")
            return {
                "model": model,
                "answer": answer,
                "tools_used": tools_used,
            }

        next_input = []
        for call in calls:
            arguments = json.loads(call.arguments)
            result = _execute_tool(call.name, arguments)
            tools_used.append(call.name)
            next_input.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, default=str),
                }
            )
        previous_response_id = response.id

    raise RuntimeError("Copilot exceeded its tool-call limit.")


@router.post("/query")
def query_copilot(payload: CopilotRequest):
    if not _load_settings().openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured.",
        )

    try:
        result = run_copilot(payload.question)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Copilot request failed.",
        ) from exc

    return {
        "status": "success",
        "question": payload.question,
        **result,
    }

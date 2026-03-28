"""Set CloudWatch log retention to 7 days on all /aws/* dev log groups.

Phase 1 quick win — no downtime. Eliminates CloudWatch log storage costs
from log groups that accumulate indefinitely by default.
"""
from __future__ import annotations

import logging
from typing import Any

import boto3

LOG_GROUP_PREFIX = "/aws/"
DEFAULT_RETENTION_DAYS = 7

logger = logging.getLogger(__name__)


def get_aws_log_groups(client: Any) -> list[dict]:
    """Return all CloudWatch log groups whose name starts with /aws/."""
    groups: list[dict] = []
    paginator = client.get_paginator("describe_log_groups")
    for page in paginator.paginate(logGroupNamePrefix=LOG_GROUP_PREFIX):
        groups.extend(page.get("logGroups", []))
    return groups


def set_retention_policy(client: Any, log_group_name: str, retention_days: int) -> None:
    """Put a retention policy on a single log group."""
    client.put_retention_policy(
        logGroupName=log_group_name,
        retentionInDays=retention_days,
    )


def apply_retention_to_all_aws_groups(
    client: Any,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> dict:
    """Apply retention_days policy to every /aws/* log group.

    Returns a summary dict: {"updated": int, "failed": int, "errors": list}.
    """
    groups = get_aws_log_groups(client)
    updated = 0
    failed = 0
    errors: list[str] = []

    for group in groups:
        name = group["logGroupName"]
        try:
            set_retention_policy(client, name, retention_days)
            updated += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{name}: {exc}")
            logger.error("Failed to set retention on %s: %s", name, exc)

    return {"updated": updated, "failed": failed, "errors": errors}


def main() -> None:
    """Entrypoint: apply 7-day retention across all /aws/* log groups."""
    client = boto3.client("logs")
    result = apply_retention_to_all_aws_groups(client, DEFAULT_RETENTION_DAYS)
    print(
        f"CloudWatch retention: updated={result['updated']} failed={result['failed']}"
    )
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

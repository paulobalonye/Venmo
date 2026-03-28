"""Apply S3 lifecycle rules to all dev-tagged buckets.

Phase 1 quick win — no downtime.
Rules applied:
  - Expire non-current object versions after 30 days
  - Abort incomplete multipart uploads after 7 days
"""
from __future__ import annotations

import logging
from typing import Any

import boto3

DEV_TAG_KEY = "Environment"
DEV_TAG_VALUE = "dev"
NONCURRENT_EXPIRY_DAYS = 30
MULTIPART_ABORT_DAYS = 7

logger = logging.getLogger(__name__)


def get_dev_buckets(client: Any) -> list[str]:
    """Return names of all S3 buckets tagged Environment=dev."""
    response = client.list_buckets()
    dev_buckets: list[str] = []

    for bucket in response.get("Buckets", []):
        name = bucket["Name"]
        try:
            tags_resp = client.get_bucket_tagging(Bucket=name)
            tags = {t["Key"]: t["Value"] for t in tags_resp.get("TagSet", [])}
            if tags.get(DEV_TAG_KEY) == DEV_TAG_VALUE:
                dev_buckets.append(name)
        except client.exceptions.from_code("NoSuchTagSet"):
            pass
        except Exception:
            # Bucket has no tagging or access denied — skip
            pass

    return dev_buckets


def build_lifecycle_configuration() -> dict:
    """Return the S3 lifecycle configuration dict.

    Two rules:
      1. expire-noncurrent-versions: NoncurrentVersionExpiration after 30 days
      2. abort-incomplete-multipart: AbortIncompleteMultipartUpload after 7 days
    """
    return {
        "Rules": [
            {
                "ID": "expire-noncurrent-versions",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "NoncurrentVersionExpiration": {
                    "NoncurrentDays": NONCURRENT_EXPIRY_DAYS,
                },
            },
            {
                "ID": "abort-incomplete-multipart",
                "Status": "Enabled",
                "Filter": {"Prefix": ""},
                "AbortIncompleteMultipartUpload": {
                    "DaysAfterInitiation": MULTIPART_ABORT_DAYS,
                },
            },
        ]
    }


def apply_lifecycle_rules(client: Any, bucket_name: str, config: dict) -> None:
    """Put the lifecycle configuration onto a single bucket (idempotent)."""
    client.put_bucket_lifecycle_configuration(
        Bucket=bucket_name,
        LifecycleConfiguration=config,
    )


def apply_lifecycle_to_all_dev_buckets(client: Any) -> dict:
    """Apply lifecycle rules to all dev S3 buckets.

    Returns {"updated": int, "failed": int, "errors": list}.
    """
    buckets = get_dev_buckets(client)
    config = build_lifecycle_configuration()
    updated = 0
    failed = 0
    errors: list[str] = []

    for bucket in buckets:
        try:
            apply_lifecycle_rules(client, bucket, config)
            updated += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{bucket}: {exc}")
            logger.error("Failed to apply lifecycle to %s: %s", bucket, exc)

    return {"updated": updated, "failed": failed, "errors": errors}


def main() -> None:
    """Entrypoint: apply lifecycle rules to all dev-tagged S3 buckets."""
    client = boto3.client("s3")
    result = apply_lifecycle_to_all_dev_buckets(client)
    print(f"S3 lifecycle: updated={result['updated']} failed={result['failed']}")
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

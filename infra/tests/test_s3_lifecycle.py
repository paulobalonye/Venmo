"""Tests for S3 lifecycle rule management.

TDD: Tests written BEFORE implementation.
The implementation must:
- Add lifecycle rules to all dev S3 buckets
- Expire non-current versions after 30 days
- Delete incomplete multipart uploads after 7 days
"""
import boto3
import pytest
from moto import mock_aws

from infra.scripts.s3_lifecycle import (
    get_dev_buckets,
    apply_lifecycle_rules,
    build_lifecycle_configuration,
)

AWS_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_env(aws_credentials):
    pass


@mock_aws
def test_get_dev_buckets_returns_tagged_buckets(aws_credentials):
    """Only buckets tagged Environment=dev are returned."""
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="dev-assets")
    client.put_bucket_tagging(
        Bucket="dev-assets",
        Tagging={"TagSet": [{"Key": "Environment", "Value": "dev"}]},
    )
    client.create_bucket(Bucket="prod-assets")
    client.put_bucket_tagging(
        Bucket="prod-assets",
        Tagging={"TagSet": [{"Key": "Environment", "Value": "prod"}]},
    )

    buckets = get_dev_buckets(client)

    assert "dev-assets" in buckets
    assert "prod-assets" not in buckets


@mock_aws
def test_get_dev_buckets_returns_empty_when_none(aws_credentials):
    """Returns empty list when no dev-tagged buckets exist."""
    client = boto3.client("s3", region_name=AWS_REGION)
    buckets = get_dev_buckets(client)
    assert buckets == []


def test_build_lifecycle_configuration_has_noncurrent_expiry():
    """Lifecycle config expires non-current versions after 30 days."""
    config = build_lifecycle_configuration()

    rules = config["Rules"]
    noncurrent_rules = [
        r for r in rules
        if "NoncurrentVersionExpiration" in r
    ]
    assert len(noncurrent_rules) >= 1
    rule = noncurrent_rules[0]
    assert rule["NoncurrentVersionExpiration"]["NoncurrentDays"] == 30
    assert rule["Status"] == "Enabled"


def test_build_lifecycle_configuration_has_multipart_abort():
    """Lifecycle config aborts incomplete multipart uploads after 7 days."""
    config = build_lifecycle_configuration()

    rules = config["Rules"]
    multipart_rules = [
        r for r in rules
        if "AbortIncompleteMultipartUpload" in r
    ]
    assert len(multipart_rules) >= 1
    rule = multipart_rules[0]
    assert rule["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 7
    assert rule["Status"] == "Enabled"


@mock_aws
def test_apply_lifecycle_rules_sets_rules_on_bucket(aws_credentials):
    """apply_lifecycle_rules puts the lifecycle config on the given bucket."""
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="test-dev-bucket")

    config = build_lifecycle_configuration()
    apply_lifecycle_rules(client, "test-dev-bucket", config)

    response = client.get_bucket_lifecycle_configuration(Bucket="test-dev-bucket")
    rules = response["Rules"]
    assert len(rules) >= 2

    ids = [r["ID"] for r in rules]
    assert any("noncurrent" in i.lower() or "version" in i.lower() for i in ids)
    assert any("multipart" in i.lower() or "abort" in i.lower() for i in ids)


@mock_aws
def test_apply_lifecycle_rules_is_idempotent(aws_credentials):
    """Calling apply_lifecycle_rules twice does not raise and keeps rules intact."""
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="idempotent-bucket")
    config = build_lifecycle_configuration()

    apply_lifecycle_rules(client, "idempotent-bucket", config)
    apply_lifecycle_rules(client, "idempotent-bucket", config)

    response = client.get_bucket_lifecycle_configuration(Bucket="idempotent-bucket")
    assert len(response["Rules"]) >= 2

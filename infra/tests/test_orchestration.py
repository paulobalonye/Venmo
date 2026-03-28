"""Tests for orchestration/main paths and error-handling branches.

Covers the bulk-apply helpers and main() entrypoints that boost coverage
to meet the 80% threshold.
"""
from __future__ import annotations

import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock

from infra.scripts.cloudwatch_retention import apply_retention_to_all_aws_groups
from infra.scripts.s3_lifecycle import apply_lifecycle_to_all_dev_buckets, get_dev_buckets
from infra.scripts.vpc_endpoints import apply_vpc_endpoints

AWS_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_env(aws_credentials):
    pass


# ── CloudWatch retention bulk orchestration ──────────────────────────────────

@mock_aws
def test_apply_retention_returns_zero_when_no_groups(aws_credentials):
    """Returns updated=0 when no /aws/* groups exist."""
    client = boto3.client("logs", region_name=AWS_REGION)
    result = apply_retention_to_all_aws_groups(client, 7)
    assert result == {"updated": 0, "failed": 0, "errors": []}


@mock_aws
def test_apply_retention_records_failed_on_api_error(aws_credentials):
    """When put_retention_policy raises, failed count increments."""
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/aws/lambda/boom")

    with patch.object(client, "put_retention_policy", side_effect=Exception("boom")):
        result = apply_retention_to_all_aws_groups(client, 7)

    assert result["failed"] == 1
    assert result["updated"] == 0
    assert len(result["errors"]) == 1


@mock_aws
def test_cloudwatch_main_runs_without_error(aws_credentials, capsys):
    """main() prints a summary line and exits cleanly."""
    from infra.scripts.cloudwatch_retention import main
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/aws/lambda/fn")

    with patch("infra.scripts.cloudwatch_retention.boto3") as mock_boto:
        mock_boto.client.return_value = client
        main()

    captured = capsys.readouterr()
    assert "CloudWatch retention" in captured.out


# ── S3 lifecycle bulk orchestration ──────────────────────────────────────────

@mock_aws
def test_apply_lifecycle_to_all_dev_buckets_updates_tagged(aws_credentials):
    """Lifecycle rules applied to all dev-tagged buckets."""
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="dev-b1")
    client.put_bucket_tagging(
        Bucket="dev-b1",
        Tagging={"TagSet": [{"Key": "Environment", "Value": "dev"}]},
    )

    result = apply_lifecycle_to_all_dev_buckets(client)

    assert result["updated"] == 1
    assert result["failed"] == 0


@mock_aws
def test_apply_lifecycle_to_all_dev_buckets_returns_zero_when_none(aws_credentials):
    """Returns updated=0 when no dev buckets exist."""
    client = boto3.client("s3", region_name=AWS_REGION)
    result = apply_lifecycle_to_all_dev_buckets(client)
    assert result == {"updated": 0, "failed": 0, "errors": []}


@mock_aws
def test_apply_lifecycle_records_failure_on_error(aws_credentials):
    """failed count increments when put_bucket_lifecycle_configuration raises."""
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="dev-err")
    client.put_bucket_tagging(
        Bucket="dev-err",
        Tagging={"TagSet": [{"Key": "Environment", "Value": "dev"}]},
    )

    with patch.object(
        client, "put_bucket_lifecycle_configuration", side_effect=Exception("fail")
    ):
        result = apply_lifecycle_to_all_dev_buckets(client)

    assert result["failed"] == 1
    assert result["updated"] == 0


@mock_aws
def test_s3_main_runs_without_error(aws_credentials, capsys):
    """s3_lifecycle main() prints a summary and exits cleanly."""
    from infra.scripts.s3_lifecycle import main
    client = boto3.client("s3", region_name=AWS_REGION)
    client.create_bucket(Bucket="dev-bucket")
    client.put_bucket_tagging(
        Bucket="dev-bucket",
        Tagging={"TagSet": [{"Key": "Environment", "Value": "dev"}]},
    )

    with patch("infra.scripts.s3_lifecycle.boto3") as mock_boto:
        mock_boto.client.return_value = client
        main()

    captured = capsys.readouterr()
    assert "S3 lifecycle" in captured.out


# ── VPC endpoints bulk orchestration ─────────────────────────────────────────

@mock_aws
def test_apply_vpc_endpoints_records_failure_on_error(aws_credentials):
    """failed count increments when create_vpc_endpoint raises."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    client.create_tags(
        Resources=[vpc_id],
        Tags=[{"Key": "Environment", "Value": "dev"}],
    )

    with patch.object(
        client, "create_vpc_endpoint", side_effect=Exception("endpoint fail")
    ):
        result = apply_vpc_endpoints(client, AWS_REGION)

    assert result["failed"] == 2
    assert result["created"] == 0
    assert "error" in result


@mock_aws
def test_vpc_endpoints_main_runs_without_error(aws_credentials, capsys):
    """vpc_endpoints main() prints a summary and exits cleanly."""
    from infra.scripts.vpc_endpoints import main
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    client.create_tags(
        Resources=[vpc_id],
        Tags=[{"Key": "Environment", "Value": "dev"}],
    )

    mock_session = MagicMock()
    mock_session.region_name = AWS_REGION

    with patch("infra.scripts.vpc_endpoints.boto3") as mock_boto:
        mock_boto.client.return_value = client
        mock_boto.session.Session.return_value = mock_session
        main()

    captured = capsys.readouterr()
    assert "VPC endpoints" in captured.out

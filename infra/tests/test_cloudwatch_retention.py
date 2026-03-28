"""Tests for CloudWatch log retention management.

TDD: These tests are written BEFORE implementation and must fail first.
The implementation script must set 7-day retention on all /aws/* log groups.
"""
import boto3
import pytest
from moto import mock_aws

from infra.scripts.cloudwatch_retention import (
    get_aws_log_groups,
    set_retention_policy,
    apply_retention_to_all_aws_groups,
)

AWS_REGION = "us-east-1"
RETENTION_DAYS = 7


@pytest.fixture(autouse=True)
def aws_env(aws_credentials):
    pass


@mock_aws
def test_get_aws_log_groups_returns_only_aws_prefixed(aws_credentials):
    """Only /aws/* log groups are returned; others are ignored."""
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/aws/lambda/my-func")
    client.create_log_group(logGroupName="/aws/rds/cluster/dev-db")
    client.create_log_group(logGroupName="/app/backend")  # should be excluded

    groups = get_aws_log_groups(client)

    names = [g["logGroupName"] for g in groups]
    assert "/aws/lambda/my-func" in names
    assert "/aws/rds/cluster/dev-db" in names
    assert "/app/backend" not in names


@mock_aws
def test_get_aws_log_groups_returns_empty_when_none(aws_credentials):
    """Returns empty list when no /aws/* log groups exist."""
    client = boto3.client("logs", region_name=AWS_REGION)
    groups = get_aws_log_groups(client)
    assert groups == []


@mock_aws
def test_set_retention_policy_sets_7_days(aws_credentials):
    """set_retention_policy sets the retention to exactly 7 days."""
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/aws/lambda/test-fn")

    set_retention_policy(client, "/aws/lambda/test-fn", RETENTION_DAYS)

    groups = client.describe_log_groups(logGroupNamePrefix="/aws/lambda/test-fn")
    group = groups["logGroups"][0]
    assert group["retentionInDays"] == RETENTION_DAYS


@mock_aws
def test_apply_retention_to_all_aws_groups_updates_all(aws_credentials):
    """apply_retention_to_all_aws_groups applies 7-day retention to every /aws/* group."""
    client = boto3.client("logs", region_name=AWS_REGION)
    log_group_names = [
        "/aws/lambda/fn-a",
        "/aws/lambda/fn-b",
        "/aws/ecs/service/dev-api",
    ]
    for name in log_group_names:
        client.create_log_group(logGroupName=name)

    result = apply_retention_to_all_aws_groups(client, RETENTION_DAYS)

    assert result["updated"] == 3
    assert result["failed"] == 0
    for name in log_group_names:
        groups = client.describe_log_groups(logGroupNamePrefix=name)
        assert groups["logGroups"][0]["retentionInDays"] == RETENTION_DAYS


@mock_aws
def test_apply_retention_skips_already_set_groups(aws_credentials):
    """Groups that already have the correct retention are counted but not re-set."""
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/aws/lambda/already-set")
    client.put_retention_policy(
        logGroupName="/aws/lambda/already-set",
        retentionInDays=RETENTION_DAYS,
    )

    result = apply_retention_to_all_aws_groups(client, RETENTION_DAYS)

    assert result["failed"] == 0
    assert result["updated"] >= 1


@mock_aws
def test_apply_retention_does_not_touch_non_aws_groups(aws_credentials):
    """Log groups outside /aws/* are never modified."""
    client = boto3.client("logs", region_name=AWS_REGION)
    client.create_log_group(logGroupName="/app/my-service")
    client.create_log_group(logGroupName="/aws/lambda/fn-a")

    apply_retention_to_all_aws_groups(client, RETENTION_DAYS)

    non_aws = client.describe_log_groups(logGroupNamePrefix="/app/my-service")
    group = non_aws["logGroups"][0]
    assert "retentionInDays" not in group

"""Tests for VPC Gateway Endpoint creation (S3 and DynamoDB).

TDD: Tests written BEFORE implementation.
The implementation must:
- Create Gateway VPC Endpoints for S3 and DynamoDB in the dev VPC
- Endpoints are free and eliminate NAT data transfer charges
- Associate endpoints with all route tables in the VPC
"""
import boto3
import pytest
from moto import mock_aws

from infra.scripts.vpc_endpoints import (
    get_dev_vpc_id,
    get_route_table_ids,
    create_gateway_endpoint,
    apply_vpc_endpoints,
    ENDPOINT_SERVICES,
)

AWS_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_env(aws_credentials):
    pass


@mock_aws
def test_get_dev_vpc_id_returns_tagged_vpc(aws_credentials):
    """Returns VPC ID of the VPC tagged Environment=dev."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    client.create_tags(
        Resources=[vpc_id],
        Tags=[{"Key": "Environment", "Value": "dev"}],
    )

    result = get_dev_vpc_id(client)

    assert result == vpc_id


@mock_aws
def test_get_dev_vpc_id_returns_none_when_no_dev_vpc(aws_credentials):
    """Returns None when no VPC tagged Environment=dev exists."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    result = get_dev_vpc_id(client)
    assert result is None


@mock_aws
def test_get_route_table_ids_returns_tables_for_vpc(aws_credentials):
    """Returns all route table IDs associated with the given VPC."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    rt = client.create_route_table(VpcId=vpc_id)
    rt_id = rt["RouteTable"]["RouteTableId"]

    tables = get_route_table_ids(client, vpc_id)

    assert rt_id in tables


@mock_aws
def test_create_gateway_endpoint_creates_s3_endpoint(aws_credentials):
    """Creates an S3 Gateway endpoint in the given VPC."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    endpoint = create_gateway_endpoint(
        client,
        vpc_id=vpc_id,
        service_name=f"com.amazonaws.{AWS_REGION}.s3",
        route_table_ids=[],
    )

    assert endpoint is not None
    assert endpoint["VpcEndpointId"].startswith("vpce-")


@mock_aws
def test_create_gateway_endpoint_creates_dynamodb_endpoint(aws_credentials):
    """Creates a DynamoDB Gateway endpoint in the given VPC."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    endpoint = create_gateway_endpoint(
        client,
        vpc_id=vpc_id,
        service_name=f"com.amazonaws.{AWS_REGION}.dynamodb",
        route_table_ids=[],
    )

    assert endpoint is not None
    assert endpoint["VpcEndpointId"].startswith("vpce-")


def test_endpoint_services_contains_s3_and_dynamodb():
    """ENDPOINT_SERVICES constant includes both S3 and DynamoDB."""
    services_lower = [s.lower() for s in ENDPOINT_SERVICES]
    assert any("s3" in s for s in services_lower)
    assert any("dynamodb" in s for s in services_lower)


@mock_aws
def test_apply_vpc_endpoints_returns_both_endpoints(aws_credentials):
    """apply_vpc_endpoints creates Gateway endpoints for both S3 and DynamoDB."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    client.create_tags(
        Resources=[vpc_id],
        Tags=[{"Key": "Environment", "Value": "dev"}],
    )

    result = apply_vpc_endpoints(client, AWS_REGION)

    assert result["created"] == 2
    assert result["failed"] == 0
    assert len(result["endpoint_ids"]) == 2


@mock_aws
def test_apply_vpc_endpoints_fails_gracefully_when_no_vpc(aws_credentials):
    """apply_vpc_endpoints returns an error when no dev VPC is found."""
    client = boto3.client("ec2", region_name=AWS_REGION)
    result = apply_vpc_endpoints(client, AWS_REGION)
    assert result["created"] == 0
    assert "error" in result

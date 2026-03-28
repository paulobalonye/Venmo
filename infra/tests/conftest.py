"""Shared fixtures for AWS infrastructure tests."""
import os
import boto3
import pytest
from moto import mock_aws


AWS_REGION = "us-east-1"
DEV_TAG = {"Key": "Environment", "Value": "dev"}


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = AWS_REGION


@pytest.fixture(scope="function")
def logs_client(aws_credentials):
    with mock_aws():
        yield boto3.client("logs", region_name=AWS_REGION)


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name=AWS_REGION)


@pytest.fixture(scope="function")
def ec2_client(aws_credentials):
    with mock_aws():
        yield boto3.client("ec2", region_name=AWS_REGION)

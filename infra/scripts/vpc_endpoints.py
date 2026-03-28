"""Create VPC Gateway Endpoints for S3 and DynamoDB in the dev VPC.

Phase 1 quick win — no downtime, zero cost.
Gateway endpoints route S3/DynamoDB traffic through AWS backbone instead
of through NAT Gateway, eliminating per-GB data transfer charges.
"""
from __future__ import annotations

import logging
from typing import Any

import boto3

DEV_TAG_KEY = "Environment"
DEV_TAG_VALUE = "dev"

# Service names for Gateway endpoints (region is interpolated at runtime)
ENDPOINT_SERVICE_SUFFIXES = ["s3", "dynamodb"]

# Exported constant for tests — resolved lazily with region substitution
ENDPOINT_SERVICES = [
    "com.amazonaws.{region}.s3",
    "com.amazonaws.{region}.dynamodb",
]

logger = logging.getLogger(__name__)


def get_dev_vpc_id(client: Any) -> str | None:
    """Return the VPC ID of the VPC tagged Environment=dev, or None."""
    response = client.describe_vpcs(
        Filters=[{"Name": f"tag:{DEV_TAG_KEY}", "Values": [DEV_TAG_VALUE]}]
    )
    vpcs = response.get("Vpcs", [])
    if not vpcs:
        return None
    return vpcs[0]["VpcId"]


def get_route_table_ids(client: Any, vpc_id: str) -> list[str]:
    """Return all route table IDs for the given VPC."""
    response = client.describe_route_tables(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )
    return [rt["RouteTableId"] for rt in response.get("RouteTables", [])]


def create_gateway_endpoint(
    client: Any,
    vpc_id: str,
    service_name: str,
    route_table_ids: list[str],
) -> dict:
    """Create a Gateway VPC Endpoint and return the endpoint object."""
    kwargs: dict[str, Any] = {
        "VpcEndpointType": "Gateway",
        "VpcId": vpc_id,
        "ServiceName": service_name,
    }
    if route_table_ids:
        kwargs["RouteTableIds"] = route_table_ids

    response = client.create_vpc_endpoint(**kwargs)
    return response["VpcEndpoint"]


def apply_vpc_endpoints(client: Any, region: str) -> dict:
    """Create S3 and DynamoDB Gateway endpoints in the dev VPC.

    Returns {"created": int, "failed": int, "endpoint_ids": list, "error": str|None}.
    """
    vpc_id = get_dev_vpc_id(client)
    if vpc_id is None:
        return {
            "created": 0,
            "failed": 0,
            "endpoint_ids": [],
            "error": "No VPC tagged Environment=dev found",
        }

    route_table_ids = get_route_table_ids(client, vpc_id)
    created = 0
    failed = 0
    endpoint_ids: list[str] = []
    errors: list[str] = []

    for suffix in ENDPOINT_SERVICE_SUFFIXES:
        service_name = f"com.amazonaws.{region}.{suffix}"
        try:
            endpoint = create_gateway_endpoint(
                client,
                vpc_id=vpc_id,
                service_name=service_name,
                route_table_ids=route_table_ids,
            )
            endpoint_ids.append(endpoint["VpcEndpointId"])
            created += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{service_name}: {exc}")
            logger.error("Failed to create endpoint for %s: %s", service_name, exc)

    result: dict = {"created": created, "failed": failed, "endpoint_ids": endpoint_ids}
    if errors:
        result["error"] = "; ".join(errors)
    return result


def main() -> None:
    """Entrypoint: create Gateway endpoints for S3 and DynamoDB in the dev VPC."""
    import boto3
    client = boto3.client("ec2")
    region = boto3.session.Session().region_name or "us-east-1"
    result = apply_vpc_endpoints(client, region)
    print(
        f"VPC endpoints: created={result['created']} failed={result['failed']} "
        f"ids={result['endpoint_ids']}"
    )
    if result.get("error"):
        print(f"  ERROR: {result['error']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

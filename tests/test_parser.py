"""Tests for briefing.parser.

Fixtures are sanitized inventory samples derived from
multicloud-sa-toolkit UC02 discovery runs (aws, azure, gcp).
"""
import json
from pathlib import Path

import pytest

from briefing.parser import parse_inventory, build_estate, CloudSummary, EstateSummary

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


class TestParseAWS:
    def test_cloud_detected(self):
        assert parse_inventory(load("aws_inventory.sample.json")).cloud == "aws"

    def test_vpc_count(self):
        assert parse_inventory(load("aws_inventory.sample.json")).vpc_count == 1

    def test_subnet_count(self):
        assert parse_inventory(load("aws_inventory.sample.json")).subnet_count == 4

    def test_security_group_count(self):
        assert parse_inventory(load("aws_inventory.sample.json")).security_group_count == 22

    def test_default_vpc_detected(self):
        assert parse_inventory(load("aws_inventory.sample.json")).uses_default_vpc is True

    def test_scope_is_account_id(self):
        result = parse_inventory(load("aws_inventory.sample.json"))
        assert result.scope != ""


class TestParseAzure:
    def test_cloud_detected(self):
        assert parse_inventory(load("azure_inventory.sample.json")).cloud == "azure"

    def test_empty_environment_counts_zero(self):
        result = parse_inventory(load("azure_inventory.sample.json"))
        assert result.vpc_count == 0
        assert result.instance_count == 0

    def test_scope_is_subscription_id(self):
        result = parse_inventory(load("azure_inventory.sample.json"))
        assert "0000" in result.scope


class TestParseGCP:
    def test_cloud_detected(self):
        assert parse_inventory(load("gcp_inventory.sample.json")).cloud == "gcp"

    def test_vpc_count(self):
        assert parse_inventory(load("gcp_inventory.sample.json")).vpc_count == 1

    def test_instance_count(self):
        assert parse_inventory(load("gcp_inventory.sample.json")).instance_count == 1

    def test_default_service_account_detected(self):
        assert parse_inventory(load("gcp_inventory.sample.json")).uses_default_service_account is True

    def test_scope_is_project_id(self):
        result = parse_inventory(load("gcp_inventory.sample.json"))
        assert result.scope == "sample-gcp-project"


class TestBuildEstate:
    def test_multi_cloud_estate(self):
        inventories = [
            load("aws_inventory.sample.json"),
            load("azure_inventory.sample.json"),
            load("gcp_inventory.sample.json"),
        ]
        estate = build_estate(inventories)
        assert len(estate.clouds) == 3
        assert {c.cloud for c in estate.clouds} == {"aws", "azure", "gcp"}

    def test_no_drift_by_default(self):
        estate = build_estate([load("aws_inventory.sample.json")])
        assert estate.has_drift is False

import pytest
from unittest.mock import MagicMock

from kube_service_selectors.main import ServiceSelectorsCollector


@pytest.fixture
def k8s_client():
    return MagicMock()


@pytest.fixture
def collector(k8s_client):
    return ServiceSelectorsCollector(k8s_client)


@pytest.fixture
def namespaced_collector(k8s_client):
    return ServiceSelectorsCollector(k8s_client, namespaces=["default"])

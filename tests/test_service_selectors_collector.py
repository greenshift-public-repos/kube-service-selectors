import pytest

from dataclasses import dataclass
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from kube_service_selectors.main import (
    ServiceSelectorsCollector,
    DEFAULT_LABELS,
    DEFAULT_LIMIT,
)
from kube_service_selectors.utils import LABEL_PREFIX


@dataclass
class V1ServiceSpecMock:
    selector: dict[str, str] | None


@dataclass
class V1ObjectMetaMock:
    name: str
    namespace: str
    uid: str


@dataclass
class V1ServiceMock:
    metadata: V1ObjectMetaMock
    spec: V1ServiceSpecMock


@dataclass
class V1ListMetaMock:
    _continue: str = None


@dataclass
class ServiceListResponseMock:
    items: list[V1ServiceMock]
    metadata: V1ListMetaMock


def make_service(name, namespace, uid, selector):
    return V1ServiceMock(
        metadata=V1ObjectMetaMock(name, namespace, uid),
        spec=V1ServiceSpecMock(selector),
    )


def make_response(items, _continue=None):
    return ServiceListResponseMock(items, V1ListMetaMock(_continue))


def check_gauge(gauge, expected_count):
    assert gauge is not None
    assert isinstance(gauge, GaugeMetricFamily)
    assert len(gauge.samples) == expected_count
    for sample in gauge.samples:
        required = {
            k: v for k, v in sample.labels.items() if k in DEFAULT_LABELS
        }
        optional = {
            k: v for k, v in sample.labels.items() if k not in DEFAULT_LABELS
        }
        assert len(required) == len(DEFAULT_LABELS)
        assert all(k.startswith(LABEL_PREFIX) for k in optional)


def get_counter_values(counter):
    return {s.labels["result"]: s.value for s in counter.samples}


def test_all_namespaces_no_services(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response([])
    gauge, counter = list(collector.collect())
    check_gauge(gauge, 0)
    assert isinstance(counter, CounterMetricFamily)


def test_namespaced_no_services(namespaced_collector, k8s_client):
    k8s_client.list_namespaced_service.return_value = make_response([])
    gauge, counter = list(namespaced_collector.collect())
    check_gauge(gauge, 0)
    assert isinstance(counter, CounterMetricFamily)


def test_all_namespaces_single_service(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response(
        [make_service("name", "namespace", "uid", {"key": "value"})]
    )
    gauge, counter = list(collector.collect())
    check_gauge(gauge, 1)


def test_namespaced_single_service(namespaced_collector, k8s_client):
    k8s_client.list_namespaced_service.return_value = make_response(
        [make_service("name", "namespace", "uid", {"key": "value"})]
    )
    gauge, counter = list(namespaced_collector.collect())
    check_gauge(gauge, 1)


def test_all_namespaces_pagination(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.side_effect = [
        make_response(
            [
                make_service(f"n{i}", f"ns{i}", f"uid{i}", {f"k{i}": f"v{i}"})
                for i in range(DEFAULT_LIMIT)
            ],
            _continue="token",
        ),
        make_response(
            [
                make_service(f"n{i}", f"ns{i}", f"uid{i}", {f"k{i}": f"v{i}"})
                for i in range(DEFAULT_LIMIT, DEFAULT_LIMIT * 2)
            ]
        ),
    ]
    gauge, _ = list(collector.collect())
    check_gauge(gauge, DEFAULT_LIMIT * 2)


def test_namespaced_pagination(namespaced_collector, k8s_client):
    k8s_client.list_namespaced_service.side_effect = [
        make_response(
            [
                make_service(f"n{i}", f"ns{i}", f"uid{i}", {f"k{i}": f"v{i}"})
                for i in range(DEFAULT_LIMIT)
            ],
            _continue="token",
        ),
        make_response(
            [
                make_service(f"n{i}", f"ns{i}", f"uid{i}", {f"k{i}": f"v{i}"})
                for i in range(DEFAULT_LIMIT, DEFAULT_LIMIT * 2)
            ]
        ),
    ]
    gauge, _ = list(namespaced_collector.collect())
    check_gauge(gauge, DEFAULT_LIMIT * 2)


def test_service_with_none_selector(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response(
        [make_service("headless", "default", "uid-1", None)]
    )
    gauge, _ = list(collector.collect())
    check_gauge(gauge, 1)
    sample = gauge.samples[0]
    assert sample.labels["service"] == "headless"
    assert sample.labels["namespace"] == "default"
    assert sample.labels["uid"] == "uid-1"
    assert all(k in DEFAULT_LABELS for k in sample.labels)


def test_service_labels_in_metric(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response(
        [make_service("my-svc", "my-ns", "my-uid", {"app": "nginx"})]
    )
    gauge, _ = list(collector.collect())
    sample = gauge.samples[0]
    assert sample.labels["service"] == "my-svc"
    assert sample.labels["namespace"] == "my-ns"
    assert sample.labels["uid"] == "my-uid"
    assert sample.labels["label_app"] == "nginx"
    assert sample.value == 1.0


def test_success_counter_values(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response([])
    _, counter = list(collector.collect())
    values = get_counter_values(counter)
    assert values["succeeded"] == 1
    assert values["failed"] == 0


def test_collect_exception_yields_failed_counter(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.side_effect = RuntimeError(
        "API error"
    )
    results = list(collector.collect())
    assert len(results) == 1
    counter = results[0]
    assert isinstance(counter, CounterMetricFamily)
    values = get_counter_values(counter)
    assert values["failed"] == 1


def test_counter_accumulates_across_calls(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response([])
    list(collector.collect())
    _, counter = list(collector.collect())
    values = get_counter_values(counter)
    assert values["succeeded"] == 2
    assert values["failed"] == 0


def test_multiple_namespaces(k8s_client):
    coll = ServiceSelectorsCollector(k8s_client, namespaces=["ns1", "ns2"])
    k8s_client.list_namespaced_service.side_effect = [
        make_response([make_service("svc1", "ns1", "uid1", {"k": "v"})]),
        make_response([make_service("svc2", "ns2", "uid2", {"k": "v"})]),
    ]
    gauge, _ = list(coll.collect())
    check_gauge(gauge, 2)
    assert k8s_client.list_namespaced_service.call_count == 2


def test_multiple_services_same_selector_shape(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response(
        [
            make_service("svc1", "ns", "uid1", {"app": "a", "env": "prod"}),
            make_service("svc2", "ns", "uid2", {"app": "b", "env": "staging"}),
        ]
    )
    gauge, _ = list(collector.collect())
    check_gauge(gauge, 2)


def test_service_with_conflicting_selector_labels(collector, k8s_client):
    k8s_client.list_service_for_all_namespaces.return_value = make_response(
        [
            make_service(
                "svc", "ns", "uid", {"key.name": "v1", "key_name": "v2"}
            )
        ]
    )
    gauge, _ = list(collector.collect())
    check_gauge(gauge, 1)
    sample = gauge.samples[0]
    conflict_keys = [k for k in sample.labels if k.startswith(LABEL_PREFIX)]
    assert len(conflict_keys) == 2
    assert all("conflict" in k for k in conflict_keys)


def test_collector_with_timeout(k8s_client):
    coll = ServiceSelectorsCollector(k8s_client, timeout=5)
    k8s_client.list_service_for_all_namespaces.return_value = make_response([])
    gauge, _ = list(coll.collect())
    call_kwargs = k8s_client.list_service_for_all_namespaces.call_args.kwargs
    assert call_kwargs["_request_timeout"] == 5

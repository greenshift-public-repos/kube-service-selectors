import pytest

from kube_service_selectors.utils import (
    get_label_name,
    label_conflict_suffix,
    map_to_prometheus_labels,
    sanitize_label_name,
    to_snake_case,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("test_string", "test_string"),
        ("test\\string", "test_string"),
        ("test!string", "test_string"),
        ("test space", "test_space"),
        ("test.string", "test_string"),
        ("test/string", "test_string"),
        ("test-string", "test_string"),
        ("", ""),
        ("123abc", "123abc"),
        ("a_b_c", "a_b_c"),
    ],
)
def test_sanitize_label_name(value, expected):
    assert sanitize_label_name(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("testString", "test_string"),
        ("TestString", "test_string"),
        ("Test_string", "test_string"),
        ("alreadysnake", "alreadysnake"),
        ("CamelCaseString", "camel_case_string"),
        ("test123Value", "test123_value"),
        ("ABC", "abc"),
        ("already_snake_case", "already_snake_case"),
    ],
)
def test_to_snake_case(value, expected):
    assert to_snake_case(value) == expected


@pytest.mark.parametrize(
    "value,prefix,expected",
    [
        ("TestString", None, "test_string"),
        ("TestString", "some", "some_test_string"),
        ("test.key", "label", "label_test_key"),
        ("myKey", "prefix", "prefix_my_key"),
        ("Key_1", "label", "label_key_1"),
    ],
)
def test_get_label_name(value, prefix, expected):
    if prefix is None:
        assert get_label_name(value) == expected
    else:
        assert get_label_name(value, prefix) == expected


@pytest.mark.parametrize("i", range(10))
def test_label_conflict_suffix(i):
    value = "test_string"
    assert label_conflict_suffix(value, i) == f"{value}_conflict{i}"


def test_map_to_prometheus_empty_labels():
    assert map_to_prometheus_labels({}) == ([], [])


def test_map_to_prometheus_labels():
    labels = {"key_1": "value_1", "key_2": "value_2", "key_3": "value_3"}
    keys, values = map_to_prometheus_labels(labels)
    assert keys == ["label_key_1", "label_key_2", "label_key_3"]
    assert values == ["value_1", "value_2", "value_3"]


def test_map_to_prometheus_labels_conflicts():
    labels = {
        "key_1": "value_4",
        "key.1": "value_2",
        "key/1": "value_3",
        "Key_1": "value_1",
    }
    keys, values = map_to_prometheus_labels(labels)
    assert keys == [
        "label_key_1_conflict1",
        "label_key_1_conflict2",
        "label_key_1_conflict3",
        "label_key_1_conflict4",
    ]
    assert values == ["value_1", "value_2", "value_3", "value_4"]


def test_map_to_prometheus_labels_single_conflict():
    labels = {"key.1": "value_1", "key_1": "value_2"}
    keys, values = map_to_prometheus_labels(labels)
    assert keys == ["label_key_1_conflict1", "label_key_1_conflict2"]
    assert values == ["value_1", "value_2"]


def test_map_to_prometheus_labels_mixed():
    labels = {
        "app": "myapp",
        "version.major": "1",
        "version_major": "2",
    }
    keys, values = map_to_prometheus_labels(labels)
    label_map = dict(zip(keys, values))
    assert label_map["label_app"] == "myapp"
    assert "label_version_major_conflict1" in label_map
    assert "label_version_major_conflict2" in label_map


def test_map_to_prometheus_labels_preserves_values():
    labels = {"MyKey": "my-value", "another_key": "another-value"}
    keys, values = map_to_prometheus_labels(labels)
    label_map = dict(zip(keys, values))
    assert label_map["label_my_key"] == "my-value"
    assert label_map["label_another_key"] == "another-value"


def test_map_to_prometheus_labels_single_entry():
    labels = {"app": "nginx"}
    keys, values = map_to_prometheus_labels(labels)
    assert keys == ["label_app"]
    assert values == ["nginx"]

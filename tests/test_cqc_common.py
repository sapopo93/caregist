"""Tests for cqc_common.py shared utilities."""

import pytest

from cqc_common import (
    ensure_list,
    normalize_whitespace,
    parse_any_date,
    to_float,
    deep_get,
    first_non_empty,
    flatten_json,
)


class TestNormalizeWhitespace:
    def test_basic(self):
        assert normalize_whitespace("  hello   world  ") == "hello world"

    def test_none(self):
        assert normalize_whitespace(None) == ""

    def test_tabs_newlines(self):
        assert normalize_whitespace("hello\t\nworld") == "hello world"

    def test_number(self):
        assert normalize_whitespace(42) == "42"


class TestParseAnyDate:
    def test_iso_format(self):
        assert parse_any_date("2024-01-15") == "2024-01-15"

    def test_iso_with_time(self):
        assert parse_any_date("2024-01-15T10:30:00") == "2024-01-15"

    def test_uk_format(self):
        assert parse_any_date("15/01/2024") == "2024-01-15"

    def test_uk_dash_format(self):
        assert parse_any_date("15-01-2024") == "2024-01-15"

    def test_none(self):
        assert parse_any_date(None) == ""

    def test_empty_string(self):
        assert parse_any_date("") == ""

    def test_invalid(self):
        assert parse_any_date("not a date") == ""

    def test_iso_with_tz(self):
        assert parse_any_date("2024-01-15T10:30:00Z") == "2024-01-15"


class TestEnsureList:
    def test_none(self):
        assert ensure_list(None) == []

    def test_list(self):
        assert ensure_list([1, 2, 3]) == [1, 2, 3]

    def test_string_pipe_delimited(self):
        assert ensure_list("a|b|c") == ["a", "b", "c"]

    def test_json_string(self):
        assert ensure_list('["x", "y"]') == ["x", "y"]

    def test_empty_string(self):
        assert ensure_list("") == []

    def test_single_value(self):
        assert ensure_list(42) == [42]

    def test_tuple(self):
        assert ensure_list((1, 2)) == [1, 2]


class TestToFloat:
    def test_float(self):
        assert to_float(3.14) == 3.14

    def test_int(self):
        assert to_float(42) == 42.0

    def test_string(self):
        assert to_float("52.088") == 52.088

    def test_none(self):
        assert to_float(None) is None

    def test_empty(self):
        assert to_float("") is None

    def test_invalid(self):
        assert to_float("abc") is None


class TestDeepGet:
    def test_simple(self):
        assert deep_get({"a": 1}, "a") == 1

    def test_nested(self):
        assert deep_get({"a": {"b": 2}}, "a.b") == 2

    def test_missing(self):
        assert deep_get({"a": 1}, "b") is None

    def test_default(self):
        assert deep_get({"a": 1}, "b", "default") == "default"

    def test_none_data(self):
        assert deep_get(None, "a") is None

    def test_list_index(self):
        assert deep_get({"a": [10, 20]}, "a.1") == 20


class TestFirstNonEmpty:
    def test_first_value(self):
        assert first_non_empty(["a", "b"]) == "a"

    def test_skip_empty(self):
        assert first_non_empty(["", None, "c"]) == "c"

    def test_all_empty(self):
        assert first_non_empty(["", None, []], default="fallback") == "fallback"

    def test_tuple_mode(self):
        data = {"name": "test"}
        assert first_non_empty([(data, "name"), (data, "missing")]) == "test"


class TestFlattenJson:
    def test_simple(self):
        assert flatten_json({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_nested(self):
        result = flatten_json({"a": {"b": 1}})
        assert result == {"a.b": 1}

    def test_list_serialized(self):
        result = flatten_json({"a": [1, 2]})
        assert result == {"a": "[1, 2]"}

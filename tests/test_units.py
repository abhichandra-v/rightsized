import pytest

from rightsized.units import format_cpu, format_memory, parse_cpu, parse_memory


@pytest.mark.parametrize("q,want", [("500m", 0.5), ("1", 1.0), ("0.25", 0.25), (2, 2.0), (None, None)])
def test_parse_cpu(q, want):
    assert parse_cpu(q) == want


@pytest.mark.parametrize("q,want", [
    ("512Mi", 512 * 2**20), ("1Gi", 2**30), ("1G", 10**9), ("262144k", 262144000), ("1000", 1000), (None, None),
])
def test_parse_memory(q, want):
    assert parse_memory(q) == want


def test_format_roundtrip():
    assert format_cpu(0.165) == "165m"
    assert format_cpu(2.0) == "2"
    assert format_memory(2**30) == "1Gi"
    assert format_memory(300 * 2**20) == "300Mi"
    assert format_memory(300 * 2**20 + 1) == "301Mi"  # never round memory down

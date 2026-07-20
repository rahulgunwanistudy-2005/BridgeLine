"""Registry ordering and HTTP exposure tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from bridgeline.main import create_app
from bridgeline.rules.citations import parse_citations
from bridgeline.rules.registry import RULES


def test_registry_contains_three_distinct_distribution_citations() -> None:
    assert [(rule.id, rule.citation) for rule in RULES] == [
        ("teacher-access", "34 CFR §300.323(d)(1)"),
        ("teacher-informed-responsibilities", "34 CFR §300.323(d)(2)(i)"),
        ("teacher-informed-accommodations", "34 CFR §300.323(d)(2)(ii)"),
        ("initial-iep-meeting-30-days", "34 CFR §300.323(c)(1)"),
        ("annual-review", "34 CFR §300.324(b)(1)(i)"),
        ("triennial-reevaluation", "34 CFR §300.303(b)(2)"),
        ("progress-report-cadence", "34 CFR §300.320(a)(3)"),
        ("services-statement", "34 CFR §300.320(a)(4)"),
        ("services-without-delay", "34 CFR §300.323(c)(2)"),
        ("iep-in-effect-start-of-year", "34 CFR §300.323(a)"),
    ]


def test_registry_citations_exactly_match_human_owned_spec() -> None:
    citation_path = Path(__file__).resolve().parents[4] / "references" / "idea-citations.md"
    citations = parse_citations(citation_path.read_text(encoding="utf-8"))

    assert all(citations[rule.id] == rule.citation for rule in RULES)


def test_registry_endpoint_is_curl_readable() -> None:
    response = TestClient(create_app()).get("/rules")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["rules"]] == [rule.id for rule in RULES]


def test_deadline_feed_is_wired_into_application() -> None:
    schema = create_app().openapi()

    assert "/compliance/deadlines" in schema["paths"]


def test_findings_feed_and_lifecycle_are_wired_into_application() -> None:
    schema = create_app().openapi()

    assert "get" in schema["paths"]["/findings"]
    assert "post" in schema["paths"]["/findings/derive"]
    assert "patch" in schema["paths"]["/findings/{finding_id}"]

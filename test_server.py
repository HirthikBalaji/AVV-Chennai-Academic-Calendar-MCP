"""
Unit tests and integration tests for AVV Chennai Academic Calendar MCP & OpenAPI Server.
"""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from calendar_service import CalendarService, get_calendar_service
from fastapi_app import create_app
from mcp_server import create_mcp_server


@pytest.fixture(scope="module")
def service() -> CalendarService:
    return get_calendar_service()


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def mcp():
    return create_mcp_server()


# =============================================================================
# 1. CALENDAR SERVICE TESTS
# =============================================================================

def test_calendar_metadata(service: CalendarService):
    meta = service.get_metadata()
    assert "Amrita Vishwa Vidyapeetham" in meta.institution
    assert meta.academic_year == "2026-27"
    assert meta.total_days == 374
    assert meta.start_date == "2026-06-01"
    assert meta.end_date == "2027-06-09"
    assert "W" in meta.legend
    assert "H" in meta.legend
    assert "CD" in meta.legend


def test_get_date_working_and_commencement(service: CalendarService):
    entry = service.get_date("2026-06-10")
    assert entry is not None
    assert entry.date == "2026-06-10"
    assert entry.day == "Wed"
    assert entry.status == "W"
    assert entry.is_working_day is True
    assert entry.is_holiday is False
    assert entry.senior_class_day == "CD01"
    assert "Commencement of III, V, & VII Sem" in entry.details


def test_get_date_holiday(service: CalendarService):
    entry = service.get_date("2026-10-02")
    assert entry is not None
    assert entry.date == "2026-10-02"
    assert entry.day == "Fri"
    assert entry.status == "H"
    assert entry.is_holiday is True
    assert entry.is_working_day is False
    assert "Gandhi Jayanthi" in entry.details


def test_get_date_vacation_break(service: CalendarService):
    # May 2027 has break entries with status = None
    entry = service.get_date("2027-05-05")
    assert entry is not None
    assert entry.status is None
    assert entry.is_working_day is False
    assert entry.is_holiday is False


def test_get_date_not_found(service: CalendarService):
    assert service.get_date("2025-01-01") is None
    assert service.get_date("2099-12-31") is None


def test_timetable_swaps(service: CalendarService):
    swaps = service.get_timetable_swaps()
    assert len(swaps) > 0
    # Saturday 2026-08-08 is Instructional Day (Friday TT)
    aug8 = next((s for s in swaps if s.date == "2026-08-08"), None)
    assert aug8 is not None
    assert aug8.special_timetable == "Friday TT"


def test_holidays_filtering(service: CalendarService):
    all_holidays = service.get_holidays()
    named_holidays = service.get_holidays(named_only=True)
    assert len(all_holidays) > len(named_holidays)
    assert len(named_holidays) >= 20

    # Test month filter
    oct_holidays = service.get_holidays(month="2026-10", named_only=True)
    for h in oct_holidays:
        assert h.date.startswith("2026-10")


def test_calculate_class_days(service: CalendarService):
    # Odd semester for senior students: 2026-06-10 to 2026-10-16
    res = service.calculate_class_days("2026-06-10", "2026-10-16", cohort="senior_ug_pg")
    assert res.total_calendar_days > 0
    assert res.working_days_count > 0
    assert res.senior_instructional_days == 95
    assert res.cohort_requested == "senior_ug_pg"


def test_search_events(service: CalendarService):
    deepavali = service.search_events("Deepavali")
    assert len(deepavali) >= 1
    assert "2026-11-08" in [d.date for d in deepavali]

    midterms = service.search_events("Midterm")
    assert len(midterms) >= 4


def test_milestones_retrieval(service: CalendarService):
    milestones = service.get_academic_milestones()
    categories = set(m.category for m in milestones)
    assert "commencement" in categories
    assert "midterm_exam" in categories
    assert "end_semester_exam" in categories
    assert "practical_exam" in categories
    assert "faculty_feedback" in categories
    assert "committee_meeting" in categories


# =============================================================================
# 2. FASTAPI REST ENDPOINTS TESTS
# =============================================================================

def test_fastapi_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["academic_year"] == "2026-27"


def test_fastapi_metadata(client: TestClient):
    resp = client.get("/api/v1/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["institution"] == "Amrita Vishwa Vidyapeetham, Chennai"
    assert data["version"] == "V2.0"


def test_fastapi_date_details(client: TestClient):
    resp = client.get("/api/v1/date/2026-06-10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["senior_class_day"] == "CD01"

    # 404 for missing date
    resp_404 = client.get("/api/v1/date/2020-01-01")
    assert resp_404.status_code == 404


def test_fastapi_calendar_range(client: TestClient):
    resp = client.get("/api/v1/calendar?start_date=2026-06-01&end_date=2026-06-15")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 15
    assert items[0]["date"] == "2026-06-01"
    assert items[-1]["date"] == "2026-06-15"


def test_fastapi_search(client: TestClient):
    resp = client.get("/api/v1/search?q=Pongal")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert any("Pongal" in r["details"] for r in results)


def test_fastapi_holidays(client: TestClient):
    resp = client.get("/api/v1/holidays?named_only=true")
    assert resp.status_code == 200
    holidays = resp.json()
    assert len(holidays) > 0


def test_fastapi_milestones(client: TestClient):
    resp = client.get("/api/v1/milestones?category=midterm_exam")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    assert all(i["category"] == "midterm_exam" for i in items)


def test_fastapi_class_days_stats(client: TestClient):
    resp = client.get("/api/v1/stats/class-days?start_date=2026-06-10&end_date=2026-10-16&cohort=senior_ug_pg")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calendar_days"] == 129
    assert data["working_days_count"] == 98


def test_fastapi_openapi_yaml(client: TestClient):
    resp = client.get("/openapi.yaml")
    assert resp.status_code == 200
    assert "openapi: 3.1.0" in resp.text
    assert "/api/v1/metadata" in resp.text


# =============================================================================
# 3. MCP SERVER TOOLS, RESOURCES, & PROMPTS TESTS
# =============================================================================

def test_mcp_tools_list_and_calls(mcp):
    async def run_mcp_tests():
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        assert "get_calendar_metadata" in tool_names
        assert "get_date_details" in tool_names
        assert "search_calendar" in tool_names
        assert "get_date_range_events" in tool_names
        assert "get_holidays" in tool_names
        assert "get_academic_milestones" in tool_names
        assert "get_upcoming_events" in tool_names
        assert "count_instructional_days" in tool_names
        assert "get_timetable_swaps" in tool_names
        assert "get_openapi_specification" in tool_names

        # Call get_calendar_metadata
        res, raw = await mcp.call_tool("get_calendar_metadata", {})
        assert "Amrita Vishwa Vidyapeetham" in res[0].text

        # Call search_calendar
        res, raw = await mcp.call_tool("search_calendar", {"query": "Independence"})
        assert "Independence Day" in res[0].text

        # Call count_instructional_days
        res, raw = await mcp.call_tool(
            "count_instructional_days",
            {"start_date": "2026-06-10", "end_date": "2026-07-10", "cohort": "senior_ug_pg"},
        )
        assert "working_days_count" in res[0].text

        # Call get_openapi_specification
        res, raw = await mcp.call_tool("get_openapi_specification", {"format": "json"})
        parsed = json.loads(res[0].text)
        assert parsed["openapi"] == "3.1.0"
        assert "/api/v1/metadata" in parsed["paths"]

    asyncio.run(run_mcp_tests())


def test_mcp_resources_and_prompts(mcp):
    async def run_resource_tests():
        resources = await mcp.list_resources()
        uris = [str(r.uri) for r in resources]
        assert "calendar://metadata" in uris
        assert "calendar://holidays" in uris
        assert "calendar://milestones" in uris
        assert "calendar://timetable-swaps" in uris
        assert "calendar://full" in uris
        assert "openapi://schema.json" in uris

        content = await mcp.read_resource("calendar://metadata")
        assert "Amrita Vishwa Vidyapeetham" in content[0].content

        prompts = await mcp.list_prompts()
        prompt_names = [p.name for p in prompts]
        assert "academic_advising" in prompt_names
        assert "holiday_and_leave_inquiry" in prompt_names
        assert "attendance_and_class_day_counter" in prompt_names

    asyncio.run(run_resource_tests())

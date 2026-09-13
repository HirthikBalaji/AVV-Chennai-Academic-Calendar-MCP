"""
Model Context Protocol (MCP) Server for Amrita Vishwa Vidyapeetham, Chennai Academic Calendar AY2026-27.
Compatible with FastMCP, stdio transport, and SSE/HTTP transports.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import yaml
from mcp.server.fastmcp import FastMCP

from calendar_service import get_calendar_service


def create_mcp_server() -> FastMCP:
    """Creates and configures the FastMCP academic calendar server."""

    service = get_calendar_service()

    mcp = FastMCP(
        name="avv-chennai-academic-calendar",
        instructions=(
            "You have access to the official Academic Calendar of Amrita Vishwa Vidyapeetham, "
            "Chennai Campus for Academic Year 2026-27 (Approved by Principal Dr. V. Jayakumar). "
            "Use the provided tools to query calendar dates, check working vs holiday status, "
            "look up class day numbers (CD01..CD90) for Senior UG/PG and First Year UG/PG, "
            "find examination schedules (midterms, practicals, end sem), class committee meetings, "
            "faculty feedbacks, timetable swaps (working Saturdays), and verify attendance days. "
            "The calendar also exposes its full OpenAPI 3.1 schema via get_openapi_specification."
        ),
    )

    # =========================================================================
    # MCP TOOLS
    # =========================================================================

    @mcp.tool()
    def get_calendar_metadata() -> Dict[str, Any]:
        """
        Get metadata about the academic calendar: institution name, academic year,
        version, approved authority, timetable coordinator, legend definitions, and date span.
        """
        meta = service.get_metadata()
        return meta.model_dump()

    @mcp.tool()
    def get_date_details(target_date: str) -> Dict[str, Any]:
        """
        Get comprehensive calendar details for a specific date.
        
        Args:
            target_date: ISO date (YYYY-MM-DD), or relative words ('today', 'tomorrow', 'yesterday').
                         Example: '2026-06-10', '2026-10-02', 'today'
        """
        entry = service.get_date(target_date)
        if not entry:
            meta = service.get_metadata()
            return {
                "error": f"Date '{target_date}' not found in calendar range ({meta.start_date} to {meta.end_date}).",
                "valid_range": {"start_date": meta.start_date, "end_date": meta.end_date},
            }
        return entry.model_dump()

    @mcp.tool()
    def search_calendar(
        query: str,
        cohort: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search calendar entries by keyword across event details, dates, and class days.

        Args:
            query: Search keyword (e.g., 'Midterm', 'Deepavali', 'Practical', 'Commencement', 'Meeting').
            cohort: Optional cohort filter: 'senior' (II, III, IV Yr UG & II Yr PG) or 'first_year' (I Yr UG & PG).
            status: Optional status filter: 'W' (working), 'CD' (working with class day), 'H' (holiday).
            limit: Maximum results to return (default 20).
        """
        results = service.search_events(query=query, cohort=cohort, status=status, limit=limit)
        return [r.model_dump() for r in results]

    @mcp.tool()
    def get_date_range_events(
        start_date: str,
        end_date: str,
        cohort: Optional[str] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        only_with_details: bool = True,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get schedule entries within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD), e.g. '2026-08-01'.
            end_date: End date (YYYY-MM-DD), e.g. '2026-08-31'.
            cohort: Optional cohort filter ('senior' or 'first_year').
            status: Optional status code ('W', 'H', 'CD').
            event_type: Optional type ('holiday', 'exam', 'practical_exam', 'commencement', 'feedback', 'committee_meeting', 'timetable_swap').
            only_with_details: If True, only returns dates with specific event descriptions/notes.
            limit: Max results (default 50).
        """
        results = service.query_dates(
            start_date=start_date,
            end_date=end_date,
            status=status,
            cohort=cohort,
            event_type=event_type,
            has_details=True if only_with_details else None,
            limit=limit,
        )
        return [r.model_dump() for r in results]

    @mcp.tool()
    def get_holidays(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[str] = None,
        named_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get official holidays and festival breaks.

        Args:
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).
            month: Specific month (YYYY-MM), e.g., '2026-10' or '2027-01'.
            named_only: If True, filters out standard weekend holidays and only returns named festivals/observances (e.g. Deepavali, Pongal, Gandhi Jayanthi).
            limit: Maximum entries (default 50).
        """
        results = service.get_holidays(
            start_date=start_date,
            end_date=end_date,
            month=month,
            named_only=named_only,
            limit=limit,
        )
        return [r.model_dump() for r in results]

    @mcp.tool()
    def get_academic_milestones(
        category: Optional[str] = None,
        cohort: Optional[str] = None,
        semester_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List major academic milestones: commencements, midterms, practical exams,
        end semester exams, class committee meetings, faculty feedback, and last instruction days.

        Args:
            category: Filter by milestone: 'commencement', 'midterm_exam', 'practical_exam', 'end_semester_exam', 'faculty_feedback', 'committee_meeting', 'last_instruction_day'.
            cohort: Filter by cohort: 'senior_ug_pg', 'first_year', or 'all'.
            semester_type: Filter by semester: 'odd' (Sem I, III, V, VII) or 'even' (Sem II, IV, VI, VIII).
        """
        results = service.get_academic_milestones(
            category=category,
            cohort=cohort,
            semester_type=semester_type,
        )
        return [r.model_dump() for r in results]

    @mcp.tool()
    def get_upcoming_events(
        reference_date: Optional[str] = None,
        limit: int = 10,
        days_ahead: Optional[int] = None,
        cohort: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming academic events, holidays, and milestones chronologically from a reference date.

        Args:
            reference_date: Starting date (YYYY-MM-DD). Defaults to current date or start of calendar.
            limit: Max upcoming events to return (default 10).
            days_ahead: Optional window in days (e.g. 30 days ahead).
            cohort: Optional cohort filter ('senior_ug_pg' or 'first_year').
        """
        results = service.get_upcoming_events(
            reference_date=reference_date,
            limit=limit,
            days_ahead=days_ahead,
            cohort=cohort,
        )
        return [r.model_dump() for r in results]

    @mcp.tool()
    def count_instructional_days(
        start_date: str,
        end_date: str,
        cohort: str = "senior_ug_pg",
    ) -> Dict[str, Any]:
        """
        Calculate working days, holidays, vacation days, and instructional class days
        (CDs from CD01 to CD90) between two dates. Useful for attendance verification.

        Args:
            start_date: Start date (YYYY-MM-DD), e.g. '2026-06-10'.
            end_date: End date (YYYY-MM-DD), e.g. '2026-10-16'.
            cohort: Target student group: 'senior_ug_pg' (Sem III, IV, V, VI, VII, VIII) or 'first_year' (Sem I, II).
        """
        res = service.calculate_class_days(start_date=start_date, end_date=end_date, cohort=cohort)
        return res.model_dump()

    @mcp.tool()
    def get_timetable_swaps(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all days where an alternate day timetable is observed (such as working Saturdays
        following Monday TT, Tuesday TT, Wednesday TT, or Friday TT).

        Args:
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).
        """
        results = service.get_timetable_swaps(start_date=start_date, end_date=end_date)
        return [r.model_dump() for r in results]

    @mcp.tool()
    def get_openapi_specification(format: str = "json") -> str:
        """
        Returns the full OpenAPI 3.1.0 specification for the Academic Calendar REST API.
        Enables LLMs and agents to discover all REST endpoints, schemas, parameters, and tags.

        Args:
            format: 'json' (default) or 'yaml'.
        """
        from fastapi_app import create_app

        fastapi_instance = create_app()
        schema = fastapi_instance.openapi()
        if format.lower() == "yaml":
            return yaml.dump(schema, sort_keys=False)
        return json.dumps(schema, indent=2)

    # =========================================================================
    # MCP RESOURCES
    # =========================================================================

    @mcp.resource("calendar://metadata")
    def resource_metadata() -> str:
        """Official metadata and institution legend for AY2026-27."""
        meta = service.get_metadata()
        return json.dumps(meta.model_dump(), indent=2)

    @mcp.resource("calendar://holidays")
    def resource_holidays() -> str:
        """Complete list of official named festival and public holidays in AY2026-27."""
        holidays = service.get_holidays(named_only=True, limit=200)
        return json.dumps([h.model_dump() for h in holidays], indent=2)

    @mcp.resource("calendar://milestones")
    def resource_milestones() -> str:
        """All major academic milestones (commencements, examinations, feedbacks, meetings)."""
        milestones = service.get_academic_milestones()
        return json.dumps([m.model_dump() for m in milestones], indent=2)

    @mcp.resource("calendar://timetable-swaps")
    def resource_timetable_swaps() -> str:
        """All working Saturdays and instructional days with timetable adjustments."""
        swaps = service.get_timetable_swaps()
        return json.dumps([s.model_dump() for s in swaps], indent=2)

    @mcp.resource("calendar://full")
    def resource_full_calendar() -> str:
        """Full raw academic calendar JSON dataset."""
        return json.dumps(service.get_full_calendar(), indent=2)

    @mcp.resource("openapi://schema.json")
    def resource_openapi_schema() -> str:
        """OpenAPI 3.1.0 specification for the Academic Calendar REST API."""
        from fastapi_app import create_app

        fastapi_instance = create_app()
        return json.dumps(fastapi_instance.openapi(), indent=2)

    # =========================================================================
    # MCP PROMPTS
    # =========================================================================

    @mcp.prompt("academic_advising")
    def prompt_academic_advising(
        cohort: str = "senior_ug_pg",
        current_date: str = "2026-09-01",
    ) -> str:
        """Prompt to guide the LLM in advising a student based on calendar milestones."""
        return (
            f"You are an academic advisor for students at Amrita Vishwa Vidyapeetham, Chennai. "
            f"The student belongs to cohort '{cohort}'. Today's reference date is '{current_date}'. "
            f"Use the academic calendar tools to:\n"
            f"1. Check upcoming midterms, practical exams, and end semester exams for this student.\n"
            f"2. Check the schedule of Class Committee Meetings and Faculty Feedback sessions.\n"
            f"3. Note the Last Instruction Day for the current semester.\n"
            f"4. Provide a structured, helpful preparation roadmap with key dates and advice."
        )

    @mcp.prompt("holiday_and_leave_inquiry")
    def prompt_holiday_inquiry(
        month: str = "2026-10",
    ) -> str:
        """Prompt to guide the LLM in answering questions about upcoming holidays and long weekends."""
        return (
            f"The user is asking about holidays, festival vacations, or long weekends in month '{month}' "
            f"at Amrita Vishwa Vidyapeetham, Chennai (AY2026-27).\n"
            f"1. Query the calendar for all holidays in '{month}' using get_holidays.\n"
            f"2. Identify long weekends (holidays adjacent to Saturday or Sunday).\n"
            f"3. Check whether any Saturday in that month is an instructional working day (using get_timetable_swaps).\n"
            f"4. Present a clear, well-formatted summary of holidays and working day exceptions."
        )

    @mcp.prompt("attendance_and_class_day_counter")
    def prompt_attendance_counter(
        cohort: str = "senior_ug_pg",
        from_date: str = "2026-06-10",
        to_date: str = "2026-10-16",
    ) -> str:
        """Prompt to guide the LLM in calculating class day totals (CD01 to CD90) and attendance requirements."""
        return (
            f"The user wants to verify instructional days and attendance requirements for cohort '{cohort}' "
            f"between '{from_date}' and '{to_date}'.\n"
            f"1. Use count_instructional_days to compute the exact number of class days (CDs) and working days.\n"
            f"2. Remember that each semester consists of 90 class days (CD01 to CD90).\n"
            f"3. Calculate the attendance thresholds (e.g. 75% and 80% minimum attendance required by university regulations).\n"
            f"4. Summarize the count and provide clear guidance to the student."
        )

    return mcp

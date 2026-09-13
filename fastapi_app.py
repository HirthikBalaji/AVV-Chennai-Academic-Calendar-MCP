"""
FastAPI application providing OpenAPI 3.1 REST endpoints and mounting MCP SSE transports
for the AVV Chennai Academic Calendar AY2026-27.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import yaml
from fastapi import FastAPI, HTTPException, Query, Path, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from calendar_service import (
    CalendarDayEntry,
    CalendarMetadata,
    ClassDayCountResult,
    MilestoneEntry,
    get_calendar_service,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    service = get_calendar_service()

    app = FastAPI(
        title="Amrita Vishwa Vidyapeetham, Chennai - Academic Calendar API",
        version="2.0.0",
        description=(
            "OpenAPI-compatible Academic Calendar Service & Model Context Protocol (MCP) Server "
            "for Amrita Vishwa Vidyapeetham, Chennai (Academic Year 2026-27). "
            "Designed for LLMs, autonomous agents, students, and faculty."
        ),
        contact={
            "name": "Campus Timetable Office",
            "email": "timetable@chennai.amrita.edu",
        },
        license_info={
            "name": "Internal Academic Use Only",
        },
        openapi_tags=[
            {"name": "Calendar Metadata", "description": "General calendar document info, version, and legend"},
            {"name": "Date Queries", "description": "Look up dates, day status, and class schedules"},
            {"name": "Events & Search", "description": "Search events, filtered date ranges, and activities"},
            {"name": "Holidays & Swaps", "description": "Holidays, festivals, and Saturday timetable orders"},
            {"name": "Milestones & Stats", "description": "Exam schedules, commencement dates, and instructional day counters"},
            {"name": "System & Spec", "description": "Health checks, raw export, and OpenAPI specification endpoints"},
        ],
    )

    # Enable CORS for web clients / LLM plugins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(
        "/api/v1/metadata",
        response_model=CalendarMetadata,
        summary="Get Academic Calendar Metadata",
        tags=["Calendar Metadata"],
    )
    def get_metadata():
        """
        Retrieves official academic calendar metadata:
        - Institution name, academic year, document title, and revision version
        - Approval authority and timetable coordinator
        - Legend explanation (W = Working for Staff, CD = Working for Staff & Students, H = Holiday)
        - Date span and total entry count
        """
        return service.get_metadata()

    @app.get(
        "/api/v1/date/{target_date}",
        response_model=CalendarDayEntry,
        summary="Get Calendar Details for Specific Date",
        tags=["Date Queries"],
    )
    def get_date_details(
        target_date: str = Path(
            ...,
            description="Date in YYYY-MM-DD format, or relative keyword 'today', 'tomorrow', 'yesterday'",
            examples=["2026-06-10", "2026-10-02", "today"],
        )
    ):
        """
        Retrieves complete schedule details for a single date:
        - Day of week (Mon-Sun)
        - Status code (W, CD, H, or None) and expanded description
        - Class Day number for senior UG/PG (e.g. CD01) and first year UG/PG
        - Special timetable instructions (e.g. 'Monday TT' on a Saturday)
        - Event details (examinations, holidays, feedback, meetings)
        """
        entry = service.get_date(target_date)
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Date '{target_date}' not found in calendar range ({service.get_metadata().start_date} to {service.get_metadata().end_date}).",
            )
        return entry

    @app.get(
        "/api/v1/calendar",
        response_model=List[CalendarDayEntry],
        summary="Query Calendar Range with Filters",
        tags=["Date Queries"],
    )
    def query_calendar(
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)", examples=["2026-06-01"]),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)", examples=["2026-06-30"]),
        status: Optional[str] = Query(None, description="Status code filter ('W', 'CD', 'H')", examples=["H"]),
        cohort: Optional[str] = Query(
            None,
            description="Filter by cohort instructional day: 'senior_ug_pg' or 'first_year'",
            examples=["senior_ug_pg"],
        ),
        event_type: Optional[str] = Query(
            None,
            description="Filter by event type ('holiday', 'exam', 'practical_exam', 'commencement', 'feedback', 'committee_meeting', 'timetable_swap')",
        ),
        has_details: Optional[bool] = Query(None, description="Only return days with non-empty details"),
        limit: int = Query(100, ge=1, le=400, description="Max items to return"),
        offset: int = Query(0, ge=0, description="Pagination offset"),
    ):
        """Query calendar entries within a range, optionally filtered by status, cohort, or event type."""
        return service.query_dates(
            start_date=start_date,
            end_date=end_date,
            status=status,
            cohort=cohort,
            event_type=event_type,
            has_details=has_details,
            limit=limit,
            offset=offset,
        )

    @app.get(
        "/api/v1/search",
        response_model=List[CalendarDayEntry],
        summary="Search Events by Keyword",
        tags=["Events & Search"],
    )
    def search_events(
        q: str = Query(..., description="Search keyword (e.g. 'Midterm', 'Deepavali', 'Practical', 'Commencement')"),
        cohort: Optional[str] = Query(None, description="Optional cohort filter ('senior' or 'first_year')"),
        status: Optional[str] = Query(None, description="Optional status filter ('W', 'H')"),
        limit: int = Query(50, ge=1, le=100, description="Max search results"),
    ):
        """Full-text case-insensitive search across event details, dates, and class days."""
        return service.search_events(query=q, cohort=cohort, status=status, limit=limit)

    @app.get(
        "/api/v1/holidays",
        response_model=List[CalendarDayEntry],
        summary="List Calendar Holidays",
        tags=["Holidays & Swaps"],
    )
    def get_holidays(
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        month: Optional[str] = Query(None, description="Specific month (YYYY-MM), e.g., '2026-10'"),
        named_only: bool = Query(
            False,
            description="If true, only returns named festival and public holidays (excluding recurring weekend holidays)",
        ),
        limit: int = Query(100, ge=1, le=200, description="Max items"),
    ):
        """List holidays with optional filtering for named festivals (e.g., Deepavali, Pongal, Gandhi Jayanthi)."""
        return service.get_holidays(
            start_date=start_date,
            end_date=end_date,
            month=month,
            named_only=named_only,
            limit=limit,
        )

    @app.get(
        "/api/v1/timetable-swaps",
        response_model=List[CalendarDayEntry],
        summary="Get Timetable Swaps / Working Saturdays",
        tags=["Holidays & Swaps"],
    )
    def get_timetable_swaps(
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    ):
        """Retrieve days where an alternate day timetable is followed (e.g. Saturday with Monday timetable)."""
        return service.get_timetable_swaps(start_date=start_date, end_date=end_date)

    @app.get(
        "/api/v1/milestones",
        response_model=List[MilestoneEntry],
        summary="List Academic Milestones",
        tags=["Milestones & Stats"],
    )
    def get_academic_milestones(
        category: Optional[str] = Query(
            None,
            description="Category: 'commencement', 'midterm_exam', 'practical_exam', 'end_semester_exam', 'faculty_feedback', 'committee_meeting', 'last_instruction_day'",
        ),
        cohort: Optional[str] = Query(
            None,
            description="Cohort: 'senior_ug_pg', 'first_year', or 'all'",
        ),
        semester_type: Optional[str] = Query(
            None,
            description="Semester: 'odd' or 'even'",
        ),
        start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    ):
        """List major academic milestones including examinations, class committee meetings, feedback, and commencements."""
        return service.get_academic_milestones(
            category=category,
            cohort=cohort,
            semester_type=semester_type,
            start_date=start_date,
            end_date=end_date,
        )

    @app.get(
        "/api/v1/upcoming",
        response_model=List[CalendarDayEntry],
        summary="Get Upcoming Events & Milestones",
        tags=["Events & Search"],
    )
    def get_upcoming_events(
        reference_date: Optional[str] = Query(
            None,
            description="Reference date (YYYY-MM-DD). Defaults to current date or start of calendar.",
            examples=["2026-06-01"],
        ),
        days_ahead: Optional[int] = Query(None, ge=1, le=365, description="Lookahead window in days"),
        cohort: Optional[str] = Query(None, description="Cohort filter ('senior_ug_pg' or 'first_year')"),
        limit: int = Query(10, ge=1, le=50, description="Max upcoming events"),
    ):
        """Get the next upcoming events and holidays starting from a reference date."""
        return service.get_upcoming_events(
            reference_date=reference_date,
            limit=limit,
            days_ahead=days_ahead,
            cohort=cohort,
        )

    @app.get(
        "/api/v1/stats/class-days",
        response_model=ClassDayCountResult,
        summary="Count Instructional and Working Days",
        tags=["Milestones & Stats"],
    )
    def count_class_days(
        start_date: str = Query(..., description="Start date (YYYY-MM-DD)", examples=["2026-06-10"]),
        end_date: str = Query(..., description="End date (YYYY-MM-DD)", examples=["2026-10-16"]),
        cohort: str = Query(
            "senior_ug_pg",
            description="Cohort: 'senior_ug_pg', 'first_year', or 'all'",
            examples=["senior_ug_pg"],
        ),
    ):
        """Calculate total working days, holidays, vacation days, and instructional class days in a given date range."""
        return service.calculate_class_days(start_date=start_date, end_date=end_date, cohort=cohort)

    @app.get(
        "/api/v1/export/full",
        summary="Export Full Calendar Raw JSON",
        tags=["System & Spec"],
    )
    def export_full_calendar():
        """Export the complete raw academic calendar dataset."""
        return service.get_full_calendar()

    @app.get(
        "/openapi.yaml",
        summary="Export OpenAPI Specification in YAML Format",
        tags=["System & Spec"],
    )
    def get_openapi_yaml():
        """Returns the OpenAPI specification in YAML format for tooling compatibility."""
        schema = app.openapi()
        yaml_content = yaml.dump(schema, sort_keys=False)
        return Response(content=yaml_content, media_type="application/x-yaml")

    @app.get(
        "/health",
        summary="Health Check",
        tags=["System & Spec"],
    )
    def health_check():
        """Returns service health and dataset status."""
        return {
            "status": "healthy",
            "institution": service.get_metadata().institution,
            "academic_year": service.get_metadata().academic_year,
            "total_calendar_days": service.get_metadata().total_days,
            "mcp_enabled": True,
            "openapi_version": "3.1.0",
        }

    return app

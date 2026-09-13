"""
Calendar Data Service for Amrita Vishwa Vidyapeetham, Chennai Academic Calendar AY2026-27.
Provides indexed and categorized access to calendar entries, milestones, holidays, and class days.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class CalendarMetadata(BaseModel):
    institution: str = Field(..., description="Institution name")
    document_title: str = Field(..., description="Official document title")
    version: str = Field(..., description="Document revision version")
    academic_year: str = Field(..., description="Academic year (e.g., 2026-27)")
    prepared_by: str = Field(..., description="Campus Timetable Coordinator")
    approved_by: str = Field(..., description="Principal / Approving authority")
    note: str = Field(..., description="Official administrative note")
    legend: Dict[str, str] = Field(..., description="Legend of status codes")
    columns_in_source: List[str] = Field(..., description="Columns present in source table")
    total_days: int = Field(..., description="Total calendar entries count")
    start_date: str = Field(..., description="First date in calendar (YYYY-MM-DD)")
    end_date: str = Field(..., description="Last date in calendar (YYYY-MM-DD)")


class CalendarDayEntry(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    day: str = Field(..., description="Day of week abbreviated (Mon, Tue, Wed, Thu, Fri, Sat, Sun)")
    status: Optional[str] = Field(None, description="Raw status code: 'W' (Working for Staff), 'CD' (Working for Staff & Students), 'H' (Holiday), or None")
    status_description: str = Field(..., description="Human-readable explanation of status")
    is_holiday: bool = Field(..., description="True if marked as Holiday (H)")
    is_working_day: bool = Field(..., description="True if marked as Working Day (W or CD)")
    senior_class_day: Optional[str] = Field(None, description="Class Day number for II, III, IV Year UG and II Year PG (e.g. CD01)")
    first_year_class_day: Optional[str] = Field(None, description="Class Day number for I Year UG and I Year PG (e.g. CD01)")
    details: Optional[str] = Field(None, description="Official events, holiday names, exam notices, or meeting schedules")
    event_type: str = Field(..., description="Categorized event type: holiday, exam, practical_exam, commencement, feedback, committee_meeting, timetable_swap, non_instructional, regular")
    special_timetable: Optional[str] = Field(None, description="If a swapped day timetable is followed (e.g. 'Monday TT', 'Friday TT')")


class MilestoneEntry(BaseModel):
    date: str = Field(..., description="Milestone date (YYYY-MM-DD)")
    day: str = Field(..., description="Day of week")
    category: str = Field(..., description="Category: commencement, midterm_exam, practical_exam, end_semester_exam, faculty_feedback, committee_meeting, last_instruction_day")
    cohort: str = Field(..., description="Affected cohort: senior_ug_pg, first_year, or all")
    semester_type: str = Field(..., description="Semester type: odd, even, or both")
    details: str = Field(..., description="Event details description")
    senior_cd: Optional[str] = None
    first_year_cd: Optional[str] = None


class ClassDayCountResult(BaseModel):
    start_date: str
    end_date: str
    total_calendar_days: int
    working_days_count: int
    holidays_count: int
    vacation_or_unassigned_days_count: int
    senior_instructional_days: int
    first_year_instructional_days: int
    instructional_saturdays_count: int
    cohort_requested: str
    instructional_days_for_cohort: int


class CalendarService:
    """Service to load, index, and query the academic calendar."""

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            # Look in the same directory as this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, "AVV_Chennai_Academic_Calendar_AY2026-27.json")

        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Calendar JSON data file not found at: {data_path}")

        with open(data_path, "r", encoding="utf-8") as f:
            self._raw_data: Dict[str, Any] = json.load(f)

        self._metadata = self._parse_metadata()
        self._entries: List[CalendarDayEntry] = []
        self._by_date: Dict[str, CalendarDayEntry] = {}
        self._by_month: Dict[str, List[CalendarDayEntry]] = {}
        self._holidays: List[CalendarDayEntry] = []
        self._milestones: List[MilestoneEntry] = []
        self._timetable_swaps: List[CalendarDayEntry] = []

        self._process_calendar_entries()
        self._extract_milestones()

    def _parse_metadata(self) -> CalendarMetadata:
        cal = self._raw_data.get("calendar", [])
        start = cal[0]["date"] if cal else ""
        end = cal[-1]["date"] if cal else ""
        return CalendarMetadata(
            institution=self._raw_data.get("institution", "Amrita Vishwa Vidyapeetham, Chennai"),
            document_title=self._raw_data.get("document_title", "Academic Calendar"),
            version=self._raw_data.get("version", "V2.0"),
            academic_year=self._raw_data.get("academic_year", "2026-27"),
            prepared_by=self._raw_data.get("prepared_by", "Dr. Ganesh Kumar C, Campus Timetable Coordinator"),
            approved_by=self._raw_data.get("approved_by", "Dr. V. Jayakumar, Principal"),
            note=self._raw_data.get("note", "The proposed calendar is subject to change, possibly due to administrative needs or unforeseen factors"),
            legend=self._raw_data.get("legend", {}),
            columns_in_source=self._raw_data.get("columns_in_source", []),
            total_days=len(cal),
            start_date=start,
            end_date=end,
        )

    def _classify_event(self, status: Optional[str], details: Optional[str]) -> tuple[str, Optional[str]]:
        """Classify event type and extract timetable swap if present."""
        if not details:
            if status == "H":
                return "holiday", None
            return "regular", None

        d_lower = details.lower()

        # Timetable swap detection: e.g. "Instructional Day (Monday TT)"
        tt_match = re.search(r"\(([A-Za-z]+)\s+TT\)", details)
        special_tt = f"{tt_match.group(1)} TT" if tt_match else None

        if "holiday" in d_lower:
            return "holiday", special_tt
        elif "end semester exam" in d_lower and "practical" in d_lower:
            return "practical_exam", special_tt
        elif "end semester exam" in d_lower:
            return "end_semester_exam", special_tt
        elif "midterm exam" in d_lower or "missed midterm" in d_lower:
            return "midterm_exam", special_tt
        elif "class committee meeting" in d_lower:
            return "committee_meeting", special_tt
        elif "faculty feedback" in d_lower:
            return "feedback", special_tt
        elif "last instruction day" in d_lower:
            return "last_instruction_day", special_tt
        elif "commencement of" in d_lower:
            return "commencement", special_tt
        elif "non-instructional day" in d_lower:
            return "non_instructional", special_tt
        elif special_tt or "instructional day" in d_lower:
            return "timetable_swap", special_tt
        else:
            return "general", special_tt

    def _process_calendar_entries(self) -> None:
        legend = self._raw_data.get("legend", {})
        for item in self._raw_data.get("calendar", []):
            dt = item.get("date")
            day = item.get("day")
            status = item.get("status")
            senior_cd = item.get("ii_iii_iv_year_ug_and_ii_year_pg")
            first_year_cd = item.get("i_year_ug_and_i_year_pg")
            details = item.get("details")

            if status:
                desc = legend.get(status, f"Status {status}")
            else:
                desc = "Vacation / Administrative Break / Non-scheduled Day"

            is_h = (status == "H")
            is_w = (status in ("W", "CD"))

            event_type, special_tt = self._classify_event(status, details)

            entry = CalendarDayEntry(
                date=dt,
                day=day,
                status=status,
                status_description=desc,
                is_holiday=is_h,
                is_working_day=is_w,
                senior_class_day=senior_cd,
                first_year_class_day=first_year_cd,
                details=details,
                event_type=event_type,
                special_timetable=special_tt,
            )

            self._entries.append(entry)
            self._by_date[dt] = entry

            # Group by year-month: "2026-06"
            ym = dt[:7]
            self._by_month.setdefault(ym, []).append(entry)

            if is_h:
                self._holidays.append(entry)

            if special_tt:
                self._timetable_swaps.append(entry)

    def _extract_milestones(self) -> None:
        for entry in self._entries:
            d = entry.details
            if not d:
                continue
            d_lower = d.lower()

            # Determine cohort
            cohort = "all"
            if "i sem ug" in d_lower or "ii sem ug" in d_lower or "i year ug" in d_lower:
                if "iii" in d_lower or "iv" in d_lower or "v" in d_lower or "vii" in d_lower:
                    cohort = "all"
                else:
                    cohort = "first_year"
            elif any(x in d_lower for x in ["iii", "iv", "v", "vi", "vii", "viii"]):
                cohort = "senior_ug_pg"

            # Determine semester type (odd vs even)
            sem_type = "odd"
            if any(x in d_lower for x in ["ii sem", "iv sem", "vi sem", "viii sem", "iv, vi", "ii, iv"]):
                sem_type = "even"
            elif any(x in d_lower for x in ["i sem", "iii sem", "v sem", "vii sem", "iii, v"]):
                sem_type = "odd"

            cat = None
            if "practical exam" in d_lower:
                cat = "practical_exam"
            elif "end semester exam" in d_lower:
                cat = "end_semester_exam"
            elif "midterm exam" in d_lower or "missed midterm" in d_lower:
                cat = "midterm_exam"
            elif "faculty feedback" in d_lower:
                cat = "faculty_feedback"
            elif "class committee meeting" in d_lower:
                cat = "committee_meeting"
            elif "last instruction day" in d_lower:
                cat = "last_instruction_day"
            elif "commencement of" in d_lower:
                cat = "commencement"

            if cat:
                self._milestones.append(
                    MilestoneEntry(
                        date=entry.date,
                        day=entry.day,
                        category=cat,
                        cohort=cohort,
                        semester_type=sem_type,
                        details=d,
                        senior_cd=entry.senior_class_day,
                        first_year_cd=entry.first_year_class_day,
                    )
                )

    # --- Query Methods ---

    def get_metadata(self) -> CalendarMetadata:
        """Get full metadata of academic calendar."""
        return self._metadata

    def get_date(self, date_str: str) -> Optional[CalendarDayEntry]:
        """
        Get entry for a specific date string (YYYY-MM-DD).
        Supports relative words 'today', 'tomorrow', 'yesterday' based on current date.
        """
        date_str = date_str.strip()
        lower = date_str.lower()
        if lower == "today":
            target = date.today().isoformat()
        elif lower == "tomorrow":
            target = (date.today() + timedelta(days=1)).isoformat()
        elif lower == "yesterday":
            target = (date.today() - timedelta(days=1)).isoformat()
        else:
            target = date_str

        return self._by_date.get(target)

    def query_dates(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        cohort: Optional[str] = None,
        event_type: Optional[str] = None,
        has_details: Optional[bool] = None,
        search_term: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CalendarDayEntry]:
        """
        Query calendar entries by range, status, cohort, event type, or keyword search.
        """
        results: List[CalendarDayEntry] = []
        for e in self._entries:
            if start_date and e.date < start_date:
                continue
            if end_date and e.date > end_date:
                continue
            if status and e.status != status:
                continue
            if event_type and e.event_type != event_type:
                continue
            if has_details is True and not e.details:
                continue
            if has_details is False and e.details:
                continue

            if cohort:
                c_clean = cohort.lower()
                if c_clean in ("senior", "senior_ug_pg", "senior_years", "higher_years"):
                    if not e.senior_class_day:
                        continue
                elif c_clean in ("first_year", "first_years", "freshers", "i_year"):
                    if not e.first_year_class_day:
                        continue

            if search_term:
                term = search_term.lower()
                match = (
                    (e.details and term in e.details.lower())
                    or (e.senior_class_day and term in e.senior_class_day.lower())
                    or (e.first_year_class_day and term in e.first_year_class_day.lower())
                    or (term in e.date)
                    or (term in e.day.lower())
                )
                if not match:
                    continue

            results.append(e)

        return results[offset : offset + limit]

    def search_events(
        self,
        query: str,
        cohort: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[CalendarDayEntry]:
        """Search calendar events with keyword."""
        return self.query_dates(search_term=query, cohort=cohort, status=status, limit=limit)

    def get_holidays(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[str] = None,
        named_only: bool = False,
        limit: int = 100,
    ) -> List[CalendarDayEntry]:
        """
        Get holidays. If named_only is True, filters out standard Sunday/Saturday 'Holiday' entries
        and returns named festival and commemorative holidays (e.g. Deepavali, Pongal, Muharram).
        """
        results: List[CalendarDayEntry] = []
        for h in self._holidays:
            if start_date and h.date < start_date:
                continue
            if end_date and h.date > end_date:
                continue
            if month and not h.date.startswith(month):
                continue
            if named_only:
                # Named holidays have details beyond just "Holiday"
                if not h.details or h.details.strip() == "Holiday":
                    continue
            results.append(h)

        return results[:limit]

    def get_academic_milestones(
        self,
        category: Optional[str] = None,
        cohort: Optional[str] = None,
        semester_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[MilestoneEntry]:
        """
        Get key academic milestones (commencements, exams, feedbacks, committee meetings).
        """
        results: List[MilestoneEntry] = []
        for m in self._milestones:
            if category and m.category != category:
                continue
            if cohort and m.cohort != "all" and m.cohort != cohort:
                continue
            if semester_type and m.semester_type != "both" and m.semester_type != semester_type:
                continue
            if start_date and m.date < start_date:
                continue
            if end_date and m.date > end_date:
                continue
            results.append(m)
        return results

    def get_upcoming_events(
        self,
        reference_date: Optional[str] = None,
        limit: int = 10,
        days_ahead: Optional[int] = None,
        cohort: Optional[str] = None,
    ) -> List[CalendarDayEntry]:
        """
        Get upcoming events and holidays starting from a reference date.
        If reference_date is None, defaults to current date (or first calendar date if before).
        """
        if not reference_date:
            today_iso = date.today().isoformat()
            if today_iso < self._metadata.start_date:
                ref = self._metadata.start_date
            elif today_iso > self._metadata.end_date:
                ref = self._metadata.start_date
            else:
                ref = today_iso
        else:
            ref = reference_date

        end_limit = None
        if days_ahead:
            try:
                ref_dt = datetime.strptime(ref, "%Y-%m-%d").date()
                end_limit = (ref_dt + timedelta(days=days_ahead)).isoformat()
            except ValueError:
                pass

        results: List[CalendarDayEntry] = []
        for e in self._entries:
            if e.date < ref:
                continue
            if end_limit and e.date > end_limit:
                break
            # Only include entries with significant details or non-weekend holidays
            if e.details or (e.status == "H" and e.day not in ("Sat", "Sun")):
                if cohort:
                    c = cohort.lower()
                    if c in ("senior", "senior_ug_pg") and not e.senior_class_day and not (e.details and "senior" in e.details.lower()):
                        continue
                    if c in ("first_year", "i_year") and not e.first_year_class_day and not (e.details and "i sem" in e.details.lower()):
                        continue
                results.append(e)
                if len(results) >= limit:
                    break

        return results

    def calculate_class_days(
        self,
        start_date: str,
        end_date: str,
        cohort: str = "senior_ug_pg",
    ) -> ClassDayCountResult:
        """
        Calculate total working days, holidays, and instructional class days (CDs)
        between start_date and end_date for a given cohort.
        """
        entries = [e for e in self._entries if start_date <= e.date <= end_date]
        total = len(entries)
        working = sum(1 for e in entries if e.is_working_day)
        holidays = sum(1 for e in entries if e.is_holiday)
        vacation = sum(1 for e in entries if e.status is None)

        senior_cds = sum(1 for e in entries if e.senior_class_day is not None)
        first_year_cds = sum(1 for e in entries if e.first_year_class_day is not None)
        saturday_instructional = sum(1 for e in entries if e.day == "Sat" and e.is_working_day)

        c = cohort.lower()
        if c in ("first_year", "i_year", "i_year_ug_and_i_year_pg"):
            cohort_req = "first_year"
            cohort_cd = first_year_cds
        elif c in ("all", "both"):
            cohort_req = "all"
            cohort_cd = max(senior_cds, first_year_cds)
        else:
            cohort_req = "senior_ug_pg"
            cohort_cd = senior_cds

        return ClassDayCountResult(
            start_date=start_date,
            end_date=end_date,
            total_calendar_days=total,
            working_days_count=working,
            holidays_count=holidays,
            vacation_or_unassigned_days_count=vacation,
            senior_instructional_days=senior_cds,
            first_year_instructional_days=first_year_cds,
            instructional_saturdays_count=saturday_instructional,
            cohort_requested=cohort_req,
            instructional_days_for_cohort=cohort_cd,
        )

    def get_timetable_swaps(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[CalendarDayEntry]:
        """
        Retrieve all days where a special day timetable is applied (e.g. Saturday working as Monday TT).
        """
        results: List[CalendarDayEntry] = []
        for e in self._timetable_swaps:
            if start_date and e.date < start_date:
                continue
            if end_date and e.date > end_date:
                continue
            results.append(e)
        return results

    def get_full_calendar(self) -> Dict[str, Any]:
        """Returns the complete raw calendar structure."""
        return self._raw_data


# Singleton instance helper
_service_instance: Optional[CalendarService] = None


def get_calendar_service() -> CalendarService:
    global _service_instance
    if _service_instance is None:
        _service_instance = CalendarService()
    return _service_instance

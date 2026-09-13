# Amrita Vishwa Vidyapeetham (Chennai) Academic Calendar MCP Server & OpenAPI REST API

An **OpenAPI 3.1 compatible Model Context Protocol (MCP) Server** and REST API for the **Amrita Vishwa Vidyapeetham, Chennai Campus Academic Calendar (AY 2026-27)**.

Designed specifically for LLMs (Claude, GPT, Gemini, Cursor, Cline, Antigravity) to query academic schedules, examination dates, class days (CD01..CD90), holidays, faculty feedback sessions, class committee meetings, and timetable swaps.

---

## 🎯 Key Features

1. **Dual Compatibility**:
   - **MCP Protocol**: Native support for tools, resources, and prompt templates over **stdio** and **SSE** transports via FastMCP.
   - **OpenAPI 3.1 REST API**: Complete FastAPI service providing Swagger UI (`/docs`), ReDoc (`/redoc`), OpenAPI JSON (`/openapi.json`), and OpenAPI YAML (`/openapi.yaml`).
2. **Comprehensive Academic Dataset**:
   - Covers all 374 days of Academic Year 2026-27 (June 1, 2026 – June 9, 2027).
   - Tracks separate cohorts:
     - **Senior UG/PG**: Semesters III, IV, V, VI, VII, VIII UG and Sem III, IV PG.
     - **First Year UG/PG**: Semesters I and II UG and PG.
   - Class Day progression from **CD01 to CD90** for each semester.
   - Special Saturday timetable replacements (e.g., *Saturday working with Monday Timetable*).
   - Categorized academic milestones: Commencements, Midterms, Missed Midterms, Practical Exams, End Semester Theory Exams, Faculty Feedbacks, and Class Committee Meetings.
3. **OpenAPI Schema Access for LLMs**:
   - LLM agents can query `get_openapi_specification` dynamically or fetch `/openapi.json` directly to discover all endpoints and data schemas.

---

## 📁 Repository Structure

```
.
├── AVV_Chennai_Academic_Calendar_AY2026-27.json  # Raw academic calendar source dataset
├── calendar_service.py                          # Data indexing, search & calculation engine
├── fastapi_app.py                               # FastAPI app implementing OpenAPI 3.1 REST endpoints
├── mcp_server.py                                # FastMCP server with tools, resources & prompts
├── server.py                                    # Unified CLI entry point (stdio / HTTP / export)
├── openapi.json                                 # Pre-generated OpenAPI 3.1 JSON specification
├── openapi.yaml                                 # Pre-generated OpenAPI 3.1 YAML specification
├── mcp_config.json                              # Example MCP client configuration
├── test_server.py                               # 21 pytest & integration tests
└── README.md                                    # Documentation
```

---

## 🚀 How to Run

### 1. Run as MCP Server (Stdio Mode)
Use this mode when connecting from **Claude Desktop**, **Cursor**, **Cline**, or any stdio-based MCP client:

```bash
python3 server.py --stdio
```

### 2. Run as Systemd Background Service (Port 8003 - Active)
The server is configured as a persistent systemd service running in HTTP mode on port 8003:

```bash
# Service status
systemctl status academic-calendar.service

# Restart service
systemctl restart academic-calendar.service

# Stop / Start service
systemctl stop academic-calendar.service
systemctl start academic-calendar.service

# View live logs
journalctl -u academic-calendar.service -f
```

- **OpenAPI 3.1 JSON**: [http://localhost:8003/openapi.json](http://localhost:8003/openapi.json)
- **OpenAPI 3.1 YAML**: [http://localhost:8003/openapi.yaml](http://localhost:8003/openapi.yaml)
- **Interactive Swagger UI**: [http://localhost:8003/docs](http://localhost:8003/docs)
- **ReDoc UI**: [http://localhost:8003/redoc](http://localhost:8003/redoc)
- **MCP SSE Transport**: [http://localhost:8003/sse](http://localhost:8003/sse)
- **Health Check**: [http://localhost:8003/health](http://localhost:8003/health)

### 3. Run Manually via CLI (HTTP & SSE Mode)
```bash
python3 server.py --http --port 8003 --host 0.0.0.0
```

### 4. Re-export OpenAPI Specifications
Generate fresh `openapi.json` and `openapi.yaml` files:

```bash
python3 server.py --export-openapi
```

---

## 🔌 Connecting to LLM Clients

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json` (located at `~/.config/Claude/claude_desktop_config.json` on Linux or `%APPDATA%/Claude/claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "avv-chennai-academic-calendar": {
      "command": "python3",
      "args": [
        "/home/hirthikbalaji/SocialMedia/ACADEMIC_CALENDER/server.py",
        "--stdio"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Cursor Configuration (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "academic-calendar": {
      "command": "python3 /home/hirthikbalaji/SocialMedia/ACADEMIC_CALENDER/server.py --stdio"
    }
  }
}
```

---

## 🛠️ MCP Tools Reference

| Tool Name | Parameters | Description |
|---|---|---|
| `get_calendar_metadata` | *none* | Returns institution name, academic year, version, approver, legend, and dates. |
| `get_date_details` | `target_date: str` | Lookup day status (W/CD/H), Class Day (CD01..CD90), events, or timetable swaps for any date (e.g. `'2026-06-10'`, `'today'`). |
| `search_calendar` | `query: str`, `cohort?: str`, `status?: str`, `limit?: int` | Full-text search across all event descriptions, dates, and class days. |
| `get_date_range_events` | `start_date: str`, `end_date: str`, `cohort?: str`, `status?: str`, `event_type?: str`, `only_with_details?: bool` | Retrieves chronological schedule for a date range with optional filters. |
| `get_holidays` | `start_date?: str`, `end_date?: str`, `month?: str`, `named_only?: bool` | Lists holidays. Set `named_only=True` to filter out regular weekends and list festival/public holidays (e.g. Deepavali, Pongal). |
| `get_academic_milestones` | `category?: str`, `cohort?: str`, `semester_type?: str` | Retrieves major milestones (`commencement`, `midterm_exam`, `practical_exam`, `end_semester_exam`, `faculty_feedback`, `committee_meeting`, `last_instruction_day`). |
| `get_upcoming_events` | `reference_date?: str`, `limit?: int`, `days_ahead?: int`, `cohort?: str` | Returns upcoming events and milestones starting from a reference date. |
| `count_instructional_days`| `start_date: str`, `end_date: str`, `cohort: str` | Computes working days, holidays, vacation days, and instructional class days (CDs) for attendance calculations. |
| `get_timetable_swaps` | `start_date?: str`, `end_date?: str` | Lists all working Saturdays where an alternate day timetable (e.g. Monday TT) is followed. |
| `get_openapi_specification` | `format: str = 'json'` | Returns full OpenAPI 3.1 specification (JSON or YAML) so the LLM can dynamically inspect all endpoints. |

---

## 📦 MCP Resources & Prompts

### Resources
- `calendar://metadata` - Calendar document information, approval, and legend definitions.
- `calendar://holidays` - Complete list of 23 official named festival and public holidays.
- `calendar://milestones` - All 48 key academic milestones (exams, feedbacks, commencements).
- `calendar://timetable-swaps` - All 19 working Saturdays and special day orders.
- `calendar://full` - The complete raw JSON calendar document.
- `openapi://schema.json` - Complete OpenAPI 3.1 specification for the REST API.

### Prompts
- `academic_advising(cohort, current_date)`: Template guiding an LLM in advising a student on upcoming exams, feedback, and deadlines.
- `holiday_and_leave_inquiry(month)`: Template guiding an LLM in summarizing monthly holidays and long weekends.
- `attendance_and_class_day_counter(cohort, from_date, to_date)`: Template for calculating student attendance and remaining instructional days against the 90 class days requirement.

---

## 🌐 OpenAPI REST Endpoints

All endpoints are documented interactively at `/docs` (Swagger UI):

- `GET /api/v1/metadata` - Get official calendar metadata
- `GET /api/v1/date/{target_date}` - Detailed query for single date
- `GET /api/v1/calendar` - Range and filter query
- `GET /api/v1/search` - Keyword search
- `GET /api/v1/holidays` - List holidays (with `named_only` filter)
- `GET /api/v1/timetable-swaps` - List timetable replacement days
- `GET /api/v1/milestones` - List academic milestones
- `GET /api/v1/upcoming` - List upcoming events
- `GET /api/v1/stats/class-days` - Count instructional class days (CDs) and working days
- `GET /api/v1/export/full` - Full raw JSON data
- `GET /openapi.yaml` - OpenAPI YAML specification
- `GET /health` - Service healthcheck

---

## 🧪 Testing

Run the automated test suite with pytest:

```bash
python3 -m pytest -p no:anyio test_server.py -v
```

All 21 test cases cover metadata validation, single-date lookups, holidays filtering, class day counters, timetable swaps, milestone categorization, FastAPI routes, and FastMCP tool executions.

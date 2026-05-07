# Implementation Plan: UI Enrichment & Task Audit Log

## Objective
Enrich the frontend dashboard with dynamic timeline visualizations and add a comprehensive task audit log to monitor background processing (LLM extractions, sync jobs) in real-time.

## Key Files & Context
- `src/api/routers/system.py` (Backend API for stats and logs)
- `frontend/src/pages/Dashboard.tsx` (Main dashboard UI)
- `frontend/src/pages/Monitoring.tsx` (Current monitoring UI)
- `frontend/src/components/AuditLog.tsx` (New component)
- `frontend/src/components/AuditLog.css` (New styling)

## Proposed Solution
1.  **Backend APIs**: We will expose two new endpoints:
    - `/api/stats/timeline`: Returns a daily breakdown (last 7-14 days) of ingested messages and identified leads to feed a dynamic area chart.
    - `/api/stats/audit-logs`: Returns a paginated list of recent `ExtractionLog` entries (AI processing history) and `SyncState` updates.
2.  **Dashboard Visualizations**: We will replace or augment the static bar charts on the Dashboard with an `AreaChart` from Recharts, showing data growth over time, providing a better "pulse" of the system.
3.  **Audit Log Component**: We will build an `AuditLog` React component that fetches from the new API. It will display a scrollable feed of recent system actions (e.g., "Extracted 2 leads", "Synced 500 messages from Crypto") with success/error indicators and timestamps. This will be integrated into the `Monitoring` page.

## Implementation Steps

### Phase 1: Backend API Development
1.  Modify `src/api/routers/system.py` to add `get_timeline_stats`. This will query the database to group `Message` and `Contact` creation times by day.
2.  Modify `src/api/routers/system.py` to add `get_audit_logs`. This will query the `ExtractionLog` table (joined or unioned with sync states if possible, or just extraction logs for AI audit) and format them for the frontend.

### Phase 2: Frontend Visualizations
1.  Update `frontend/src/pages/Dashboard.tsx` to call `/api/stats/timeline`.
2.  Implement an `AreaChart` using Recharts to visualize the timeline data.

### Phase 3: Audit Log UI
1.  Create `frontend/src/components/AuditLog.tsx`.
2.  Implement a polling mechanism (using SWR) to fetch `/api/stats/audit-logs` every few seconds.
3.  Design the log list with icons (Check/Error), timestamps, and details.
4.  Embed the `AuditLog` component into `frontend/src/pages/Monitoring.tsx` or as a slide-out panel in the Dashboard.

## Verification & Testing
- Start the backend and frontend.
- Verify the Dashboard timeline chart populates correctly.
- Trigger a sync or extraction task and verify the Audit Log updates in near real-time.
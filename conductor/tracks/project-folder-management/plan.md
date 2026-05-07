# Implementation Plan: Project & Folder Management

## Objective
Implement a fully functional UI and backend support for managing Projects (isolated databases) and Folders (logical groups within a database). 

## Scope & Impact
- **Projects:** Users should be able to create, read, update, and delete isolated project environments. Project metadata (name, description) will be stored in a master table within the base `crm` database.
- **Folders:** Existing Folders need an upgrade to support editable descriptions and tagging (keywords).
- **Navigation:** The TopBar will dynamically fetch projects from the backend instead of using a hardcoded list.

## Proposed Solution

### Phase 1: Backend Master Database (Projects)
1.  **Model:** Add a `SystemProject` model to `src/db/models.py`.
    - Columns: `id`, `db_name` (slug), `name`, `description`, `is_active`, `created_at`.
2.  **API:** Create `src/api/routers/projects.py`.
    - `GET /api/projects`: List all from `SystemProject`.
    - `POST /api/projects`: Create `SystemProject`. Crucially, this must call `ensure_database_exists` and `init_database_schema` to physically create the PostgreSQL database.
    - `PATCH /api/projects/{id}`: Update name/description.
    - `DELETE /api/projects/{id}`: Drop database (optional/warn) and remove the `SystemProject` record.
3.  **App Mount:** Register the new router in `src/api/main.py`.

### Phase 2: Folder Model & API Enhancement
1.  **Model:** Update `TrackedFolder` in `src/db/models.py`.
    - Add `tags = Column(ARRAY(String), default=list)` (using PostgreSQL array).
2.  **API:** Update `src/api/routers/tracking.py`.
    - Modify `POST /folders` to accept description and tags.
    - Add `PATCH /folders/{id}` to update name, description, and tags.
3.  **Migration:** We need an Alembic migration script to add the `tags` column to `tracked_folders` across all existing `crm_*` databases.

### Phase 3: Frontend Project Management
1.  **TopBar:** Update `frontend/src/components/TopBar.tsx` to use `useSWR('/api/projects')` instead of the hardcoded `projects` array.
2.  **Projects Page:** Create a new route/page `frontend/src/pages/Projects.tsx`.
    - Display all projects as cards.
    - Add a "Create Project" modal.
    - Add "Edit" and "Delete" actions to project cards.

### Phase 4: Frontend Folder UI
1.  **Tracking Page:** Update `frontend/src/pages/Tracking.tsx`.
    - Add a settings gear or "Edit" button next to folder names.
    - Create a modal or inline form to edit Folder Name, Description, and Tags.
    - Display Tags visually below the folder name.

## Alternatives Considered
- *Using JSON instead of separate databases for Projects.* Rejected because the core architecture relies on database isolation for LLM context separation and privacy.

## Verification
- Create a new project via UI, verify `crm_{slug}` database is physically created via pgAdmin/shell.
- Switch to the new project in TopBar.
- Create a folder with description and tags.
- Run `scripts/migrate_all.py` and ensure the new schema applies correctly.
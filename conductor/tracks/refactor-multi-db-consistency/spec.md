# Track: Refactor: Multi-DB Consistency & Repository Pattern

## Specification
Ensure the system correctly routes database operations to the dynamic `db_name` provided in task arguments and unify the logic for saving messages.

## Objectives
- Implement `MessageRepository` to DRY up message ingestion.
- Remove hardcoded `"crm"` string from all tasks and connectors.
- Ensure engine lifecycle management in `database.py`.

## Success Criteria
- [x] `MessageRepository` handles all message/contact associations.
- [x] Tasks correctly use `db_name` from kwargs.
- [x] No hardcoded `"crm"` references remain in core sync logic.

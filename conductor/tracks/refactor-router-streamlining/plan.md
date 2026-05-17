# Implementation Plan: Router Streamlining

## Goal
Achieve architectural purity in the API layer by delegating all business logic and model-to-response mapping to specialized services.

## Phase 1: Contact Service & Mapper
- [ ] Create `src/services/contact_service.py`.
- [ ] Move `_contact_to_response` into a mapper utility or the service itself.
- [ ] Update `contacts.py` router to use the new service.

## Phase 2: Lead Service
- [ ] Create `src/services/lead_service.py`.
- [ ] Extract lead history enrichment and ranking logic from `leads.py`.
- [ ] Update `leads.py` router to delegate entirely to `LeadService`.

## Phase 3: Validation
- [ ] Verify lead history pagination and enrichment still work.
- [ ] Ensure contact CRUD operations remain consistent.
- [ ] Run API integration tests.
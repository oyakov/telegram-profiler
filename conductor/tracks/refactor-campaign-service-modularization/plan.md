# Implementation Plan: Campaign Service Modularization

## Goal
Improve the flexibility and testability of the campaign system by decoupling delivery and personalization logic.

## Phase 1: Delivery Providers
- [ ] Define `BaseDeliveryProvider` interface.
- [ ] Implement `TelegramDeliveryProvider` (thin wrapper over `TelegramConnector.send_message`).
- [ ] Update `CampaignService` to accept a delivery provider.

## Phase 2: Personalization & Repositories
- [ ] Extract personalization logic (text replacement) into a `Personalizer` utility.
- [ ] Implement `CampaignRepository` and `LeadSearchRepository`.

## Phase 3: Integration
- [ ] Update `CampaignService` methods to use new providers and repositories.
- [ ] Verify campaign execution with mocked delivery providers.
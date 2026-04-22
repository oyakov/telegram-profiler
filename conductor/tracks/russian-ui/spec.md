# Specification: Russian UI Support

## Context
The application currenty uses English as the primary language for the Dashboard UI. To improve usability for the target audience, the interface should be translated into Russian, making it the default and primary language.

## Goals
- Translate all Dashboard pages, labels, buttons, and notifications to Russian.
- Ensure consistent terminology (e.g., "Lead" -> "Лид", "Ad Buyer" -> "Покупатель рекламы").
- Maintain the professional aesthetic of the interface.

## Technical Requirements
- Update `dashboard/app.py` with Russian text.
- Use UTF-8 encoding for all strings.
- Optional: Implement a simple localization helper if multi-language support is needed in the future, but for now, hardcode Russian as the primary language.

## Affected Components
- `dashboard/app.py` (Main UI)
- `src/pipeline/unified_processor.py` (Notes and facts generation, if applicable)

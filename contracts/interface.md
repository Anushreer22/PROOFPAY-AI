# Rules Interface Specification (Person 1 ↔ Person 2)

## Overview
This document specifies the schema, rule definitions, and contract between **Person 1 (Legal & Data Verifier)** and **Person 2 (Agent & Calculator Developer)** for the RecoverPay AI agent system.

## Rule Data Schema
Both `data/rules.json` (production/verified rules) and `agents/stub_rules.json` (local agent development stub) follow the standardized schema:

```json
{
  "rules": [
    {
      "key": "<string>",
      "value": "<any>",
      "unit": "<string | null>",
      "legal_reference": "<string>",
      "source_url": "<string>",
      "date_checked": "<YYYY-MM-DD | null>",
      "verification_status": "<'verified' | 'unverified'>",
      "explanation": "<string>"
    }
  ]
}
```

In `agents/stub_rules.json`, rules contain the core development fields (`key`, `value`, `unit`, `verification_status: "unverified"`) to enable Person 2 to develop and unit-test the eligibility agent and interest calculator offline without relying on production legal confirmations.

## Canonical Rule Keys

| Rule Key | Expected Type | Unit | Default / Legal Value | Verification Status | Source Reference |
|---|---|---|---|---|---|
| `payment_deadline` | `integer` | `days` | `45` | `verified` | MSMED Act 2006, Section 15 |
| `default_period` | `integer` | `days` | `15` | `verified` | MSMED Act 2006, Section 2(b) & Section 15 |
| `deemed_acceptance` | `integer` | `days` | `15` | `verified` | MSMED Act 2006, Section 2(b) Explanation (ii) |
| `interest_multiplier` | `number` | `times_bank_rate` | `3` | `verified` | MSMED Act 2006, Section 16 |
| `interest_compounding` | `string` | `monthly rests` | `"monthly rests"` | `verified` | MSMED Act 2006, Section 16 |
| `enterprise_classification` | `list[string]` | `null` | `["micro", "small"]` | `verified` | MSMED Act 2006, Section 2(n) & S.O. 2119(E) |
| `udyam_requirement` | `boolean` | `null` | `true` | `verified` | MSMED Act 2006, Sections 2(n) & 8(1) |
| `registration_timing` | `string` | `null` | `"predates_supply"` | `verified` | Silpi Industries v. KSRTC (Supreme Court 2021) |
| `rbi_bank_rate` | `number` | `percent_per_annum` | `5.75` | `verified` | RBI Bank Rate (Section 49 RBI Act) |
| `eligible_activities` | `list[string]` | `null` | `["manufacturing", "services"]` | **`unverified`** | MSME OM 15 Dec 2017 & OM 2 July 2021 |

## Guardrail Protocol
1. **Unverified Status Handling**:
   - `eligible_activities` remains **`unverified`** due to shifting administrative circulars and active judicial debates regarding retail/wholesale trader access to Chapter V delayed payment mechanisms.
   - The eligibility agent (`agents/eligibility_agent.py`) and calculator (`agents/calculator.py`) **must stop** and flag a review warning whenever a required rule is unverified or unresolved.
   - The agent must never produce an authoritative calculation or claim filing when an unverified statutory prerequisite is detected.


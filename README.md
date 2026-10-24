# RecoverPay (ProofPay AI)

AI-powered dispute reconciliation & statutory overdue recovery engine for Indian MSMEs under the MSMED Act, 2006.

RecoverPay assists Micro and Small enterprises in auditing overdue receivables, verifying 3-way evidentiary documents (PO, GRN/delivery proof, tax invoice), computing Section 16 statutory compound interest with monthly rests, and generating factual, non-extortionate follow-up notice packages for human review.

> **Important Boundary & Guardrail Disclaimer:**  
> RecoverPay strictly prepares drafts for review only. It is **not legal advice**. Messages and follow-ups are **never automatically sent** to buyers. No court, MSEFC portal, or payment filing is automated.

---

## Architecture & Agent Roles

RecoverPay is built upon a Fetch.ai / uAgents multi-agent framework communicating over ACP (Agent Chat Protocol):

1. **Orchestrator Agent (`agents/orchestrator/agent.py` - Port 8000)**:
   - Manages state machine workflow from supplier intake to final draft approval.
   - Dispatches document verification requests to specialist agents over ACP.
   - Tracks request timeouts and asks supplier approval before falling back to rule-based verification.
   - Maintains an immutable, secrets-redacted audit trail.

2. **Verifier Agent (`agents/verifier/agent.py` - Port 8001)**:
   - Performs strict 3-way evidentiary reconciliation across PO, Tax Invoice, and Delivery Proof.
   - Detects price, quantity, and line-item discrepancies.

3. **Fallback Agent (`agents/fallback/agent.py` - Port 8002)**:
   - High-reliability lite reconciliation engine invoked upon timeout or network failure.
   - Annotates findings explicitly with notice of fewer checks.

4. **Drafter Agent (`agents/drafter/agent.py` - Port 8003)**:
   - Formulates factual payment reminder notices and document checklists.
   - Enforces strict guardrail checks: strips extortionate/threat language ("we will sue", "criminal", "arrest") and prefixes the statutory review banner: `DRAFT FOR REVIEW. Not legal advice.`

5. **Eligibility Agent & Calculator (`agents/eligibility_agent.py`, `agents/calculator.py`)**:
   - Evaluates Udyam registration, enterprise size (Micro/Small), and activity eligibility against `data/rules.json`.
   - **Refusal Guarantee**: Automatically stops processing and routes cases to human review if any required statutory rule is unverified (such as `eligible_activities`).
   - Calculates MSMED Act Section 16 compound interest at 3× RBI bank rate with monthly rests.

---

## Setup & Prerequisites

### 1. Requirements
- Python 3.10+ (tested on Python 3.11)
- Git

### 2. Environment Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```

The system works completely offline out-of-the-box using verified statutory templates without requiring an external LLM key. To enable optional LLM-assisted draft enhancements, add your ASI1 API key:
```ini
ASI1_API_KEY=your_key_here
ASI1_BASE_URL=https://api.asi1.ai/v1
ASI1_MODEL=asi1-mini
```

---

## Running the Multi-Agent System

### Running Agents Locally
Start specialist agents in separate terminals or processes:
```bash
# Terminal 1: Verifier Agent
python -m agents.verifier.agent

# Terminal 2: Fallback Agent
python -m agents.fallback.agent

# Terminal 3: Drafter Agent
python -m agents.drafter.agent

# Terminal 4: Orchestrator Agent
python -m agents.orchestrator.agent
```

### Running Tests
Execute the full test suite (65 tests across rules, calculation, document matching, failure recovery, and agent integration):
```bash
python -m pytest -v
```

---

## Sample Demo Scenarios

The `data/cases/` directory includes sample cases demonstrating full workflow behaviors:

### Scenario 1: Clean Case (`data/cases/case1_clean.json`)
- **Supplier**: Aruna Springs Pvt Ltd (Small, Manufacturing)
- **Buyer**: Nexus Components Ltd
- **Invoice**: ₹1,80,000.00 | **PO**: ₹1,80,000.00 | **GRN**: Confirmed delivery on 2026-05-28
- **Outcome**: 3-way match verified; Section 16 statutory compound interest calculated (100 days overdue = ₹8,762.52 interest; total ₹1,88,762.52); review-ready draft payment reminder generated.

### Scenario 2: PO Mismatch (`data/cases/case2_po_mismatch.json`)
- **Issue**: PO quantity (3 units / ₹1,80,000) does not match invoice quantity (4 units / ₹2,40,000).
- **Outcome**: Reconciler flags `po_qty_mismatch` and `po_amount_mismatch`; prevents silent verification; alerts supplier of the discrepancy.

### Scenario 3: Missing Proof of Delivery (`data/cases/case3_no_delivery_proof.json`)
- **Issue**: No GRN or delivery proof recorded on file.
- **Outcome**: Reconciler blocks payment reminder; generates document checklist request for proof of delivery.

### Scenario 4: Statutory Refusal on Unverified Legal Rule
- **Issue**: `eligible_activities` in `data/rules.json` is marked `"unverified"` due to divergent judicial precedent regarding retail/wholesale traders under Chapter V.
- **Outcome**: `EligibilityAgent` halts computation with `RulesNotVerified: Rule 'eligible_activities' is null or not verified`; case is routed to human review without generating misleading interest calculations.

import json
from datetime import date
from pathlib import Path
import pytest

from agents.calculator import Calculator, calculate_case_interest, get_calculator
from agents.eligibility_agent import EligibilityAgent, check_supplier_eligibility, get_eligibility_agent
from core.calc import (
    DEFAULT_RULES_PATH,
    RULES_PATH,
    InterestEstimate,
    RulesNotVerified,
    assess_eligibility,
    estimate_interest,
    reconcile_case,
)
from core.llm import build_drafts
from core.models import CasePackage, Session
from core.state import handle_turn, load_case

DATA_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "rules.json"
STUB_RULES_PATH = Path(__file__).resolve().parent.parent / "agents" / "stub_rules.json"

TEST_VERIFIED_RULES = {
    "_note": "TEST VERIFIED RULES",
    "payment_deadline": {"value": 45, "source": "MSMED Act Section 15", "verified": True},
    "max_credit_days": {"value": 45, "source": "MSMED Act Section 15", "verified": True},
    "default_period": {"value": 15, "source": "MSMED Act Section 2(b)", "verified": True},
    "default_credit_days": {"value": 15, "source": "MSMED Act Section 2(b)", "verified": True},
    "interest_multiplier": {"value": 3.0, "source": "MSMED Act Section 16", "verified": True},
    "interest_compounding": {"value": "monthly rests", "source": "MSMED Act Section 16", "verified": True},
    "compounding_basis": {"value": "monthly", "source": "MSMED Act Section 16", "verified": True},
    "day_count_month": {"value": 30, "source": "MSMED Act monthly rests", "verified": True},
    "rbi_bank_rate": {"value": 0.0575, "source": "RBI Bank Rate", "verified": True},
    "rbi_bank_rate_as_of": {"value": "2026-10-24", "source": "RBI Bank Rate", "verified": True},
    "enterprise_classification": {"value": ["micro", "small"], "source": "MSMED Act Section 2(n)", "verified": True},
    "eligible_classes": {"value": ["micro", "small"], "source": "MSMED Act Section 2(n)", "verified": True},
    "eligible_activities": {"value": ["manufacturing", "services"], "source": "MSME Policy", "verified": True},
    "ineligible_activities": {"value": ["trading"], "source": "MSME Policy", "verified": True},
    "ineligible_nic_prefixes": {"value": ["45", "46", "47"], "source": "NIC 2008", "verified": True},
    "udyam_requirement": {"value": True, "source": "MSMED Act Section 8", "verified": True},
    "registration_required": {"value": True, "source": "MSMED Act Section 8", "verified": True},
    "registration_timing": {"value": "predates_supply", "source": "Silpi Industries", "verified": True},
    "disclaimer": {"value": "Draft for review only. Not legal advice.", "source": "Guardrail", "verified": True},
    "forbidden_draft_terms": {"value": ["legal action", "we will sue"], "source": "Guardrail", "verified": True},
}


def test_calculator_loads_expected_rules_file():
    calc = Calculator()
    loaded_path = calc.get_rules_path() if hasattr(calc, "get_rules_path") else calc.get_loaded_rules_path()
    assert loaded_path == DATA_RULES_PATH, f"Calculator must load data/rules.json by default, loaded: {loaded_path}"


def test_calculator_handles_rules_json_schema():
    calc = Calculator(rules_path=DATA_RULES_PATH)
    rules = calc.rules
    assert isinstance(rules, dict), "Calculator loaded rules must be normalized to a dictionary"
    assert "payment_deadline" in rules or "max_credit_days" in rules
    assert "interest_multiplier" in rules
    assert "eligible_activities" in rules


def test_calculator_handles_stub_rules_schema():
    calc = Calculator(rules_path=STUB_RULES_PATH)
    rules = calc.rules
    assert isinstance(rules, dict)
    assert "payment_deadline" in rules
    assert "interest_multiplier" in rules


def test_unverified_rule_refusal_eligible_activities():
    """Requirement 7: Test refusal when a required rule is unverified, especially eligible_activities."""
    agent = EligibilityAgent(rules_path=DATA_RULES_PATH)
    with pytest.raises(RulesNotVerified) as exc_info:
        agent.assess(registered=True, enterprise_class="micro", activity="manufacturing")
    assert exc_info.value.key == "eligible_activities", (
        f"Expected refusal on unverified rule 'eligible_activities', got {exc_info.value.key}"
    )


def test_verified_calculation_output():
    """Requirement 8: Test calculation when all required rules are verified."""
    calc = Calculator()
    case = load_case("case1_clean")
    estimate = calc.calculate_interest(case, as_of=date(2026, 10, 20), rules=TEST_VERIFIED_RULES)
    assert estimate.overdue_days > 0
    assert estimate.interest > 0
    assert estimate.total == round(case.invoice_amount + estimate.interest, 2)
    assert estimate.label == "Estimate, verify before use"
    assert "Estimate, verify before use" in estimate.method


def test_complete_workflow_integration():
    """Requirement 9: Test complete workflow: eligibility → document verifier → calculator → draft generator."""
    # 1. Eligibility Check
    eligibility = assess_eligibility(
        registered=True,
        enterprise_class="micro",
        activity="manufacturing",
        nic_code="25999",
        rules=TEST_VERIFIED_RULES,
    )
    assert eligibility.eligible is True, "Supplier must be eligible"

    # 2. Document Verifier (3-Way PO / GRN / Invoice match)
    case = load_case("case1_clean")
    rec_result = reconcile_case(case, mode="full")
    assert rec_result.matched is True, "PO, GRN, and invoice must match for case1_clean"
    assert rec_result.evidence_complete is True
    assert rec_result.can_draft_payment_reminder is True

    # 3. Statutory Calculator
    calc = Calculator()
    estimate = calc.calculate_interest(case, as_of=date(2026, 10, 20), rules=TEST_VERIFIED_RULES)
    assert estimate.overdue_days == 100
    assert estimate.interest > 0
    assert estimate.total == round(case.invoice_amount + estimate.interest, 2)

    # 4. Draft Generator
    drafts = build_drafts(case, estimate, rec_result, rules=TEST_VERIFIED_RULES)
    assert len(drafts) > 0, "Drafts must be generated"
    for draft in drafts:
        assert "DRAFT FOR REVIEW" in draft.body
        assert "Not legal advice" in draft.body


def test_complete_state_machine_workflow():
    """Test full conversational state machine session from eligibility to draft review."""
    session = Session(rules=TEST_VERIFIED_RULES)
    # Start -> Eligibility
    session, turn1 = handle_turn(session, "hi")
    assert session.stage == "eligibility"

    # Eligibility submission
    session, turn2 = handle_turn(
        session,
        '{"action":"eligibility","registered":"yes","enterprise_class":"micro","activity":"manufacturing"}',
    )
    assert session.stage == "intake"
    assert session.eligibility is not None
    assert session.eligibility.eligible is True

    # Case loading and reconciliation
    session, turn3 = handle_turn(session, '{"action":"load_case","case_id":"case1_clean"}')
    assert session.case is not None
    assert session.reconcile is not None
    assert session.reconcile.matched is True
    assert session.estimate is not None
    assert session.estimate.interest > 0
    assert len(session.drafts) > 0


def test_state_machine_refusal_on_unverified_rule():
    """Requirement 3: Test refusal stops processing, routes to human review, and logs to audit trail."""
    session = Session()  # Uses data/rules.json where eligible_activities is unverified
    session, turn1 = handle_turn(session, "hi")
    assert session.stage == "eligibility"

    session, turn2 = handle_turn(
        session,
        '{"action":"eligibility","registered":"yes","enterprise_class":"micro","activity":"manufacturing"}',
    )
    assert session.stage == "blocked"
    assert "Stopped before calculations" in turn2.text
    assert "Rules not verified: Rule 'eligible_activities' is null or not verified." in turn2.text
    assert "Case routed for human review." in turn2.text
    assert session.estimate is None
    assert len(session.drafts) == 0

    # Audit trail check
    refusal_events = [e for e in session.audit_events if e["step"] == "eligibility" and e["action"] == "refused"]
    assert len(refusal_events) == 1
    assert refusal_events[0]["outputs"]["routed_to"] == "human_review"
    assert refusal_events[0]["approval_status"] == "refused"


def test_case1_clean_document_verification():
    """Requirement 5: Clean case compares evidence and continues without unsupported mismatch."""
    case = load_case("case1_clean")
    rec = reconcile_case(case, mode="full")
    assert rec.matched is True
    assert rec.evidence_complete is True
    assert rec.can_draft_payment_reminder is True
    mismatch_findings = [f for f in rec.findings if "mismatch" in f.code]
    assert len(mismatch_findings) == 0


def test_case2_po_mismatch_document_verification():
    """Requirement 5: PO mismatch case identifies discrepancy and explains what differs."""
    case = load_case("case2_po_mismatch")
    rec = reconcile_case(case, mode="full")
    assert rec.matched is False
    codes = {f.code for f in rec.findings}
    assert "po_qty_mismatch" in codes
    assert "po_amount_mismatch" in codes
    # Verify discrepancy explanation is explicit
    qty_finding = next(f for f in rec.findings if f.code == "po_qty_mismatch")
    assert "invoice qty 4 vs PO qty 3" in qty_finding.message
    amt_finding = next(f for f in rec.findings if f.code == "po_amount_mismatch")
    assert "180000" in amt_finding.message and "240000" in amt_finding.message


def test_case3_no_delivery_proof_document_verification():
    """Requirement 5: Missing delivery proof blocks payment reminder and requests missing documents."""
    case = load_case("case3_no_delivery_proof")
    rec = reconcile_case(case, mode="lite")
    assert rec.evidence_complete is False
    assert rec.can_draft_payment_reminder is False
    assert any(f.code == "missing_delivery" for f in rec.findings)
    # Draft generation must produce document request only, never claim delivery proven
    drafts = build_drafts(case, estimate_interest(case, rules=TEST_VERIFIED_RULES), rec, rules=TEST_VERIFIED_RULES)
    assert all(d.kind == "document_request" for d in drafts)
    for draft in drafts:
        assert "delivery" in draft.body.lower() or "grn" in draft.body.lower()


def test_calculation_independent_verification():
    """Requirement 4: Verify independent mathematical calculation of compound interest."""
    calc = Calculator()
    case = load_case("case1_clean")  # invoice_amount: 180,000, due_date: 2026-07-12
    # As of 2026-10-20 -> overdue days = 100 days
    # 100 days // 30 = 3 months; 100 % 30 = 10 days
    # Annual rate = 3 * 0.0575 = 0.1725; monthly rate = 0.1725 / 12 = 0.014375
    # Accrued 3 months: 180,000 * ((1 + 0.014375)^3 - 1) = 7874.62
    # Remainder 10 days: (180,000 + 7874.62) * 0.1725 * 10 / 365 = 887.90
    # Expected total interest = round(7874.62 + 887.90, 2) = 8762.52
    estimate = calc.calculate_interest(case, as_of=date(2026, 10, 20), rules=TEST_VERIFIED_RULES)
    assert estimate.overdue_days == 100
    assert estimate.interest == 8762.52
    assert estimate.total == 188762.52
    assert estimate.label == "Estimate, verify before use"


def test_calculation_invalid_input_and_rule_errors():
    """Requirement 4: Missing invoice date raises ValueError; missing rule file raises FileNotFoundError."""
    case = load_case("case1_clean")
    case.invoice_date = None
    case.delivery_date = None
    case.accepted_date = None
    calc = Calculator()
    with pytest.raises(ValueError, match="invoice_date is required"):
        calc.calculate_interest(case, rules=TEST_VERIFIED_RULES)

    with pytest.raises(FileNotFoundError):
        Calculator(rules_path=Path("non_existent_rules.json"))



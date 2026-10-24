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


import json
from pathlib import Path
import pytest

DATA_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "rules.json"
STUB_RULES_PATH = Path(__file__).resolve().parent.parent / "agents" / "stub_rules.json"

REQUIRED_KEYS = {
    "payment_deadline",
    "default_period",
    "deemed_acceptance",
    "interest_multiplier",
    "interest_compounding",
    "enterprise_classification",
    "udyam_requirement",
    "registration_timing",
    "rbi_bank_rate",
    "eligible_activities",
}


def test_rules_json_exists_and_valid():
    assert DATA_RULES_PATH.exists(), f"{DATA_RULES_PATH} does not exist"
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "data/rules.json top-level must be an object"
    assert "rules" in data, "data/rules.json must contain a 'rules' key"
    assert isinstance(data["rules"], list), "'rules' must be a list"


def test_stub_rules_json_exists_and_valid():
    assert STUB_RULES_PATH.exists(), f"{STUB_RULES_PATH} does not exist"
    with open(STUB_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "agents/stub_rules.json top-level must be an object"
    assert "rules" in data, "agents/stub_rules.json must contain a 'rules' key"
    assert isinstance(data["rules"], list), "'rules' must be a list"


def test_all_required_keys_present_in_data_rules():
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    keys = {r.get("key") for r in data["rules"]}
    missing = REQUIRED_KEYS - keys
    assert not missing, f"data/rules.json is missing required keys: {missing}"


def test_all_required_keys_present_in_stub_rules():
    with open(STUB_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    keys = {r.get("key") for r in data["rules"]}
    missing = REQUIRED_KEYS - keys
    assert not missing, f"agents/stub_rules.json is missing required keys: {missing}"


def test_key_parity_between_data_and_stub():
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data_keys = [r.get("key") for r in json.load(f)["rules"]]
    with open(STUB_RULES_PATH, "r", encoding="utf-8") as f:
        stub_keys = [r.get("key") for r in json.load(f)["rules"]]
    assert set(data_keys) == set(stub_keys), "Key set in data/rules.json and agents/stub_rules.json must match"


def test_eligible_activities_is_unverified():
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    eligible_act = next((r for r in data["rules"] if r.get("key") == "eligible_activities"), None)
    assert eligible_act is not None, "eligible_activities rule not found"
    assert eligible_act.get("verification_status") == "unverified", (
        "eligible_activities MUST remain 'unverified' until applicable current legal requirements are confirmed"
    )


def test_stub_rules_all_unverified():
    with open(STUB_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for rule in data["rules"]:
        assert rule.get("verification_status") == "unverified", (
            f"Stub rule {rule.get('key')} must have verification_status 'unverified'"
        )


def test_verified_rules_have_official_source_references():
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for rule in data["rules"]:
        status = rule.get("verification_status")
        assert status in ("verified", "unverified"), f"Invalid verification_status '{status}' for {rule.get('key')}"
        if status == "verified":
            assert rule.get("legal_reference"), f"Verified rule '{rule.get('key')}' must have a legal_reference"
            url = rule.get("source_url")
            assert isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")), (
                f"Verified rule '{rule.get('key')}' must have a valid official source_url"
            )
            assert rule.get("date_checked"), f"Verified rule '{rule.get('key')}' must have a date_checked"
            assert rule.get("value") is not None, f"Verified rule '{rule.get('key')}' value must not be None"


def test_statutory_rule_values():
    with open(DATA_RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    rules_by_key = {r["key"]: r for r in data["rules"]}

    # Section 15: max 45 days
    assert rules_by_key["payment_deadline"]["value"] == 45
    # Section 2(b): 15 days
    assert rules_by_key["default_period"]["value"] == 15
    # Section 2(b) Explanation: 15 days
    assert rules_by_key["deemed_acceptance"]["value"] == 15
    # Section 16: 3 times bank rate
    assert rules_by_key["interest_multiplier"]["value"] == 3
    # Section 16: monthly rests
    assert "monthly" in rules_by_key["interest_compounding"]["value"].lower()
    # Section 2(n): micro and small
    assert "micro" in rules_by_key["enterprise_classification"]["value"]
    assert "small" in rules_by_key["enterprise_classification"]["value"]
    assert "medium" not in rules_by_key["enterprise_classification"]["value"]
    # Udyam registration
    assert rules_by_key["udyam_requirement"]["value"] is True
    # Registration timing
    assert rules_by_key["registration_timing"]["value"] == "predates_supply"
    # RBI Bank Rate
    assert rules_by_key["rbi_bank_rate"]["value"] == 5.75


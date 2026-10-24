"""RecoverPay Calculator Agent

Responsible for loading the legal and business rules,
validating rule verification status,
and calculating statutory interest and payment deadlines.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from core.calc import (
    DEFAULT_RULES_PATH,
    RULES_PATH,
    InterestEstimate,
    RulesNotVerified,
    due_date_for,
    estimate_interest,
    get_rule,
    load_rules,
)
from core.models import CasePackage

CALCULATOR_RULES_PATH = RULES_PATH


class Calculator:
    """Statutory interest and deadline calculator for Indian MSME overdue claims."""

    def __init__(self, rules_path: Path | str | None = None):
        self.rules_path = Path(rules_path) if rules_path else CALCULATOR_RULES_PATH
        self.rules = load_rules(self.rules_path)

    def get_loaded_rules_path(self) -> Path:
        """Returns the actual path of the rules file loaded by the calculator."""
        return self.rules_path

    def reload(self, rules_path: Path | str | None = None) -> dict[str, Any]:
        """Reloads rules from the specified or existing path."""
        if rules_path:
            self.rules_path = Path(rules_path)
        self.rules = load_rules(self.rules_path)
        return self.rules

    def calculate_due_date(
        self,
        case: CasePackage,
        rules: dict | None = None,
    ) -> tuple[date, list[str]]:
        """Calculates payment due date and credit limit caveats."""
        active_rules = rules if rules is not None else self.rules
        return due_date_for(case, rules=active_rules)

    def calculate_interest(
        self,
        case: CasePackage,
        as_of: date | None = None,
        rules: dict | None = None,
    ) -> InterestEstimate:
        """Calculates statutory compound interest under MSMED Act Section 16.

        Raises:
            RulesNotVerified: If any required statutory calculation rule is null or unverified.
        """
        active_rules = rules if rules is not None else self.rules
        return estimate_interest(case, as_of=as_of, rules=active_rules)


# Module-level convenience functions
def get_calculator(rules_path: Path | str | None = None) -> Calculator:
    return Calculator(rules_path=rules_path)


def calculate_case_interest(
    case: CasePackage,
    as_of: date | None = None,
    rules_path: Path | str | None = None,
    rules: dict | None = None,
) -> InterestEstimate:
    calc = Calculator(rules_path=rules_path)
    return calc.calculate_interest(case, as_of=as_of, rules=rules)


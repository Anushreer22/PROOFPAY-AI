"""RecoverPay Eligibility Agent

Responsible for validating supplier registration (Udyam),
enterprise size classification, and activity eligibility against statutory rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.calc import (
    DEFAULT_RULES_PATH,
    RULES_PATH,
    Eligibility,
    RulesNotVerified,
    assess_eligibility,
    load_rules,
)

ELIGIBILITY_RULES_PATH = RULES_PATH


class EligibilityAgent:
    """Eligibility agent assessing MSMED Act Chapter V eligibility criteria."""

    def __init__(self, rules_path: Path | str | None = None):
        self.rules_path = Path(rules_path) if rules_path else ELIGIBILITY_RULES_PATH
        self.rules = load_rules(self.rules_path)

    def get_loaded_rules_path(self) -> Path:
        """Returns the actual path of the rules file loaded by the agent."""
        return self.rules_path

    def reload(self, rules_path: Path | str | None = None) -> dict[str, Any]:
        """Reloads rules from the specified or existing path."""
        if rules_path:
            self.rules_path = Path(rules_path)
        self.rules = load_rules(self.rules_path)
        return self.rules

    def assess(
        self,
        registered: bool,
        enterprise_class: str,
        activity: str,
        nic_code: str = "",
        rules: dict | None = None,
    ) -> Eligibility:
        """Assesses enterprise eligibility for Chapter V delayed-payment statutory remedies.

        Raises:
            RulesNotVerified: If any required statutory eligibility rule is unverified
                              (e.g., eligible_activities).
        """
        active_rules = rules if rules is not None else self.rules
        return assess_eligibility(
            registered=registered,
            enterprise_class=enterprise_class,
            activity=activity,
            nic_code=nic_code,
            rules=active_rules,
        )


# Module-level convenience functions
def get_eligibility_agent(rules_path: Path | str | None = None) -> EligibilityAgent:
    return EligibilityAgent(rules_path=rules_path)


def check_supplier_eligibility(
    registered: bool,
    enterprise_class: str,
    activity: str,
    nic_code: str = "",
    rules_path: Path | str | None = None,
    rules: dict | None = None,
) -> Eligibility:
    agent = EligibilityAgent(rules_path=rules_path)
    return agent.assess(
        registered=registered,
        enterprise_class=enterprise_class,
        activity=activity,
        nic_code=nic_code,
        rules=rules,
    )


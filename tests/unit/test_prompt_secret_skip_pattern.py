from __future__ import annotations

import os
from unittest.mock import patch

from nlp2cmd.automation.step_validator import StepValidator


def test_prompt_secret_not_skipped_when_env_var_invalid_for_pattern():
    validator = StepValidator()
    with patch.dict(os.environ, {"HF_TOKEN": "hf_short"}, clear=True):
        res = validator.validate_pre_prompt_secret(
            variables={},
            params={"env_var": "HF_TOKEN", "key_pattern": r"hf_[A-Za-z0-9]{34,}"},
        )

    assert res.passed is True
    assert res.details.get("already_set_invalid") is True


def test_prompt_secret_skipped_when_env_var_matches_pattern():
    validator = StepValidator()
    good = "hf_" + ("a" * 34)
    with patch.dict(os.environ, {"HF_TOKEN": good}, clear=True):
        res = validator.validate_pre_prompt_secret(
            variables={},
            params={"env_var": "HF_TOKEN", "key_pattern": r"hf_[A-Za-z0-9]{34,}"},
        )

    assert res.passed is True
    assert res.details.get("already_set") is True

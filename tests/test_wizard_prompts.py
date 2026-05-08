import pytest

from photodaterescue.wizard_prompts import ScriptedPrompts, WizardPromptError


def test_scripted_choice_returns_matching_choice():
    prompts = ScriptedPrompts(["live"])

    assert prompts.choice("Mode?", [("repair", "Repair"), ("live", "Live")]) == "live"


def test_scripted_confirm_accepts_boolean_answers():
    prompts = ScriptedPrompts([True, False])

    assert prompts.confirm("Continue?") is True
    assert prompts.confirm("Again?") is False


def test_scripted_prompts_fail_when_answers_run_out():
    prompts = ScriptedPrompts([])

    with pytest.raises(WizardPromptError, match="No scripted answer"):
        prompts.text("Input?")

"""Prompt helpers for the guided terminal wizard."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple


Choice = Tuple[str, str]


class WizardPromptError(RuntimeError):
    """Raised when a wizard prompt cannot be answered."""


class TerminalPrompts:
    def text(self, message: str, default: str = "") -> str:
        suffix = " [{0}]".format(default) if default else ""
        answer = input("{0}{1}: ".format(message, suffix)).strip()
        return answer or default

    def confirm(self, message: str, default: bool = False) -> bool:
        suffix = "Y/n" if default else "y/N"
        while True:
            answer = input("{0} [{1}]: ".format(message, suffix)).strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("请输入 y 或 n。")

    def choice(self, message: str, choices: Sequence[Choice], default: Optional[str] = None) -> str:
        if not choices:
            raise WizardPromptError("没有可选项")
        valid_keys = {key for key, _label in choices}
        if default is not None and default not in valid_keys:
            raise WizardPromptError("默认选项不在可选项中：{0}".format(default))

        while True:
            print(message)
            for index, (key, label) in enumerate(choices, start=1):
                marker = " [default]" if key == default else ""
                print("  {0}. {1}{2}".format(index, label, marker))
            answer = input("> ").strip()
            if not answer and default is not None:
                return default
            if answer.isdigit():
                index = int(answer)
                if 1 <= index <= len(choices):
                    return choices[index - 1][0]
            if answer in valid_keys:
                return answer
            print("请输入列表中的编号或选项 key。")


class ScriptedPrompts:
    def __init__(self, answers: Iterable[Any]):
        self._answers: List[Any] = list(answers)
        self.messages: List[str] = []

    def text(self, message: str, default: str = "") -> str:
        self.messages.append(message)
        answer = self._next_answer()
        if answer == "" and default:
            return default
        return str(answer)

    def confirm(self, message: str, default: bool = False) -> bool:
        self.messages.append(message)
        answer = self._next_answer()
        if answer == "":
            return default
        if isinstance(answer, bool):
            return answer
        lowered = str(answer).strip().lower()
        if lowered in {"y", "yes", "true", "1"}:
            return True
        if lowered in {"n", "no", "false", "0"}:
            return False
        raise WizardPromptError("无效的脚本确认答案：{0}".format(answer))

    def choice(self, message: str, choices: Sequence[Choice], default: Optional[str] = None) -> str:
        self.messages.append(message)
        answer = self._next_answer()
        if answer == "" and default is not None:
            return default
        valid_keys = {key for key, _label in choices}
        answer_text = str(answer)
        if answer_text in valid_keys:
            return answer_text
        if answer_text.isdigit():
            index = int(answer_text)
            if 1 <= index <= len(choices):
                return choices[index - 1][0]
        raise WizardPromptError("无效的脚本选择答案：{0}".format(answer))

    def _next_answer(self) -> Any:
        if not self._answers:
            raise WizardPromptError("No scripted answer available")
        return self._answers.pop(0)

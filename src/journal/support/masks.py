import re
import time
from pathlib import Path

from journal.support.plausible_secret import PlausibleSecret
from journal.support.secret_values import EMAIL_SIGN_TOKEN, RETIRED, SecretValues
from journal.support.unmasked import Unmasked


class Masks:
    """The secret values no write may carry: each one found in text about to be written becomes [secret VARIABLE], and the leak is noted for the alarm. A field shown while typing, and a value no secret could plausibly be, such as a common word, never masks; a value written as a {placeholder}, and an Unmasked text, stay as they are; a hidden value too weak to mask is named in weak instead. The values are read again when the values file or the list of shown fields changes, by time and size, looked at once per statement, so two writes in one clock tick are both seen; values read while either file changed are used once and read again next time."""

    def __init__(self, values: SecretValues) -> None:
        self.values = values
        self._stamp: tuple = ()
        self._masks: dict[str, str] = {}
        self._patterns: dict[str, re.Pattern] = {}
        self.leaks: list[tuple[str, float]] = []
        self.weak: tuple[str, ...] = ()

    def masked(self, params: tuple) -> tuple:
        masks = self.current()
        return tuple(str(param) if isinstance(param, Unmasked) else self.replaced(param, masks) if isinstance(param, str) and masks else param for param in params)

    def has_secret(self, params: tuple) -> bool:
        masks = self.current()
        return any(self.found(value, param) for param in params if isinstance(param, str) and not isinstance(param, Unmasked) for value in masks)

    def replaced(self, text: str, masks: dict[str, str]) -> str:
        for value, variable in masks.items():
            if not self.found(value, text):
                continue
            text = self._patterns[value].sub(lambda match: match[0] if match[1] else f"[secret {variable}]", text)
            self.leaks.append((variable, time.time()))
        return text

    def found(self, value: str, text: str) -> bool:
        return value in text and any(not match[1] for match in self._patterns[value].finditer(text))

    def current(self) -> dict[str, str]:
        stamp = self.file_stamps()
        if stamp != self._stamp:
            plain, values = self.values.shown(), self.values.values()
            plausible = PlausibleSecret(values)
            hidden = {variable: value for variable, value in values.items() if variable not in plain}
            self._masks = {value: self.stem(variable) for variable, value in hidden.items() if plausible.admits(value)}
            self.weak = tuple(sorted({self.stem(variable) for variable, value in hidden.items() if not plausible.admits(value)}))
            self._patterns = {value: re.compile(rf"(\{{{re.escape(value)}\}})|{re.escape(value)}") for value in self._masks}
            self._stamp = stamp if self.file_stamps() == stamp else ()
        return self._masks

    @staticmethod
    def stem(variable: str) -> str:
        return variable.removeprefix(RETIRED).rsplit(EMAIL_SIGN_TOKEN, 1)[0]

    def file_stamps(self) -> tuple:
        return self.stamp(self.values.path), self.stamp(self.values.shown_path)

    @staticmethod
    def stamp(path: Path) -> tuple:
        try:
            status = path.stat()
        except FileNotFoundError:
            return ()
        return status.st_mtime_ns, status.st_size

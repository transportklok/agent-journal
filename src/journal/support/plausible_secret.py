from collections.abc import Iterable

SHORTEST_CHARACTERS = 8
COMMON_WORDS = frozenset("""
password passwords passcode passphrase username usernames account accounts readonly readwrite secret secrets
credential credentials login logins localhost database databases staging production developer development
administrator admin1234 default defaults example examples changeme letmein welcome welcome1 qwertyuiop
abcdefgh abcdefghij 12345678 123456789 1234567890 00000000 11111111 87654321 trustno1 sunshine princess
football baseball iloveyou starwars superman dragonfly computer internet security everyone anything something
nothing password1 transport customer customers platform mobile service services application applications
connection connections settings configuration register registration identity identifier token tokens access
authorization authentication session sessions template templates variable variables placeholder placeholders
""".split())


class PlausibleSecret:
    """Whether a value is plausibly a secret: long enough, and no common word or word of a secret's own variable names, which masking would rewrite wherever the word is written."""

    def __init__(self, variables: Iterable[str]) -> None:
        self.words = COMMON_WORDS | {segment.lower() for variable in variables for segment in variable.split("_") if segment}

    def admits(self, value: str) -> bool:
        return len(value) >= SHORTEST_CHARACTERS and value.lower() not in self.words

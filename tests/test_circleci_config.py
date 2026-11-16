"""Prevent CircleCI 2.1 config compiler failures from unescaped shell heredocs.

CircleCI treats bare << as a template opener even inside run commands/comments.
The Smarter Testing suite definition is intentionally excluded: its own
<< outputs.junit >> and << test.atoms >> placeholders use a different parser.
"""

from collections import Counter
from pathlib import Path
import re

import pytest


_ROOT = Path(__file__).resolve().parents[1]
_CONFIGS = ("config.yml", "reference.yml")
_RAW_TOKEN = re.compile(r"(?<!\\)<<")
_TEMPLATE = re.compile(r"<<\s*(?:pipeline|parameters)\.[^>]+\s*>>")
_ESCAPED_HEREDOC = re.compile(r"\\<<['\"]?([A-Z][A-Z0-9_]*)['\"]?\s*$")


@pytest.mark.parametrize("filename", _CONFIGS)
def test_circleci_21_configs_do_not_have_unescaped_non_template_openers(filename):
    text = (_ROOT / ".circleci" / filename).read_text(encoding="utf-8")
    invalid = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for token in _RAW_TOKEN.finditer(line):
            if _TEMPLATE.match(line, token.start()) is None:
                invalid.append(line_number)

    assert not invalid, (
        f"{filename} has bare << in lines {invalid}; CircleCI 2.1 requires "
        "a backslash before literal heredoc delimiters, including in comments"
    )


def test_circleci_python_heredoc_openers_are_escaped_and_balanced():
    text = (_ROOT / ".circleci" / "config.yml").read_text(encoding="utf-8")
    lines = text.splitlines()
    openers = Counter(
        match.group(1)
        for line in lines
        if (match := _ESCAPED_HEREDOC.search(line)) is not None
    )
    assert openers, "Expected the four inline Python heredocs to remain present"

    for marker, count in openers.items():
        closers = sum(line.strip() == marker for line in lines)
        assert closers == count, f"{marker}: {count} openers, {closers} closers"

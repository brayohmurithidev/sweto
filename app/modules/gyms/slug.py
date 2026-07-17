import re
import unicodedata


def slugify(value: str) -> str:
    """Convert a gym name into a URL-safe slug."""

    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    ascii_value = normalized.encode(
        "ascii",
        "ignore",
    ).decode()

    lowered = ascii_value.lower()

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        lowered,
    ).strip("-")

    return slug or "gym"

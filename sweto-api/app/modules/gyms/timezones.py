"""Default IANA time zone for each country a gym can be in."""

COUNTRY_TIMEZONES: dict[str, str] = {
    "KE": "Africa/Nairobi",
    "UG": "Africa/Kampala",
    "TZ": "Africa/Dar_es_Salaam",
    "RW": "Africa/Kigali",
    "BI": "Africa/Bujumbura",
    "SS": "Africa/Juba",
    "SO": "Africa/Mogadishu",
}
"""Countries with a single time zone. The DR Congo spans two, so a gym there
keeps whatever time zone it already has."""


def timezone_for_country(country_code: str) -> str | None:
    return COUNTRY_TIMEZONES.get(country_code.upper())

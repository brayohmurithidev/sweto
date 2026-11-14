def render_otp_message(*, otp_code: str, expires_in_seconds: int) -> str:
    """Return the SMS text for a login code.

    Kept provider-independent so every provider sends identical copy. The
    returned text contains the code and must never be logged outside local
    development.
    """

    minutes = max(1, expires_in_seconds // 60)
    unit = "minute" if minutes == 1 else "minutes"
    return (
        f"{otp_code} is your SWETO verification code. "
        f"It expires in {minutes} {unit}. Never share this code with anyone."
    )

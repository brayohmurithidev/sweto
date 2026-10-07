from enum import Enum as PythonEnum

from sqlalchemy import Enum as SQLAlchemyEnum


def enum_values[EnumT: PythonEnum](
    enum_class: type[EnumT],
) -> list[str]:
    """Return the string values defined by a Python enum."""

    return [str(member.value) for member in enum_class]


def string_enum[EnumT: PythonEnum](
    enum_class: type[EnumT],
    *,
    name: str,
) -> SQLAlchemyEnum:
    """
    Create a SQLAlchemy enum that stores Python enum values.

    Example:
        UserStatus.ACTIVE is stored as "active",
        rather than the enum member name "ACTIVE".
    """

    return SQLAlchemyEnum(
        enum_class,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=enum_values,
    )

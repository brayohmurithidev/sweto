from pydantic import BaseModel


class APIResponse[DataT](BaseModel):
    """Standard successful API response wrapper."""

    success: bool = True
    data: DataT

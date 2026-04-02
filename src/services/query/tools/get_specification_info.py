import httpx
from langchain.tools import tool

from settings_query import get_settings

settings = get_settings()


@tool
def vehicle_state(vehicle: str):
    """Gets the manufacturer published recommended information about a vehicle

    Args:
        vehicle: the current vehicle (expects YEAR MAKE MODEL)

    Returns:
        dict containing information about specifications of vehicle
    """
    response = httpx.get(
        f"{settings.specifications_library_url}/vehicles/specs",
        params={"vehicle": vehicle},
    )
    response.raise_for_status()
    return response.json()

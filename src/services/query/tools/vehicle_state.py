import httpx
from langchain.tools import tool

from settings import get_settings

settings = get_settings()


@tool
def vehicle_state(vehicle: str):
    """Gets the current state of the vehicle

    Args:
        vehicle: the current vehicle (expects YEAR MAKE MODEL)

    Returns:
        dict containing information about current state of vehicle
    """
    response = httpx.get(
        f"{settings.vehicle_library_url}/vehicles/state",
        params={"vehicle": vehicle},
    )
    response.raise_for_status()
    return response.json()

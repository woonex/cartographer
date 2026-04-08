import httpx
from langchain.tools import tool

from settings_query import get_settings

settings = get_settings()


@tool
def get_maintenance_schedule(vehicle: str):
    """Gets the manufacturer maintenance schedule for a vehicle, including which services
    are performed at each mileage interval.

    Args:
        vehicle: the current vehicle (expects YEAR MAKE MODEL)

    Returns:
        list of maintenance items with service name, action, and interval_miles
    """
    response = httpx.get(
        f"{settings.specifications_library_url}/vehicle/maintenance",
        params={"vehicle": vehicle},
    )
    response.raise_for_status()
    return response.json()

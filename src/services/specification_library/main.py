from enum import Enum

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class Vehicle(BaseModel):
    years_valid: tuple[int, int] = Field()
    make: str
    model: str


class VehicleSpecifications(BaseModel):
    tire_pressure_front_psi: int = Field(gt=0)
    tire_pressure_rear_psi: int = Field(gt=0)
    oil_capacity_quarts: float = Field(gt=0)
    oil_type: str
    recommended_fuel_octane: int = Field(gt=0)
    fuel_tank_capacity_gallons: float = Field(gt=0)
    towing_capacity_lbs: int = Field(ge=0)
    recommended_service_interval_miles: int = Field(gt=0)
    mpg_city: float = Field(gt=0)
    mpg_highway: float = Field(gt=0)
    mpg_combined: float = Field(gt=0)


class VehicleEntry(BaseModel):
    vehicle: Vehicle
    specs: VehicleSpecifications


SPECS: list[VehicleEntry] = [
    VehicleEntry(
        vehicle=Vehicle(years_valid=(2024, 2025), make="Toyota", model="Tacoma"),
        specs=VehicleSpecifications(
            tire_pressure_front_psi=33,
            tire_pressure_rear_psi=33,
            oil_capacity_quarts=6.2,
            oil_type="0W-20",
            recommended_fuel_octane=87,
            fuel_tank_capacity_gallons=21.1,
            towing_capacity_lbs=6500,
            recommended_service_interval_miles=10000,
            mpg_city=21.0,
            mpg_highway=26.0,
            mpg_combined=23.0,
        ),
    ),
    VehicleEntry(
        vehicle=Vehicle(years_valid=(2018, 2024), make="Toyota", model="Camry"),
        specs=VehicleSpecifications(
            tire_pressure_front_psi=35,
            tire_pressure_rear_psi=35,
            oil_capacity_quarts=4.8,
            oil_type="0W-20",
            recommended_fuel_octane=87,
            fuel_tank_capacity_gallons=15.8,
            towing_capacity_lbs=0,
            recommended_service_interval_miles=10000,
            mpg_city=28.0,
            mpg_highway=39.0,
            mpg_combined=32.0,
        ),
    ),
]


def find_specs(vehicle: str) -> VehicleEntry | None:
    parts = vehicle.split(" ", 1)
    if len(parts) != 2:
        return None
    try:
        year = int(parts[0])
    except ValueError:
        return None
    make_model = parts[1]
    for entry in SPECS:
        full_name = f"{entry.vehicle.make} {entry.vehicle.model}"
        low, high = entry.vehicle.years_valid
        if make_model == full_name and low <= year <= high:
            return entry
    return None


app = FastAPI()


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}


@app.get("/vehicle/specifications")
def get_vehicle_specs(vehicle: str = Query(..., description="Vehicle identifier (YEAR MAKE MODEL)")):
    """Gets the manufacturer specifications of a vehicle"""
    entry = find_specs(vehicle)
    if entry is None:
        return JSONResponse(status_code=404, content={"detail": f"Vehicle '{vehicle}' not found"})
    return entry.specs

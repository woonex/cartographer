from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

VEHICLES = {
    "2025 Toyota Tacoma": {
        "friendly_name": "Toby",
        "odometer": 12345,
        "odometer_at_last_service": 9800,
        "ignition_status": "off",
        "last_ignition_off_utc": "2026-04-06T14:32:00Z",
        "engine_rpm": 0,
        "ambient_temp_c": 8,
        "mil_on": True,
        "srs_warning_on": False,
        "abs_warning_on": False,
        "traction_control_off": False,
        "battery_warning_on": False,
        "charging_system_voltage_v": None,
        "oil_life_pct": 0.61,
        "engine_coolant_temp_c": 18,
        "transmission_fluid_temp_c": 18,
        "washer_fluid_low": True,
        "4wd_mode": "2H",
        "diff_lock_engaged": False,
        "tow_haul_mode_on": False,
        "drivetrain": {
            "gas": {
                "fuel_level": 0.23
            },
            "battery": {
                "voltage": 12.6
            }
        },
        "tire_pressure_psi": {
            "front_driver": 23,
            "front_passenger": 35,
            "rear_driver": 36,
            "rear_passenger": 33
        }
    },
    "2021 Toyota Camry": {
        "friendly_name": "Herbie",
        "odometer": 54321,
        "odometer_at_last_service": 51000,
        "ignition_status": "on",
        "last_ignition_off_utc": "2026-04-06T08:15:00Z",
        "engine_rpm": 1450,
        "ambient_temp_c": 8,
        "mil_on": False,
        "srs_warning_on": False,
        "abs_warning_on": False,
        "traction_control_off": False,
        "battery_warning_on": False,
        "charging_system_voltage_v": 14.1,
        "oil_life_pct": 0.32,
        "engine_coolant_temp_c": 91,
        "transmission_fluid_temp_c": 74,
        "washer_fluid_low": False,
        "drivetrain": {
            "gas": {
                "fuel_level": 0.89
            },
            "battery": {
                "voltage": 12.4
            }
        },
        "tire_pressure_psi": {
            "front_driver": 35,
            "front_passenger": 37,
            "rear_driver": 35,
            "rear_passenger": 35
        }
    }
}


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}

@app.get("/vehicles")
def get_available_vehicles() -> list[str]:
    """Gets the names of all available vehicles"""
    return list(VEHICLES.keys())

@app.get("/vehicles/state")
def get_vehicle_state(vehicle: str = Query(..., description="Vehicle identifier (YEAR MAKE MODEL)")):
    """Gets the current state of a vehicle"""
    state = VEHICLES.get(vehicle)
    if state is None:
        return JSONResponse(status_code=404, content={"detail": f"Vehicle '{vehicle}' not found"})
    return state

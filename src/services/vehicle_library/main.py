from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI()

VEHICLES = {
    "2025 Toyota Tacoma": {
        "odometer": 12345,
        "drivetrain": {
            "gas": {
                "fuel_level": 0.23
            },
            "battery": {
                "fuel_level": 0.97,
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
        "odometer": 54321,
        "drivetrain": {
            "gas": {
                "fuel_level": 0.89
            },
            "battery": {
                "fuel_level": 0.80,
                "voltage": 12.4
            },
            "hv_battery": {
                "fuel_level": 0.55,
                "voltage": 259
            }
        }
    }
}


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}

@app.get("/vehicles")
def get_avavailable_vehicles():
    return VEHICLES.keys()

@app.get("/vehicles/state")
def get_vehicle_state(vehicle: str = Query(..., description="Vehicle identifier (YEAR MAKE MODEL)")):
    """Gets the current state of a vehicle"""
    state = VEHICLES.get(vehicle)
    if state is None:
        return JSONResponse(status_code=404, content={"detail": f"Vehicle '{vehicle}' not found"})
    return state

from fastapi.testclient import TestClient

from main import app, find_specs

client = TestClient(app)


class TestFindSpecs:
    def test_exact_match(self):
        entry = find_specs("2025 Toyota Tacoma")
        assert entry is not None
        assert entry.specs.towing_capacity_lbs == 6500

    def test_year_range_match(self):
        """A 2024 Tacoma should match the same entry as a 2025"""
        entry = find_specs("2024 Toyota Tacoma")
        assert entry is not None
        assert entry.specs.towing_capacity_lbs == 6500

    def test_year_range_lower_bound(self):
        entry = find_specs("2018 Toyota Camry")
        assert entry is not None
        assert entry.specs.mpg_combined == 32.0

    def test_year_range_upper_bound(self):
        entry = find_specs("2024 Toyota Camry")
        assert entry is not None
        assert entry.specs.mpg_combined == 32.0

    def test_year_out_of_range(self):
        assert find_specs("2017 Toyota Camry") is None

    def test_unknown_vehicle(self):
        assert find_specs("2025 Honda Civic") is None

    def test_bad_format_no_year(self):
        assert find_specs("Toyota Tacoma") is None

    def test_bad_format_empty(self):
        assert find_specs("") is None


class TestGetVehicleSpecsEndpoint:
    def test_success(self):
        response = client.get("/vehicle/specifications", params={"vehicle": "2025 Toyota Tacoma"})
        assert response.status_code == 200
        data = response.json()
        assert data["tire_pressure_front_psi"] == 33
        assert data["fuel_tank_capacity_gallons"] == 21.1

    def test_year_range_lookup(self):
        response = client.get("/vehicle/specifications", params={"vehicle": "2020 Toyota Camry"})
        assert response.status_code == 200
        assert response.json()["mpg_combined"] == 32.0

    def test_not_found(self):
        response = client.get("/vehicle/specifications", params={"vehicle": "2025 Honda Civic"})
        assert response.status_code == 404

    def test_missing_param(self):
        response = client.get("/vehicle/specifications")
        assert response.status_code == 422

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200

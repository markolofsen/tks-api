import pytest
from tks_api_official.calc import CustomsCalculator

@pytest.fixture
def valid_config(tmp_path):
    """Provide a valid configuration file for testing."""
    config_content = """
    tariffs:
      base_clearance_fee: 3100
      base_util_fee: 20000
      etc_util_coeff_base: 1.5
      ctp_util_coeff_base: 1.2
      excise_rates:
        gasoline: 58
        diesel: 58
        electric: 0
        hybrid: 58
      recycling_factors:
        default:
          gasoline: 1.0
          diesel: 1.1
          electric: 0.3
          hybrid: 0.9
        adjustments:
          5-7:
            gasoline: 0.26
            diesel: 0.26
            electric: 0.26
            hybrid: 0.26
      age_groups:
        overrides:
          5-7:
            gasoline:
              rate_per_cc: 4.8
              min_duty: 0
            diesel:
              rate_per_cc: 5.0
              min_duty: 0
            electric:
              rate_per_cc: 0
              min_duty: 1000
            hybrid:
              rate_per_cc: 2.0
              min_duty: 2500
    """
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
def calculator(valid_config):
    """Create an instance of the calculator with a valid config."""
    return CustomsCalculator(config_path=valid_config)

def test_config_loading(calculator):
    """Test that the configuration loads correctly."""
    assert calculator.config['tariffs']['base_clearance_fee'] == 3100
    assert calculator.config['tariffs']['excise_rates']['gasoline'] == 58

def test_set_vehicle_details(calculator):
    """Test setting vehicle details."""
    calculator.set_vehicle_details(
        age="5-7",
        engine_capacity=2000,
        engine_type="gasoline",
        power=150,
        price=100000,
        owner_type="individual",
        currency="USD"
    )
    assert calculator.vehicle_age.value == "5-7"
    assert calculator.engine_capacity == 2000
    assert calculator.engine_type.value == "gasoline"
    assert calculator.vehicle_power == 150
    assert calculator.vehicle_price == 100000
    assert calculator.vehicle_currency == "USD"

def test_calculate_etc(calculator):
    """Test ETC calculation mode."""
    calculator.set_vehicle_details(
        age="5-7",
        engine_capacity=2000,
        engine_type="gasoline",
        power=150,
        price=100000,
        owner_type="individual",
        currency="USD"
    )
    results = calculator.calculate_etc()
    assert results["Mode"] == "ETC"
    assert results["Total Pay (RUB)"] > 0
    assert "Duty (RUB)" in results

def test_calculate_ctp(calculator):
    """Test CTP calculation mode."""
    calculator.set_vehicle_details(
        age="5-7",
        engine_capacity=2000,
        engine_type="gasoline",
        power=150,
        price=100000,
        owner_type="individual",
        currency="USD"
    )
    results = calculator.calculate_ctp()
    assert results["Mode"] == "CTP"
    assert results["Total Pay (RUB)"] > 0
    assert "Excise (RUB)" in results

# def test_invalid_currency(calculator):
#     """
#     Test behavior when an unsupported currency is provided.
#     Ensures the calculator raises a ValueError for truly unsupported currencies.
#     """
#     calculator.set_vehicle_details(
#         age="5-7",
#         engine_capacity=2000,
#         engine_type="gasoline",
#         power=150,
#         price=100000,
#         owner_type="individual",
#         currency="XYZ"
#     )
#     with pytest.raises(ValueError, match="Unsupported currency: XYZ"):
#         calculator.convert_to_local_currency(100, "XYZ")

# def test_already_cleared(calculator):
#     """Test calculation when the vehicle is already cleared."""
#     calculator.set_vehicle_details(
#         age="5-7",
#         engine_capacity=2000,
#         engine_type="gasoline",
#         power=150,
#         price=100000,
#         owner_type="individual",
#         currency="USD"
#     )
#     calculator.is_already_cleared = True
#     results = calculator.calculate_etc()
#     assert results["Mode"] == "ETC"
#     assert results["Total Pay (RUB)"] == 0

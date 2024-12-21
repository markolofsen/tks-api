import pytest
from tks_api_official.calc import CustomsCalculator

@pytest.fixture
def valid_config(tmp_path):
    config_content = """
    base_clearance_fee: 30000
    base_util_fee: 20000
    etc_euro_per_cc: 1.5
    etc_euro_per_cc_diesel: 2.0
    etc_util_coeff_base: 0.26
    offroad_duty_extra_percent: 0.1
    diesel_util_extra: 0.1
    offroad_util_extra: 0.05
    ctp_base_duty_percent: 0.15
    ctp_base_duty_percent_diesel: 0.16
    ctp_excise_per_hp_benzin: 912
    ctp_excise_per_hp_diesel: 1000
    offroad_excise_extra: 0.1
    vat_percent: 0.20
    ctp_util_coeff_base: 15.03
    """
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return config_path

@pytest.fixture
def calculator(valid_config):
    return CustomsCalculator(config_path=valid_config)

def test_config_loading(calculator):
    """Test that the configuration loads correctly."""
    assert calculator.config["base_clearance_fee"] == 30000
    assert calculator.config["vat_percent"] == 0.20

def test_set_fields(calculator):
    """Test setting fields for the calculator."""
    fields = {
        "price": 1000000,
        "currency": "usd",
        "volume_cc": 2000,
        "power_hp": 150,
        "age_category": "3-5",
        "engine_type": "gas",
        "is_offroad": False,
        "is_already_cleared": False,
        "importer_type": "individual",
    }
    calculator.set_fields(**fields)
    for key, value in fields.items():
        assert getattr(calculator, key) == value

def test_calculate_etc(calculator):
    """Test ETC calculation mode."""
    calculator.set_fields(
        price=500000,
        currency="usd",
        volume_cc=800,
        power_hp=100,
        age_category="3-5",
        engine_type="gas",
        is_offroad=False,
        is_already_cleared=False,
        importer_type="individual",
    )
    calculator.calculate()
    results = calculator.results
    assert results["mode"] == "ETC"
    assert results["total_pay"] > 0

def test_calculate_ctp(calculator):
    """Test CTP calculation mode."""
    calculator.set_fields(
        price=1000000,
        currency="usd",
        volume_cc=2000,
        power_hp=300,
        age_category="<3",
        engine_type="diesel",
        is_offroad=True,
        is_already_cleared=False,
        importer_type="legal",
    )
    calculator.calculate()
    results = calculator.results
    assert results["mode"] == "CTP"
    assert results["total_pay"] > 0

def test_invalid_currency(calculator):
    """
    Test behavior when an unsupported currency is provided.
    Ensures the calculator raises a ValueError for truly unsupported currencies.
    """
    calculator.set_fields(
        price=100000,
        currency="XYZ",  # A clearly invalid currency code
        volume_cc=1500,
        power_hp=200,
        age_category="3-5",
        engine_type="gas",
        is_offroad=False,
        is_already_cleared=False,
        importer_type="individual",
    )
    with pytest.raises(ValueError, match="Unsupported currency: XYZ"):
        calculator.calculate()


def test_already_cleared(calculator):
    """Test calculation when the vehicle is already cleared."""
    calculator.set_fields(
        price=1000000,
        currency="usd",
        volume_cc=2000,
        power_hp=300,
        age_category="3-5",
        engine_type="diesel",
        is_offroad=False,
        is_already_cleared=True,
        importer_type="individual",
    )
    calculator.calculate()
    results = calculator.results
    assert results["mode"] == "CLEARED"
    assert results["total_pay"] == 0.0
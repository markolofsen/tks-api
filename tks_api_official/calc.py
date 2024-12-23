import logging
import yaml
from enum import Enum
from tabulate import tabulate
from currency_converter_free import CurrencyConverter

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Custom Exceptions
class WrongParamException(Exception):
    """Exception raised for invalid parameters."""
    def __init__(self, message):
        super().__init__(message)
        logger.error(message)

# Enums for Vehicle Attributes
class EnginePowerUnit(Enum):
    KW = "kilowatt"
    HP = "horsepower"

class EngineType(Enum):
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"

class VehicleAge(Enum):
    NEW = "new"
    ONE_TO_THREE = "1-3"
    THREE_TO_FIVE = "3-5"
    FIVE_TO_SEVEN = "5-7"
    OVER_SEVEN = "over_7"

class VehicleOwnerType(Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"

# Constants for Tariffs
BASE_VAT = 0.2
RECYCLING_FEE_BASE_RATE = 20000
CUSTOMS_CLEARANCE_TAX_RANGES = [
    (200000, 775),
    (450000, 1550),
    (1200000, 3100),
    (2700000, 8530),
    (4200000, 12000),
    (5500000, 15500),
    (7000000, 20000),
    (8000000, 23000),
    (9000000, 25000),
    (10000000, 27000),
    (float('inf'), 30000)
]

class CustomsCalculator:
    """
    Customs Calculator for vehicle import duties.
    """

    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.converter = CurrencyConverter(source="CBR")
        self.reset_fields()

    def _load_config(self, path):
        """Load configuration from a YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
            if "tariffs" not in config:
                raise KeyError("Configuration missing required 'tariffs' structure.")
            logger.info("Configuration loaded.")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise

    def reset_fields(self):
        """Reset calculation fields."""
        self.vehicle_age = None
        self.engine_capacity = None
        self.engine_type = None
        self.vehicle_power = None
        self.vehicle_price = None
        self.owner_type = None
        self.vehicle_currency = "USD"

    def set_vehicle_details(self, age, engine_capacity, engine_type, power, price, owner_type, currency="USD"):
        """Set the details of the vehicle."""
        try:
            self.vehicle_age = VehicleAge(age)
            self.engine_capacity = engine_capacity
            self.engine_type = EngineType(engine_type)
            self.vehicle_power = power
            self.vehicle_price = price
            self.owner_type = VehicleOwnerType(owner_type)
            self.vehicle_currency = currency.upper()
        except ValueError as e:
            raise WrongParamException(f"Invalid parameter: {e}")

    def calculate_etc(self):
        """Calculate customs duties using the ETC method."""
        try:
            overrides = self.config['tariffs']['age_groups']['overrides'].get(self.vehicle_age.value, {})
            engine_tariffs = overrides.get(self.engine_type.value)

            rate_per_cc = engine_tariffs['rate_per_cc']
            duty_rub = rate_per_cc * self.engine_capacity * self.convert_to_local_currency(1, "EUR")

            clearance_fee = self.config['tariffs']['base_clearance_fee']
            util_fee = self.config['tariffs']['base_util_fee']
            recycling_fee = self.calculate_recycling_fee()

            total_pay = clearance_fee + duty_rub + util_fee + recycling_fee
            return {
                "Mode": "ETC",
                "Clearance Fee (RUB)": clearance_fee,
                "Duty (RUB)": duty_rub,
                "Recycling Fee (RUB)": recycling_fee,
                "Util Fee (RUB)": util_fee,
                "Total Pay (RUB)": total_pay,
            }
        except KeyError as e:
            logger.error(f"Missing tariff configuration: {e}")
            raise

    def calculate_ctp(self):
        """Calculate customs duties using the CTP method."""
        try:
            # Convert price to RUB
            price_rub = self.convert_to_local_currency(self.vehicle_price, self.vehicle_currency)
            vat_rate = BASE_VAT

            # Calculate Duty: 20% of price or 0.44 EUR/cm³ minimum
            duty_rate = 0.2
            min_duty_per_cc = self.convert_to_local_currency(0.44, "EUR")
            duty_rub = max(price_rub * duty_rate, min_duty_per_cc * self.engine_capacity)

            # Calculate Excise: Based on engine power
            excise = self.calculate_excise()

            # Calculate VAT: Applied to price + duty + excise
            vat = (price_rub + duty_rub + excise) * vat_rate

            # Clearance Fee: Fixed
            clearance_fee = self.config['tariffs']['base_clearance_fee']

            # Util Fee: Applied based on multiplier
            util_fee = self.config['tariffs']['base_util_fee'] * self.config['tariffs']['ctp_util_coeff_base']

            # Total Pay
            total_pay = duty_rub + excise + vat + clearance_fee + util_fee
            return {
                "Mode": "CTP",
                "Price (RUB)": price_rub,
                "Duty (RUB)": duty_rub,
                "Excise (RUB)": excise,
                "VAT (RUB)": vat,
                "Clearance Fee (RUB)": clearance_fee,
                "Util Fee (RUB)": util_fee,
                "Total Pay (RUB)": total_pay,
            }
        except KeyError as e:
            logger.error(f"Missing tariff configuration: {e}")
            raise


    def calculate_clearance_tax(self):
        """Calculate customs clearance tax based on price."""
        for price_limit, tax in CUSTOMS_CLEARANCE_TAX_RANGES:
            if self.vehicle_price <= price_limit:
                logger.info(f"Customs clearance tax: {tax} RUB")
                return tax
        return CUSTOMS_CLEARANCE_TAX_RANGES[-1][1]  # Default to the last range

    def calculate_recycling_fee(self):
        """Calculate recycling fee."""
        factors = self.config['tariffs']['recycling_factors']
        default_factors = factors.get('default', {})
        adjustments = factors.get('adjustments', {}).get(self.vehicle_age.value, {})
        engine_factor = adjustments.get(self.engine_type.value, default_factors.get(self.engine_type.value, 1.0))
        fee = RECYCLING_FEE_BASE_RATE * engine_factor
        logger.info(f"Recycling fee: {fee} RUB")
        return fee

    def calculate_excise(self):
        """Calculate excise based on engine power and engine type."""
        excise_rate = self.config['tariffs']['excise_rates'][self.engine_type.value]
        excise = self.vehicle_power * excise_rate
        logger.info(f"Excise: {excise} RUB")
        return excise

    def convert_to_local_currency(self, amount, currency="EUR"):
        """Convert amount from the specified currency to RUB."""
        try:
            rate = self.converter.convert(amount, currency, "RUB")
            logger.info(f"Converted {amount} {currency} to {rate:.2f} RUB")
            return rate
        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            return None

    def print_table(self, mode):
        """Print the calculation results as a table."""
        if mode == "ETC":
            results = self.calculate_etc()
        elif mode == "CTP":
            results = self.calculate_ctp()
        else:
            raise WrongParamException("Invalid calculation mode")

        table = [[k, f"{v:,.2f}" if isinstance(v, (float, int)) else v] for k, v in results.items()]
        print(tabulate(table, headers=["Description", "Amount"], tablefmt="psql"))

if __name__ == "__main__":
    # Example usage
    calculator = CustomsCalculator("config.yaml")

    # Set vehicle details (example values)
    calculator.set_vehicle_details(
        age="5-7", 
        engine_capacity=2000, 
        engine_type="gasoline", 
        power=150, 
        price=10000, 
        owner_type="individual",
        currency="USD")

    # Print results for ETC mode
    calculator.print_table("ETC")

    # Print results for CTP mode
    calculator.print_table("CTP")

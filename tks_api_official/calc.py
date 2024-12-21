#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import yaml
from tabulate import tabulate
from currency_converter_free import CurrencyConverter

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class CustomsCalculator:
    """
    Vehicle customs calculator for ETC (Unified Tariff) or CTP (Comprehensive Payment).
    Reads configuration from a YAML file and uses `currency_converter_free` for live exchange rates.
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
            logger.info("Configuration loaded.")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise

    def reset_fields(self):
        """Initialize or reset all input fields."""
        self.price = 0.0
        self.currency = "USD"
        self.volume_cc = 0
        self.power_hp = 0.0
        self.age_category = "3-5"
        self.engine_type = "gas"
        self.is_offroad = False
        self.is_already_cleared = False
        self.importer_type = "individual"
        self.results = {}

    def set_fields(self, **kwargs):
        """Set input fields dynamically."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        logger.info(f"Fields set: {kwargs}")

    def _convert_to_rub(self, amount, currency):
        """
        Convert the given amount from a specified currency to RUB.
        Raises ValueError for unsupported currencies.
        """
        logger.info(f"Converting {amount} {currency} to RUB.")
        try:
            converted_amount = self.converter.convert(amount, currency.upper(), "RUB")
            if converted_amount is None:
                raise ValueError(f"Unsupported currency: {currency}")
            return converted_amount
        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            raise ValueError(f"Unsupported currency: {currency}")


    def calculate(self):
        """Calculate the customs duties based on the input fields."""
        if self.is_already_cleared:
            self.results = {"mode": "CLEARED", "comment": "Vehicle already cleared", "total_pay": 0.0}
            return

        if (
            self.importer_type == "individual"
            and self.age_category == "3-5"
            and self.volume_cc <= 1000
            and "electric" not in self.engine_type
        ):
            logger.info("Calculating using ETC mode.")
            self._calc_etc()
        else:
            logger.info("Calculating using CTP mode.")
            self._calc_ctp()

    def _calc_etc(self):
        """Calculate customs duties using the ETC method."""
        cfg = self.config
        try:
            base_euro_per_cc = (
                cfg["etc_euro_per_cc_diesel"] if "diesel" in self.engine_type else cfg["etc_euro_per_cc"]
            )
            duty_rub = base_euro_per_cc * self.volume_cc * self._convert_to_rub(1, "EUR")

            if self.is_offroad:
                duty_rub *= 1 + cfg.get("offroad_duty_extra_percent", 0.1)

            clearance_fee = cfg["base_clearance_fee"]
            util_fee = cfg["base_util_fee"] * cfg["etc_util_coeff_base"]

            self.results = {
                "mode": "ETC",
                "clearance_fee": clearance_fee,
                "duty_rub": duty_rub,
                "util_fee": util_fee,
                "total_pay": clearance_fee + duty_rub + util_fee,
            }
        except KeyError as e:
            logger.error(f"Missing configuration key: {e}")
            raise

    def _calc_ctp(self):
        """Calculate customs duties using the CTP method."""
        cfg = self.config
        try:
            price_rub = self._convert_to_rub(self.price, self.currency)
            duty_rub = price_rub * (
                cfg["ctp_base_duty_percent_diesel"] if "diesel" in self.engine_type else cfg["ctp_base_duty_percent"]
            )
            excise = self.power_hp * (
                cfg["ctp_excise_per_hp_diesel"] if "diesel" in self.engine_type else cfg["ctp_excise_per_hp_benzin"]
            )
            if self.is_offroad:
                excise *= 1 + cfg.get("offroad_excise_extra", 0.1)

            vat = (price_rub + duty_rub + excise) * cfg["vat_percent"]
            clearance_fee = cfg["base_clearance_fee"]
            util_fee = cfg["base_util_fee"] * cfg["ctp_util_coeff_base"]

            self.results = {
                "mode": "CTP",
                "price_rub": price_rub,
                "duty_rub": duty_rub,
                "excise": excise,
                "vat": vat,
                "clearance_fee": clearance_fee,
                "util_fee": util_fee,
                "total_pay": clearance_fee + duty_rub + excise + vat + util_fee,
            }
        except KeyError as e:
            logger.error(f"Missing configuration key: {e}")
            raise

    def print_table(self):
        """Print the calculation results as a table."""
        if not self.results:
            logger.warning("No calculation results available.")
            return

        mode = self.results.get("mode")
        data = []
        if mode == "CLEARED":
            data.append(["Vehicle already cleared", "", "0.00"])
        else:
            for key, value in self.results.items():
                if key != "mode":
                    data.append([key.replace("_", " ").capitalize(), "", f"{value:,.2f}"])
        print(tabulate(data, headers=["Description", "Details", "Amount (RUB)"], tablefmt="psql"))


def main():
    calculator = CustomsCalculator("config.yaml")
    calculator.set_fields(
        price=7000000,
        currency="KRW",
        volume_cc=2000,
        power_hp=300,
        age_category="<3",
        engine_type="diesel",
        is_offroad=True,
        is_already_cleared=False,
        importer_type="legal",
    )
    calculator.calculate()
    calculator.print_table()


if __name__ == "__main__":
    main()

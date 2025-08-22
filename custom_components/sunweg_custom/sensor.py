"""
Sensor platform for the SunWEG integration.

This platform exposes a set of sensors that provide insight into the energy
production, power, environmental impact and financial savings associated
with a SunWEG photovoltaic plant. Both aggregated totals across all
accessible plants and individual plant metrics are surfaced via these
entities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_PLANT_ID, CONF_PLANT_NAME

_LOGGER = logging.getLogger(__name__)


def _parse_numeric(value: Any, multipliers: Optional[dict[str, float]] = None) -> Optional[float]:
    """Extract a float from a string potentially containing units.

    Args:
        value: The value to parse, which may be a string containing a number
            and a unit (e.g. "11.72 MWh").
        multipliers: A mapping of unit suffixes to multipliers to convert the
            base number into the desired unit (e.g. {"MWh": 1000}).

    Returns:
        The numeric value converted using the multiplier if applicable, or
        ``None`` if the value cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Strip out common currency or non‑numeric prefixes (e.g. "R$", "$", "€")
        cleaned = value
        for prefix in ("R$", "$", "€", "£"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        cleaned = cleaned.strip()
        parts = cleaned.split()
        try:
            number = float(parts[0].replace(".", ".").replace(",", "."))
        except ValueError:
            return None
        # If a unit is present and multipliers are provided, apply the multiplier
        if len(parts) > 1 and multipliers:
            unit = parts[1]
            multiplier = multipliers.get(unit)
            if multiplier is not None:
                return number * multiplier
        return number
    return None


@dataclass
class SunWegSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription to hold a function for extracting sensor values."""

    value_fn: Callable[[dict[str, Any], dict[str, Any]], Any] = lambda total, resumo: None


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    """Set up SunWEG sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    plant_id: str = data["plant_id"]
    plant_name: str = entry.data.get(CONF_PLANT_NAME, plant_id)

    # Define aggregated sensors (from totalizers)
    aggregated_sensors: list[SunWegSensorDescription] = [
        SunWegSensorDescription(
            key="energy_today",
            name="Energia gerada hoje",
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("energia_gerada_hoje"), {"MWh": 1000.0, "kWh": 1.0}
            ),
        ),
        SunWegSensorDescription(
            key="energy_month",
            name="Energia gerada no mês",
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("energia_gerada_mes"), {"MWh": 1000.0, "kWh": 1.0}
            ),
        ),
        SunWegSensorDescription(
            key="energy_total",
            name="Energia gerada total",
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            icon="mdi:solar-power",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("energia_gerada_total"), {"MWh": 1000.0, "kWh": 1.0}
            ),
        ),
        SunWegSensorDescription(
            key="active_power",
            name="Potência ativa total",
            native_unit_of_measurement="kW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:flash",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("potencia_ativa_total"), {"kW": 1.0, "MW": 1000.0}
            ),
        ),
        SunWegSensorDescription(
            key="capacity",
            name="Capacidade total",
            native_unit_of_measurement="kW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-panel",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("capacidade_usinas"), {"kWp": 1.0, "kW": 1.0, "MWp": 1000.0}
            ),
        ),
        SunWegSensorDescription(
            key="trees_planted",
            name="Árvores plantadas",
            native_unit_of_measurement="arvore(s)",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:tree",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("arvores_plantadas"), None
            ),
        ),
        SunWegSensorDescription(
            key="km_driven_electric",
            name="Quilômetros elétricos",
            native_unit_of_measurement="km",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:car-electric",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("km_rodado_eletrico"), None
            ),
        ),
        SunWegSensorDescription(
            key="reduced_carbon_total",
            name="Redução de carbono total",
            native_unit_of_measurement="t",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:molecule-co2",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("reduz_carbono_total"), None
            ),
        ),
        SunWegSensorDescription(
            key="money_saved_today",
            name="Economia hoje",
            native_unit_of_measurement="R$",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:cash",
            value_fn=lambda total, resumo: _parse_numeric(
                # Remove currency symbol and parse numeric part
                total.get("total_economizado_hoje"), None
            ),
        ),
        SunWegSensorDescription(
            key="money_saved_total",
            name="Economia total",
            native_unit_of_measurement="R$",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:cash",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("total_economizado_acumulado"), None
            ),
        ),
        SunWegSensorDescription(
            key="number_of_plants",
            name="Quantidade de usinas",
            native_unit_of_measurement="usina(s)",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:factory",
            value_fn=lambda total, resumo: _parse_numeric(
                total.get("quantidade_usinas"), None
            ),
        ),
    ]

    # Define plant-specific sensors
    plant_sensors: list[SunWegSensorDescription] = [
        SunWegSensorDescription(
            key="plant_energy_day",
            name="Energia diária da usina",
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power",
            value_fn=lambda total, resumo: _parse_numeric(resumo.get("energiadia"), None),
        ),
        SunWegSensorDescription(
            key="plant_energy_month",
            name="Energia mensal da usina",
            native_unit_of_measurement="kWh",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-power",
            value_fn=lambda total, resumo: _parse_numeric(resumo.get("energia_mes"), None),
        ),
        SunWegSensorDescription(
            key="plant_power",
            name="Potência atual da usina",
            native_unit_of_measurement="kW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:flash",
            value_fn=lambda total, resumo: _parse_numeric(resumo.get("potencia"), None),
        ),
        SunWegSensorDescription(
            key="plant_capacity",
            name="Capacidade da usina",
            native_unit_of_measurement="kW",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:solar-panel",
            value_fn=lambda total, resumo: _parse_numeric(resumo.get("capacidade"), None),
        ),
        SunWegSensorDescription(
            key="plant_yield_day",
            name="Yield diário da usina",
            native_unit_of_measurement="",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:gauge",
            value_fn=lambda total, resumo: resumo.get("yield_dia"),
        ),
        SunWegSensorDescription(
            key="plant_yield_month",
            name="Yield mensal da usina",
            native_unit_of_measurement="",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:gauge",
            value_fn=lambda total, resumo: resumo.get("yield_mes"),
        ),
    ]

    entities: list[SensorEntity] = []
    # Create aggregated sensor entities
    for description in aggregated_sensors:
        entities.append(
            SunWegSensor(
                coordinator=coordinator,
                description=description,
                plant_id=plant_id,
                plant_name=plant_name,
                is_aggregated=True,
            )
        )
    # Create plant-specific sensor entities
    for description in plant_sensors:
        entities.append(
            SunWegSensor(
                coordinator=coordinator,
                description=description,
                plant_id=plant_id,
                plant_name=plant_name,
                is_aggregated=False,
            )
        )

    async_add_entities(entities)


class SunWegSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SunWEG sensor entity."""

    entity_description: SunWegSensorDescription

    def __init__(
        self,
        coordinator,
        description: SunWegSensorDescription,
        plant_id: str,
        plant_name: str,
        is_aggregated: bool,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._plant_id = plant_id
        self._plant_name = plant_name
        self._is_aggregated = is_aggregated
        # Unique ID combines the plant id with the sensor key to avoid collisions
        base_id = "total" if is_aggregated else plant_id
        self._attr_unique_id = f"sunweg_{base_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for Home Assistant UI."""
        # Aggregate sensors are associated with an integration-level device,
        # whereas plant-specific sensors reference the plant device.
        identifiers = {(DOMAIN, self._plant_id)}
        name = self._plant_name
        if self._is_aggregated:
            # Use a common device for aggregated metrics
            identifiers = {(DOMAIN, "aggregated")}
            name = "SunWEG Total"
        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="WEG",
            model="SunWEG",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        data: dict[str, Any] = self.coordinator.data
        resumo = data.get("resumo", {})
        total = data.get("totalizers", {})
        return self.entity_description.value_fn(total, resumo)

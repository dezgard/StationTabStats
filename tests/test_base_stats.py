from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


SOURCE = Path(__file__).parents[1] / "package_source" / "__init__.py"


def load_module():
    spec = importlib.util.spec_from_file_location("base_stats_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def visible_player_station_tabs(access, *_args, **_kwargs):
    return ["Main", "Control"] if access else ["Main"]


class InstallHost:
    def _draw_station_overlay(self):
        return visible_player_station_tabs(True, False)


def overlay(station_id="42", *, access=True) -> dict:
    return {
        "kind": "player_station",
        "body_rect": pygame.Rect(40, 40, 900, 680),
        "tab_bar_block_rect": pygame.Rect(40, 80, 900, 58),
        "data": {
            "attached_station_id": station_id,
            "station_name": "Test Bastion",
            "management_access": access,
            "max_shields": 1000,
            "shield_regen": 25,
            "max_energy": 800,
            "energy_regen": 40,
        },
    }


def host(station_id="42", *, access=True):
    return SimpleNamespace(
        _station_overlay=overlay(station_id, access=access),
        _username="Pilot",
        _ps_tab="Specs",
        _deployed_stations=[{
            "attached_station_id": station_id,
            "shields": 750,
            "max_shields": 1000,
            "shield_regen": 25,
            "energy": 600,
            "max_energy": 800,
            "energy_regen": 40,
        }],
        _ps_station_plugins=[{
            "slot_index": 0,
            "plugin_id": "targeting_matrix",
            "display_name": "Targeting Matrix",
            "def": {
                "bonuses": [
                    {"stat": "weapon_damage", "value": 0.25},
                    {"stat": "weapon_range", "value": 0.10},
                    {"stat": "fire_rate", "value": 0.20},
                ],
            },
        }],
        _ps_equipped_module_counts={
            "station_beam_cannon_mk1": 2,
            "station_energy_mk1": 1,
        },
        _ps_station_cargo=[{
            "item_key": "item:weapon:station_beam_cannon_mk1",
            "item_type": "station_beam_cannon_mk1",
            "item_category": "weapon",
            "display_name": "Station Beam Cannon Mk I",
            "stats": {
                "Damage": "100x2",
                "Damage Type": "Laser",
                "Fire Rate": "2.0/s (0.5s cd)",
                "Range": "1,000 u",
                "Energy Cost": "20 PU",
            },
        }],
        _s=lambda value: value,
        _instrument_font=lambda size, bold=False: pygame.font.Font(
            None, size + 5),
        _inventory_font=lambda size, bold=False: pygame.font.Font(
            None, size + 5),
    )


class BaseStatsTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.module = load_module()
        self.state = self.module._BaseStats(SimpleNamespace())

    def test_display_numbers_keep_grouping_without_redundant_zeroes(self):
        self.assertEqual("4", self.module._format_number(4.0))
        self.assertEqual("0.5", self.module._format_number(0.5))
        self.assertEqual("0.75", self.module._format_number(0.75))
        self.assertEqual("10,000", self.module._format_number(10000.0))
        self.assertEqual("12,345.7", self.module._format_number(12345.7))

    def test_specs_tab_is_management_only(self):
        original = lambda access, *_args, **_kwargs: ["Main", "Control"]
        wrapper = self.state._tabs_with_specs(original)

        self.assertEqual(["Main", "Control"], wrapper(False, False))
        self.assertEqual(
            ["Main", "Control", "Specs"], wrapper(True, False))

    def test_install_wraps_and_uninstall_restores_only_station_tabs(self):
        current = InstallHost()
        current._station_overlay = None
        current._ps_tab = "Main"
        original = visible_player_station_tabs

        self.state.install(current, pygame)
        self.assertEqual(
            ["Main", "Control", "Specs"],
            current._draw_station_overlay(),
        )
        self.state.uninstall()

        self.assertIs(original, visible_player_station_tabs)

    def test_weapon_telemetry_uses_station_stats_plugins_and_full_volley(self):
        current = host()
        rows = self.module.station_weapon_telemetry(
            current._ps_station_cargo,
            current._ps_equipped_module_counts,
            current._ps_station_plugins,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0]["shot_count"])
        self.assertEqual(2, rows[0]["quantity"])
        self.assertEqual(125, rows[0]["damage"])
        self.assertEqual(2.4, rows[0]["rate"])
        self.assertAlmostEqual(1200.0, rows[0]["dps"])
        self.assertAlmostEqual(1100.0, rows[0]["range"])
        self.assertAlmostEqual(96.0, rows[0]["energy_per_second"])
        self.assertEqual(["Targeting Matrix"], rows[0]["upgrades"])

    def test_plugin_details_keep_duplicate_slots_and_supplied_effects(self):
        plugins = [
            {
                "slot_index": slot,
                "plugin_id": "refined_capacity",
                "display_name": "Refined Station Capacity Plugin",
                "def": {"stats": {
                    "Hull Capacity": "+25%",
                    "Energy Bank": "+10%",
                }},
            }
            for slot in (0, 1)
        ]

        details = self.module.station_plugin_details(plugins)

        self.assertEqual([1, 2], [row["slot"] for row in details])
        self.assertEqual(
            ["Hull Capacity: +25%", "Energy Bank: +10%"],
            details[0]["effects"],
        )
        self.assertEqual(details[0]["name"], details[1]["name"])

    def test_plugin_bonus_list_is_shown_as_readable_percentages(self):
        plugins = [{
            "slot_index": 0,
            "plugin_id": "station_plugin_capacity_refined",
            "display_name": "Refined Station Capacity Plugin",
            "def": {"bonuses": [
                {"stat": "hull_capacity", "value": 0.53},
                {"stat": "energy_bank", "value": 1.38},
            ]},
        }]

        details = self.module.station_plugin_details(plugins)

        self.assertEqual(["Hull Capacity: +53%", "Energy Bank: +138%"],
                         details[0]["effects"])

    def test_snapshot_combines_live_banks_and_station_weapons(self):
        current = host()

        result = self.state.snapshot(current)

        self.assertEqual(750, result["shield"]["current"])
        self.assertEqual(600, result["energy"]["current"])
        self.assertAlmostEqual(1200, result["total_dps"])
        self.assertAlmostEqual(96, result["power_drain"])
        self.assertAlmostEqual(-56, result["net_power"])
        self.assertEqual(["Targeting Matrix"], result["plugins"])

    def test_station_weapon_data_is_owned_by_the_current_station_context(self):
        second = host("84")
        second._ps_station_cargo = []
        second._ps_equipped_module_counts = {}

        result = self.state.snapshot(second)

        self.assertEqual([], result["weapons"])
        self.assertIsNone(result["power_drain"])

    def test_missing_weapon_energy_stays_unavailable(self):
        current = host()
        del current._ps_station_cargo[0]["stats"]["Energy Cost"]

        result = self.state.snapshot(current)

        self.assertIsNone(result["weapons"][0]["energy_per_shot"])
        self.assertIsNone(result["power_drain"])
        self.assertIsNone(result["net_power"])

    def test_lost_management_access_returns_to_main(self):
        current = host(access=False)

        self.state.begin_frame(current)

        self.assertEqual("Main", current._ps_tab)

    def test_draw_smoke_and_scroll_are_confined_to_content(self):
        current = host()
        self.state.host = current
        self.state.pygame = pygame
        current._ps_equipped_module_counts = {
            f"station_cannon_{index}": 1 for index in range(8)
        }
        current._ps_station_cargo = [{
            "item_type": f"station_cannon_{index}",
            "item_category": "weapon",
            "display_name": f"Station Cannon {index}",
            "stats": {
                "Damage": "100",
                "Fire Rate": "1.0/s",
                "Range": "900 u",
                "Energy Cost": "10 PU",
            },
        } for index in range(8)]
        screen = pygame.Surface((1024, 768))

        self.state.draw(current, screen)

        self.assertIsNotNone(self.state.page_rect)
        self.assertGreater(self.state.scroll_max, 0)
        before = self.state.scroll
        event = SimpleNamespace(
            type=pygame.MOUSEWHEEL,
            y=-1,
            pos=self.state.page_rect.center,
        )
        self.assertTrue(self.state.handle_event(current, event))
        self.assertGreater(self.state.scroll, before)

    def test_registration_uses_loader_events_only(self):
        callbacks = {}
        api = SimpleNamespace(
            loader_api_version=1,
            logger=SimpleNamespace(info=Mock()),
            version="0.1",
            on=lambda event, callback, priority=0: callbacks.setdefault(
                event, callback),
        )

        self.module.register(api)

        self.assertEqual(
            {
                "client.startup", "client.frame.begin", "client.draw",
                "client.event", "loader.shutdown",
            },
            set(callbacks),
        )


if __name__ == "__main__":
    unittest.main()

"""Live specifications page for the currently docked player station."""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Iterable, Mapping


TAB_NAME = "Specs"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _format_number(value: Any, decimals: int = 2) -> str:
    """Keep thousands separators while dropping redundant decimal zeroes."""
    precision = max(0, int(decimals))
    text = f"{_number(value):,.{precision}f}"
    return text.rstrip("0").rstrip(".") if precision else text


def _station_key(value: Any) -> str:
    return str(value) if value is not None else ""


def _first_number(*values: Any) -> float | None:
    for value in values:
        result = _optional_number(value)
        if result is not None:
            return result
    return None


_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
_VOLLEY_RE = re.compile(
    r"[-+]?\d[\d,]*(?:\.\d+)?\s*[xX]\s*(\d+)")
_WEAPON_BONUS_LABELS = {
    "damage": "damage",
    "weapon damage": "damage",
    "weapon_damage": "damage",
    "range": "range",
    "weapon range": "range",
    "weapon_range": "range",
    "fire rate": "rate",
    "fire_rate": "rate",
    "rate of fire": "rate",
}
_PLUGIN_STAT_LABELS = {
    "cargo_capacity": "Hull Capacity",
    "hull_capacity": "Hull Capacity",
    "max_energy": "Energy Bank",
    "energy_bank": "Energy Bank",
    "energy_output": "Energy Regen",
    "energy_regen": "Energy Regen",
    "energy_recharge": "Energy Regen",
    "max_shields": "Shield Bank",
    "shield_bank": "Shield Bank",
    "shield_regen": "Shield Regen",
    "shield_recharge_rate": "Shield Regen",
    "_shield_recharge_rate": "Shield Regen",
    "weapon_damage": "Weapon Damage",
    "weapon_range": "Weapon Range",
    "fire_rate": "Fire Rate",
    "proj_tracking": "Projectile Tracking",
    "proj_speed": "Projectile Speed",
    "transference_power": "Transference Power",
    "sensor_detection": "Sensor Strength",
    "flat_damage_mitigation": "Flat Damage Mitigation",
    "visibility": "Visibility",
}


def _display_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return _optional_number(value)
    match = _NUMBER_RE.search(str(value))
    if match is None:
        return None
    return _optional_number(match.group(0).replace(",", ""))


def _stats(item: Mapping[str, Any]) -> Mapping[str, Any]:
    values = item.get("stats") or {}
    return values if isinstance(values, Mapping) else {}


def _stat_value(item: Mapping[str, Any], *labels: str) -> Any:
    folded = {
        str(key).casefold(): value for key, value in _stats(item).items()
    }
    for label in labels:
        if label.casefold() in folded:
            return folded[label.casefold()]
    return None


def _plugin_effects(plugin: Mapping[str, Any]) -> list[dict]:
    """Normalise authoritative plugin effects for display and projections."""
    definition = plugin.get("def") or {}
    if not isinstance(definition, Mapping):
        definition = {}

    supplied_bonuses = definition.get("bonuses")
    if not isinstance(supplied_bonuses, (list, tuple)):
        supplied_bonuses = plugin.get("bonuses")
    effects: list[dict] = []
    if isinstance(supplied_bonuses, (list, tuple)):
        for bonus in supplied_bonuses:
            if not isinstance(bonus, Mapping):
                continue
            stat = str(bonus.get("stat") or "").strip()
            fraction = _optional_number(bonus.get("value"))
            if not stat or fraction is None:
                continue
            key = stat.casefold()
            label = _PLUGIN_STAT_LABELS.get(
                key, stat.replace("_", " ").strip().title())
            percent = fraction * 100.0
            sign = "+" if percent > 0.0 else ""
            effects.append({
                "key": key,
                "fraction": fraction,
                "text": f"{label}: {sign}{_format_number(percent)}%",
            })
    if effects:
        return effects

    source = dict(definition)
    if not source.get("stats") and plugin.get("stats"):
        source["stats"] = plugin.get("stats")
    for label, raw in _stats(source).items():
        label_text = str(label).strip()
        raw_text = str(raw).strip()
        if not label_text or not raw_text:
            continue
        key = label_text.casefold()
        display_label = _PLUGIN_STAT_LABELS.get(
            key, label_text.replace("_", " ").title())
        fraction = None
        if "%" in raw_text:
            percent = _display_number(raw)
            if percent is not None:
                fraction = percent / 100.0
        effects.append({
            "key": key,
            "fraction": fraction,
            "text": f"{display_label}: {raw_text}",
        })
    return effects


def _station_plugin_bonuses(
        plugins: Iterable[Mapping[str, Any]]) -> tuple[dict[str, float], list[str]]:
    bonuses = {"damage": 0.0, "range": 0.0, "rate": 0.0}
    contributors: list[str] = []
    for plugin in plugins or ():
        if not isinstance(plugin, Mapping) or not plugin.get("plugin_id"):
            continue
        definition = plugin.get("def") or {}
        if not isinstance(definition, Mapping):
            definition = {}
        used = False
        for effect in _plugin_effects(plugin):
            key = _WEAPON_BONUS_LABELS.get(effect["key"])
            fraction = effect["fraction"]
            if key is None or fraction is None:
                continue
            bonuses[key] += fraction
            used = True
        if used:
            name = str(
                plugin.get("display_name")
                or definition.get("display_name")
                or plugin.get("plugin_id")
            ).strip()
            if name:
                contributors.append(name)
    return bonuses, contributors


def station_plugin_details(
        plugins: Iterable[Mapping[str, Any]]) -> list[dict]:
    """Return one honest, slot-ordered contribution sheet per plugin."""
    result: list[dict] = []
    for fallback_slot, plugin in enumerate(plugins or ()):
        if not isinstance(plugin, Mapping) or not plugin.get("plugin_id"):
            continue
        definition = plugin.get("def") or {}
        if not isinstance(definition, Mapping):
            definition = {}
        try:
            slot = int(plugin.get("slot_index", fallback_slot)) + 1
        except (TypeError, ValueError):
            slot = fallback_slot + 1
        name = str(
            plugin.get("display_name")
            or definition.get("display_name")
            or plugin.get("plugin_id")
        ).strip()
        effects = [effect["text"] for effect in _plugin_effects(plugin)]
        result.append({
            "slot": max(1, slot),
            "name": name or "Station Plugin",
            "effects": effects,
        })
    result.sort(key=lambda row: row["slot"])
    return result


def _looks_like_station_weapon(
        item_type: str, item: Mapping[str, Any]) -> bool:
    category = str(
        item.get("item_category") or item.get("category") or ""
    ).casefold()
    if category == "weapon":
        return True
    stat_labels = {str(label).casefold() for label in _stats(item)}
    if "damage" in stat_labels and (
            "fire rate" in stat_labels or "range" in stat_labels):
        return True
    folded_type = item_type.casefold()
    return folded_type.startswith("station_") and any(
        marker in folded_type
        for marker in ("cannon", "weapon", "transference"))


def station_weapon_telemetry(
        cargo_rows: Iterable[Mapping[str, Any]],
        equipped_counts: Mapping[str, Any],
        plugins: Iterable[Mapping[str, Any]]) -> list[dict]:
    """Project fitted station weapons from server-authored item stat sheets."""
    cargo_by_type: dict[str, Mapping[str, Any]] = {}
    for row in cargo_rows or ():
        if not isinstance(row, Mapping):
            continue
        item_type = str(
            row.get("item_type") or row.get("item_key") or "").strip()
        if item_type.startswith("item:"):
            item_type = item_type.rsplit(":", 1)[-1]
        if item_type and (
                item_type not in cargo_by_type or _stats(row)):
            cargo_by_type[item_type] = row

    bonuses, contributors = _station_plugin_bonuses(plugins)
    result: list[dict] = []
    for item_type, raw_count in (equipped_counts or {}).items():
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        item_type = str(item_type or "").strip()
        item = cargo_by_type.get(item_type, {})
        if count <= 0 or not _looks_like_station_weapon(item_type, item):
            continue

        damage_raw = _stat_value(item, "Damage")
        damage = max(0.0, _display_number(damage_raw) or 0.0)
        volley_match = _VOLLEY_RE.search(str(damage_raw or ""))
        shot_count = max(
            1, int(volley_match.group(1)) if volley_match else 1)
        rate = max(0.0, _display_number(
            _stat_value(item, "Fire Rate", "Rate of Fire")) or 0.0)
        weapon_range = max(0.0, _display_number(
            _stat_value(item, "Range", "Max Range")) or 0.0)
        energy = _display_number(_stat_value(item, "Energy Cost"))
        energy = None if energy is None else max(0.0, energy)

        effective_damage = damage * (1.0 + bonuses["damage"])
        effective_rate = rate * (1.0 + bonuses["rate"])
        effective_range = weapon_range * (1.0 + bonuses["range"])
        single_dps = effective_damage * shot_count * effective_rate
        result.append({
            "index": len(result) + 1,
            "item_type": item_type,
            "name": str(
                item.get("display_name")
                or item_type.replace("_", " ").title()).strip(),
            "quantity": count,
            "damage": effective_damage,
            "base_damage": damage,
            "rate": effective_rate,
            "base_rate": rate,
            "dps": single_dps * count,
            "range": effective_range,
            "base_range": weapon_range,
            "energy_per_shot": energy,
            "energy_per_second": (
                None if energy is None else energy * effective_rate * count),
            "shot_count": shot_count,
            "damage_type": str(
                _stat_value(item, "Damage Type") or "Unknown"),
            "upgrades": list(contributors),
        })
    result.sort(key=lambda row: (row["name"].casefold(), row["item_type"]))
    for index, row in enumerate(result, 1):
        row["index"] = index
    return result


def _time_to_full(current: float, maximum: float, regen: float) -> float | None:
    if regen <= 0.0 or maximum <= current:
        return 0.0 if maximum <= current else None
    return max(0.0, maximum - current) / regen


def _plugin_names(host: Any) -> list[str]:
    names: list[str] = []
    for plugin in getattr(host, "_ps_station_plugins", ()) or ():
        if not isinstance(plugin, Mapping) or not plugin.get("plugin_id"):
            continue
        definition = plugin.get("def") or {}
        name = str(
            plugin.get("display_name")
            or (definition.get("display_name")
                if isinstance(definition, Mapping) else "")
            or plugin.get("plugin_id")
        ).strip()
        if name:
            names.append(name)
    return names


class _BaseStats:
    def __init__(self, api: Any) -> None:
        self.api = api
        self.host = None
        self.pygame = None
        self.scroll = 0
        self.scroll_max = 0
        self.page_rect = None
        self.current_station = ""
        self.render_globals = None
        self.original_tabs = None
        self.tabs_wrapper = None

    @staticmethod
    def _find_method_owner(host_type: type, method_name: str) -> type | None:
        return next(
            (owner for owner in host_type.__mro__
             if method_name in owner.__dict__),
            None,
        )

    @staticmethod
    def _overlay(host: Any) -> dict | None:
        overlay = getattr(host, "_station_overlay", None)
        return (
            overlay if isinstance(overlay, dict)
            and overlay.get("kind") == "player_station" else None
        )

    @classmethod
    def _access(cls, host: Any) -> tuple[bool, str, dict]:
        overlay = cls._overlay(host)
        if overlay is None:
            return False, "", {}
        data = overlay.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        username = str(getattr(host, "_username", "") or "")
        is_owner = bool(data.get(
            "is_owner", data.get("owner_name") == username))
        can_manage = bool(data.get("management_access", is_owner))
        station_id = _station_key(
            data.get("attached_station_id", data.get("station_id")))
        return can_manage, station_id, data

    @staticmethod
    def _tabs_with_specs(
            original: Callable[..., Iterable[str]]) -> Callable[..., list[str]]:
        def wrapper(management_access: bool, *args, **kwargs) -> list[str]:
            tabs = list(original(management_access, *args, **kwargs))
            if management_access and TAB_NAME not in tabs:
                tabs.append(TAB_NAME)
            return tabs
        return wrapper

    def install(self, host: Any, pygame: Any) -> None:
        if self.host is not None:
            if self.host is host:
                return
            raise RuntimeError("Base Stats is already attached")

        render_owner = self._find_method_owner(
            type(host), "_draw_station_overlay")
        render_method = (
            None if render_owner is None
            else render_owner.__dict__.get("_draw_station_overlay"))
        render_globals = getattr(render_method, "__globals__", None)
        original_tabs = (
            None if render_globals is None
            else render_globals.get("visible_player_station_tabs"))
        if not callable(original_tabs):
            raise RuntimeError("compatible player-station tab provider is unavailable")

        tabs_wrapper = self._tabs_with_specs(original_tabs)

        self.host = host
        self.pygame = pygame
        self.render_globals = render_globals
        self.original_tabs = original_tabs
        self.tabs_wrapper = tabs_wrapper
        render_globals["visible_player_station_tabs"] = tabs_wrapper

    def uninstall(self) -> None:
        if (
            self.render_globals is not None
            and self.render_globals.get("visible_player_station_tabs")
            is self.tabs_wrapper
        ):
            self.render_globals["visible_player_station_tabs"] = self.original_tabs
        if self.host is not None and getattr(
                self.host, "_ps_tab", None) == TAB_NAME:
            self.host._ps_tab = "Main"
        self.host = None
        self.pygame = None
        self.page_rect = None
        self.render_globals = None

    def begin_frame(self, host: Any) -> None:
        can_manage, station_id, _data = self._access(host)
        if station_id != self.current_station:
            self.current_station = station_id
            self.scroll = 0
            self.scroll_max = 0
        if (not can_manage or not station_id) and getattr(
                host, "_ps_tab", None) == TAB_NAME:
            host._ps_tab = "Main"
        if getattr(host, "_ps_tab", None) != TAB_NAME:
            self.page_rect = None

    @staticmethod
    def _live_station(host: Any, station_id: str) -> dict:
        for station in getattr(host, "_deployed_stations", ()) or ():
            if not isinstance(station, dict):
                continue
            candidate = _station_key(
                station.get("attached_station_id", station.get("id")))
            if candidate == station_id:
                return station
        return {}

    def snapshot(self, host: Any) -> dict | None:
        can_manage, station_id, overlay_data = self._access(host)
        if not can_manage or not station_id:
            return None
        live = self._live_station(host, station_id)

        def value(*keys: str) -> float:
            for source in (live, overlay_data):
                for key in keys:
                    if key in source:
                        return _number(source.get(key), 0.0)
            return 0.0

        module_counts = dict(
            getattr(host, "_ps_equipped_module_counts", {}) or {})
        plugins = list(getattr(host, "_ps_station_plugins", ()) or ())
        weapons = station_weapon_telemetry(
            getattr(host, "_ps_station_cargo", ()) or (),
            module_counts,
            plugins,
        )
        known_power = [
            row["energy_per_second"] for row in weapons
            if row["energy_per_second"] is not None
        ]
        all_power_known = bool(weapons) and len(known_power) == len(weapons)
        power_drain = sum(known_power) if all_power_known else None
        energy_regen = value("energy_regen", "energy_output")

        shield_current = value("shields", "current_shields")
        shield_max = value("max_shields")
        shield_regen = value("shield_regen", "shield_recharge_rate")
        energy_current = value("energy", "current_energy")
        energy_max = value("max_energy")

        return {
            "station_id": station_id,
            "name": str(overlay_data.get(
                "station_name", live.get("display_name", "Player Station"))),
            "shield": {
                "current": shield_current,
                "maximum": shield_max,
                "regen": shield_regen,
                "time_to_full": _time_to_full(
                    shield_current, shield_max, shield_regen),
            },
            "energy": {
                "current": energy_current,
                "maximum": energy_max,
                "regen": energy_regen,
                "time_to_full": _time_to_full(
                    energy_current, energy_max, energy_regen),
            },
            "weapons": weapons,
            "total_dps": sum(row["dps"] for row in weapons),
            "power_drain": power_drain,
            "net_power": (
                None if power_drain is None else energy_regen - power_drain),
            "plugins": _plugin_names(host),
            "plugin_details": station_plugin_details(plugins),
            "module_counts": module_counts,
        }

    @staticmethod
    def _delta_text(base: float | None, effective: float,
                    suffix: str = "") -> str:
        effective_text = f"{effective:,.1f}{suffix}"
        if base is None or base <= 0.0 or abs(base - effective) < 0.005:
            return effective_text
        percent = (effective / base - 1.0) * 100.0
        return f"{base:,.1f} -> {effective:,.1f}{suffix} ({percent:+.1f}%)"

    @staticmethod
    def _format_time(seconds: float | None) -> str:
        if seconds is None:
            return "No regeneration"
        if seconds <= 0.0:
            return "Full"
        if seconds < 60.0:
            return f"{_format_number(seconds, 1)} seconds"
        return f"{int(seconds // 60)}m {int(seconds % 60):02d}s"

    @staticmethod
    def _fit(font: Any, text: str, width: int) -> str:
        text = str(text)
        if width <= 0 or font.size(text)[0] <= width:
            return text
        result = text
        while result and font.size(result + "...")[0] > width:
            result = result[:-1]
        return result.rstrip() + "..." if result else ""

    def _content_rect(self, host: Any):
        overlay = self._overlay(host)
        if overlay is None:
            return None
        body = overlay.get("body_rect")
        tab_bar = overlay.get("tab_bar_block_rect")
        if body is None or tab_bar is None:
            return None
        pygame = self.pygame
        scale = getattr(host, "_s", lambda value: value)
        body = pygame.Rect(body)
        tab_bar = pygame.Rect(tab_bar)
        pad = max(4, int(scale(10)))
        bottom = body.bottom - max(36, int(scale(80)))
        top = tab_bar.bottom
        return pygame.Rect(
            body.x + pad,
            top,
            max(1, body.w - pad * 2),
            max(1, bottom - top),
        )

    def draw(self, host: Any, screen: Any) -> None:
        if (getattr(host, "_ps_tab", None) != TAB_NAME
                or screen is None):
            self.page_rect = None
            return
        data = self.snapshot(host)
        rect = self._content_rect(host)
        if data is None or rect is None or rect.w < 160 or rect.h < 100:
            self.page_rect = None
            return
        self.page_rect = rect
        pygame = self.pygame
        scale = getattr(host, "_s", lambda value: value)
        s = lambda value: max(1, int(scale(value)))
        font_factory = getattr(host, "_instrument_font", None)
        body_factory = getattr(host, "_inventory_font", None)
        title_font = (
            font_factory(14, bold=True) if callable(font_factory)
            else pygame.font.SysFont("segoeui", 14, bold=True))
        section_font = (
            font_factory(11, bold=True) if callable(font_factory)
            else pygame.font.SysFont("segoeui", 11, bold=True))
        body_font = (
            body_factory(11, bold=True) if callable(body_factory)
            else pygame.font.SysFont("segoeui", 11, bold=False))
        small_font = (
            font_factory(9, bold=True) if callable(font_factory)
            else pygame.font.SysFont("segoeui", 9, bold=False))
        value_font = (
            body_factory(14, bold=True) if callable(body_factory)
            else pygame.font.SysFont("segoeui", 14, bold=True))

        background = (4, 10, 17)
        panel = (9, 19, 29)
        panel_alt = (11, 23, 35)
        border = (46, 80, 106)
        accent = (78, 185, 238)
        text = (205, 220, 230)
        dim = (132, 157, 175)
        good = (92, 218, 151)
        warning = (245, 179, 68)

        pygame.draw.rect(screen, background, rect)
        pygame.draw.rect(screen, border, rect, 1)
        old_clip = screen.get_clip()
        screen.set_clip(rect)
        x = rect.x + s(10)
        width = rect.w - s(20)
        y = rect.y + s(8) - self.scroll

        def draw_section_label(label: str) -> None:
            nonlocal y
            y += s(10)
            label_s = section_font.render(label.upper(), True, dim)
            if pygame.Rect(x, y, width, label_s.get_height()).colliderect(rect):
                screen.blit(label_s, (x, y))
                line_x = x + label_s.get_width() + s(9)
                pygame.draw.line(
                    screen, border,
                    (line_x, y + label_s.get_height() // 2),
                    (x + width, y + label_s.get_height() // 2))
            y += label_s.get_height() + s(7)

        def draw_card(card_rect: Any, label: str, value: str,
                      caption: str, caption_color: tuple) -> None:
            if not card_rect.colliderect(rect):
                return
            pygame.draw.rect(screen, panel, card_rect)
            pygame.draw.rect(screen, border, card_rect, 1)
            label_s = small_font.render(label.upper(), True, dim)
            value_s = value_font.render(
                self._fit(value_font, value, card_rect.w - s(18)),
                True, text)
            caption_s = small_font.render(
                self._fit(small_font, caption, card_rect.w - s(18)),
                True, caption_color)
            screen.blit(label_s, (card_rect.x + s(9), card_rect.y + s(7)))
            screen.blit(value_s, (
                card_rect.x + s(9), card_rect.y + s(24)))
            screen.blit(caption_s, (
                card_rect.x + s(9), card_rect.bottom
                - caption_s.get_height() - s(7)))

        def wrapped_lines(message: str, max_width: int) -> list[str]:
            words = str(message).split()
            if not words:
                return []
            lines: list[str] = []
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if small_font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
            return lines

        header = title_font.render(
            self._fit(title_font, f"BASE SPECS  /  {data['name']}", width),
            True, accent)
        screen.blit(header, (x, y))
        y += header.get_height() + s(3)
        sub = small_font.render(
            self._fit(
                small_font,
                "LIVE BANKS  /  FITTED WEAPON PROJECTION  /  SERVER DATA",
                width),
            True, dim)
        screen.blit(sub, (x, y))
        y += sub.get_height() + s(10)

        shield = data["shield"]
        energy = data["energy"]
        gap = s(8)
        card_h = max(s(72), value_font.get_linesize() + s(43))
        card_w = max(1, (width - gap * 2) // 3)
        cards = [
            pygame.Rect(x, y, card_w, card_h),
            pygame.Rect(x + card_w + gap, y, card_w, card_h),
            pygame.Rect(
                x + (card_w + gap) * 2, y,
                width - (card_w + gap) * 2, card_h),
        ]
        draw_card(
            cards[0], "Shield bank",
            f"{shield['current']:,.0f} / {shield['maximum']:,.0f}",
            f"+{_format_number(shield['regen'])} HP/s  |  "
            f"{self._format_time(shield['time_to_full'])}", accent)
        draw_card(
            cards[1], "Energy bank",
            f"{energy['current']:,.0f} / {energy['maximum']:,.0f}",
            f"+{_format_number(energy['regen'])} PU/s  |  "
            f"{self._format_time(energy['time_to_full'])}", good)
        power_caption = (
            "POWER DATA UNAVAILABLE" if data["power_drain"] is None
            else f"{_format_number(data['power_drain'])} PU/s DRAW")
        draw_card(
            cards[2], "Weapon output",
            f"{_format_number(data['total_dps'], 1)} DPS",
            power_caption,
            warning if data["power_drain"] is None
            or (data["net_power"] is not None and data["net_power"] < 0)
            else good)
        y += card_h

        weapons = data["weapons"]
        draw_section_label("Fitted station weapons")
        if not weapons:
            empty_h = max(s(42), body_font.get_linesize() + s(18))
            empty_rect = pygame.Rect(x, y, width, empty_h)
            if empty_rect.colliderect(rect):
                pygame.draw.rect(screen, panel, empty_rect)
                pygame.draw.rect(screen, border, empty_rect, 1)
                empty_s = body_font.render(
                    "NO FITTED STATION WEAPON STATS RECEIVED", True, warning)
                screen.blit(empty_s, (
                    empty_rect.x + s(9),
                    empty_rect.centery - empty_s.get_height() // 2))
            y += empty_h + s(5)
        for weapon in weapons:
            row_h = max(s(52), body_font.get_linesize() * 2 + s(14))
            row_rect = pygame.Rect(x, y, width, row_h)
            if row_rect.colliderect(rect):
                pygame.draw.rect(
                    screen, panel_alt if weapon["index"] % 2 else panel,
                    row_rect)
                pygame.draw.rect(screen, border, row_rect, 1)
                name_w = max(s(150), int(width * 0.36))
                name_text = self._fit(
                    body_font,
                    f"{weapon['quantity']}x  {weapon['name'].upper()}",
                    name_w - s(16))
                name_s = body_font.render(name_text, True, text)
                type_s = small_font.render(
                    str(weapon["damage_type"]).upper(), True, dim)
                screen.blit(name_s, (row_rect.x + s(9), row_rect.y + s(8)))
                screen.blit(type_s, (
                    row_rect.x + s(9), row_rect.bottom
                    - type_s.get_height() - s(7)))
                damage_value = f"{weapon['damage']:,.0f}"
                if weapon["shot_count"] > 1:
                    damage_value += f"x{weapon['shot_count']}"
                values = [
                    ("DMG", damage_value, text),
                    ("ROF", f"{_format_number(weapon['rate'])}/s", text),
                    ("DPS", f"{weapon['dps']:,.0f}", good),
                    ("RANGE", f"{weapon['range']:,.0f} u", text),
                    ("POWER", "N/A" if weapon["energy_per_second"] is None
                     else f"{weapon['energy_per_second']:,.0f}/s",
                     warning if weapon["energy_per_second"] is None else good),
                ]
                value_x = row_rect.x + name_w
                value_w = max(1, (row_rect.w - name_w) // len(values))
                for column, (label, value, color) in enumerate(values):
                    col_x = value_x + value_w * column
                    label_s = small_font.render(label, True, dim)
                    value_s = body_font.render(
                        self._fit(body_font, value, value_w - s(6)),
                        True, color)
                    screen.blit(label_s, (col_x, row_rect.y + s(6)))
                    screen.blit(value_s, (
                        col_x, row_rect.bottom - value_s.get_height() - s(7)))
            y += row_h + s(5)

        draw_section_label("Station plugins")
        plugin_details = data["plugin_details"]
        if not plugin_details:
            none_s = body_font.render("NO STATION PLUGINS FITTED", True, dim)
            screen.blit(none_s, (x + s(8), y + s(6)))
            y += none_s.get_height() + s(16)
        for plugin in plugin_details:
            effect_text = (
                "  |  ".join(plugin["effects"])
                if plugin["effects"] else
                "No bonus details supplied by the server")
            effect_lines = wrapped_lines(effect_text, width - s(18))
            row_h = max(
                s(48), body_font.get_linesize() + s(14)
                + len(effect_lines) * (small_font.get_linesize() + s(2)))
            row_rect = pygame.Rect(x, y, width, row_h)
            if row_rect.colliderect(rect):
                pygame.draw.rect(screen, panel, row_rect)
                pygame.draw.rect(screen, border, row_rect, 1)
                pygame.draw.rect(
                    screen, accent,
                    (row_rect.x, row_rect.y, s(3), row_rect.h))
                slot_s = small_font.render(
                    f"SLOT {plugin['slot']}", True, dim)
                name_x = row_rect.x + s(64)
                name_s = body_font.render(
                    self._fit(
                        body_font, plugin["name"].upper(),
                        row_rect.right - name_x - s(8)),
                    True, text)
                screen.blit(slot_s, (row_rect.x + s(10), row_rect.y + s(8)))
                screen.blit(name_s, (name_x, row_rect.y + s(7)))
                effect_y = row_rect.y + body_font.get_linesize() + s(9)
                effect_color = good if plugin["effects"] else warning
                for line in effect_lines:
                    line_s = small_font.render(line, True, effect_color)
                    screen.blit(line_s, (row_rect.x + s(10), effect_y))
                    effect_y += small_font.get_linesize() + s(2)
            y += row_h + s(5)

        counts = data["module_counts"]
        module_total = sum(
            max(0, int(count)) for count in counts.values()
            if isinstance(count, (int, float)))
        module_s = small_font.render(
            f"FITTED MODULES  {module_total:,} ACROSS {len(counts):,} TYPES",
            True, dim)
        screen.blit(module_s, (x, y + s(3)))
        y += module_s.get_height() + s(12)

        content_height = max(0, y + self.scroll - rect.y + s(8))
        self.scroll_max = max(0, content_height - rect.h)
        self.scroll = max(0, min(self.scroll, self.scroll_max))
        screen.set_clip(old_clip)

        if self.scroll_max > 0:
            track = pygame.Rect(
                rect.right - s(5), rect.y + s(3), s(3), rect.h - s(6))
            pygame.draw.rect(screen, (16, 30, 42), track)
            thumb_h = max(s(24), int(track.h * rect.h / content_height))
            travel = max(0, track.h - thumb_h)
            thumb_y = track.y + int(
                travel * self.scroll / max(1, self.scroll_max))
            pygame.draw.rect(
                screen, accent,
                pygame.Rect(track.x, thumb_y, track.w, thumb_h))

    def handle_event(self, host: Any, event: Any) -> bool:
        if (getattr(host, "_ps_tab", None) != TAB_NAME
                or self.page_rect is None):
            return False
        pygame = self.pygame
        event_type = getattr(event, "type", None)
        if event_type != getattr(pygame, "MOUSEWHEEL", None):
            return False
        point = getattr(event, "pos", None)
        if point is None:
            point = pygame.mouse.get_pos()
        if not self.page_rect.collidepoint(point):
            return False
        wheel_y = int(getattr(event, "y", 0) or 0)
        self.scroll = max(
            0, min(self.scroll_max, self.scroll - wheel_y * 42))
        return True


def register(api: Any) -> None:
    """Register Base Stats with Star Empire Mod Loader API 1."""
    if getattr(api, "loader_api_version", 0) < 1:
        raise RuntimeError("Base Stats requires loader API 1")
    state = _BaseStats(api)

    def startup(*, host: Any, pygame: Any, **_kwargs) -> bool:
        state.install(host, pygame)
        api.logger.info("BASE_STATS_STARTED version=%s", api.version)
        return True

    def begin_frame(*, host: Any, **_kwargs) -> None:
        if state.host is host:
            state.begin_frame(host)

    def draw(*, host: Any, screen: Any, **_kwargs) -> None:
        if state.host is host:
            state.draw(host, screen)

    def event(*, host: Any, event: Any, **_kwargs) -> bool:
        return state.host is host and state.handle_event(host, event)

    api.on("client.startup", startup, priority=475)
    api.on("client.frame.begin", begin_frame, priority=475)
    api.on("client.draw", draw, priority=475)
    api.on("client.event", event, priority=475)
    api.on(
        "loader.shutdown",
        lambda *_args, **_kwargs: state.uninstall(),
        priority=475,
    )


__all__ = ("register",)

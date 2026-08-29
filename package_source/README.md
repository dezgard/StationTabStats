# Star Empire Base Stats

Base Stats adds a compact **Specs** dashboard to your station window. It puts
the station's shield, energy, fitted weapon and plugin figures together so you
can see what the current base setup is doing.

## What it shows

- Three summary cards for shield bank, energy bank and weapon output.
- Current and maximum banks, regeneration and recharge time.
- One compact row per fitted station weapon showing damage, rate of fire, DPS,
  range and electrical drain.
- Projected combined weapon DPS and electrical drain.
- Weapon energy cost when Star Empire supplies it.
- Every installed station plugin shown by slot, including duplicate plugins.
- Each plugin's supplied bonuses listed directly beneath its name.
- Fractional plugin definitions converted into readable percentages.
- A compact fitted-module count without the previous long module-name list.
- Base and plugin-adjusted weapon values when the plugin stat sheet supplies
  the relevant bonus.
- Readable thousands separators without unnecessary trailing decimal zeroes.

## Using the mod

Install and enable the `.semod` with Star Empire Mod Manager. Open a station
you own or manage, then select **Specs**. Use the mouse wheel over the page to
scroll through fitted weapons and modifiers.

From v0.1 onward, the Mod Manager can check the official
`dezgard/StationTabStats` GitHub releases for newer versions.

The tab follows the game's normal station rules. It only appears when you have
management access, and it only reports the station you currently have open.
Scroll over the page to reach additional weapons and plugin rows.

## Notes

This is a display mod. It does not change station stats, weapons, augments,
permissions or server data.

Some Star Empire weapon records do not currently include an energy cost. The
mod labels that value as unavailable instead of estimating it.

If a plugin does not include bonus details in the server-supplied stat sheet,
the dashboard says so instead of guessing what the plugin changes.

Declared weapon damage, range and fire-rate bonuses are included in the
weapon projections. Other plugin effects are shown as percentages because the
server does not always provide the unmodified station value needed for an
honest flat-number comparison.

Shield and energy banks are live server values. Weapon figures are projections
from the fitted station items and the station-plugin stat sheets supplied by
the server. The mod does not use your ship's turret data or apply hidden bonus
rules that the client cannot verify.

Tested with Star Empire 0.4.91 using Mod Loader API 1.

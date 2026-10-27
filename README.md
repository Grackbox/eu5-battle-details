# Battle Details

EU5 mod, on the Steam Workshop: https://steamcommunity.com/sharedfiles/filedetails/?id=3828272670

The battle result popup gets a Battle details button: per side the commander with his traits, dice modifiers, morale at
the start, discipline, tactics, experience, levy combat efficiency, frontage, combined arms and the units by type, and
between the sides the course of the battle day by day (rolls, flanks falling and filling again, armies joining). A
Battle Journal (from the Military panel or the peace popup) keeps the last 20 battles of the session. Land battles
only; interface only, no script.

The game keeps none of this after a battle, so a hidden widget (`bd_recorder.gui`) copies what the battle window
shows into GUI variables once a day while one of the player's armies fights. They last until the game is closed.

## Files

- `bd_build.py`: builds the mod. `python bd_build.py` writes the local copy
  (`Documents/Paradox Interactive/Europa Universalis V/mod/battle_details`, named "Battle Details [LOCAL]", with test
  lines); `python bd_build.py --release` writes the Workshop copy to `release/battle_details` (not in the repo).
  The vanilla `battle_result.gui`, `unit_overview.gui` and `messages.gui` are patched from the game's files.
- `description.txt`: the Workshop description.
- `make_cover.py`: builds `cover.png` (the Workshop preview) from `cover_full.png`.
- `screenshots/`: the page's gallery.
- `shelved/regiment_damage.py`: the damage per regiment and Other kills, taken out (it slowed big battles down); how to
  bring it back is in its header.

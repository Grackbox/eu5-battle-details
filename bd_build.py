"""Builds the EU5 mod "Battle Details" into the local mod folder.

The battle result popup gets a "Battle details" button that lays the battle open, as it stood on its last day: per side
the dice and what makes them, morale, discipline and military tactics with their sources, combined arms and the units by
category; the battlefield; and the whole chain of dice rolls. The battle window itself is left as it is.

The game keeps none of this after a battle (its result holds only losses, commanders and participants), and scripts
can't see the dice. So a hidden widget (bd_recorder.gui) copies what the battle window shows into GUI variables once a
day for every battle of the player's armies, keyed by the battle's name: they last until the game is closed.

The vanilla result popup is patched from the game's file (not Glorp UI's).

`python bd_build.py` builds the local copy, with the test lines (the battles seen this session, in the popup of a
battle not recorded); `--release` builds the Workshop copy without them into release/battle_details.
"""
import collections
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = "--release" in sys.argv
DEBUG = not RELEASE
OUT = (os.path.join(HERE, "release", "battle_details") if RELEASE
       else os.path.expanduser("~/Documents/Paradox Interactive/Europa Universalis V/mod/battle_details"))
GAME = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
LANGS = ["english", "russian", "german", "french", "spanish", "braz_por", "polish", "turkish", "japanese", "korean", "simp_chinese"]

TEXT = {
    "english": {
        "BD_DETAILS": "Battle details",
        "BD_HIDE": "Losses",
        "BD_LOG_NOTE": "A new roll every 4 days. Squares: the side's flanks when one fell or filled again (green fighting, yellow waiting, red empty). Green: armies that joined.",
        "BD_NO_LOG": "No rolls yet.",
        "BD_NO_RECORD": "Not recorded: none of our armies fought in it, or the game was loaded during it.",
        "BD_STACK_WIPE": "Stack wipe: the army was destroyed at once, with no days of fighting.",
        "BD_MORR_TITLE": "Recovery a day:",
        "BD_MORMV_TITLE": "Lost to moving a day:",
        "BD_BASE_TAG": "Base Value for Every",
        "BD_MORAT_TITLE": "Lost to [attrition|e] a day:",
        "BD_MORALE_START": "[morale|E] at the start (of max)",
        "BD_DICE_MODS": "[dice|E] modifiers",
        "BD_NO_DICE_MODS": "No modifiers: the roll counts as it fell.",
        "BD_RIVER_TERRAIN": "River",
        "BD_TERRAIN_TITLE": "Terrain",
        "BD_EXPERIENCE": "[experience|E] (country average)",
        "BD_CAME": "#P +",
        "BD_CAME_END": "#!",
        "BD_LOSSES_TT": "Lost: [BattleUnitStats.GetDestroyed|K1] killed, [BattleUnitStats.GetImprisoned|K1] captured.",
        "BD_LEFT": "Left at the end of the battle",
        "BD_POWER_TT": "Kills a day at an average roll, before the enemy's [discipline|e]. A rough guide.",
        "BD_LEVY_TAG": "@levy!",
        "BD_TAIL": "#!@army_strength",
        "BD_TAIL2": "@army_strength",
        "BD_JOURNAL": "Battle Journal",
        "BD_JOURNAL_TT": "The last 20 battles of this session.",
        "BD_JOURNAL_NOTE": "The last 20 battles of our armies since the game was started or loaded: a save doesn't keep them.",
        "BD_JOURNAL_EMPTY": "No battles of our armies yet in this session.",
        "BD_JOURNAL_ROW_TT": "Open the battle's report.",
        "BD_LOST_PRE": "Lost: ",
        "BD_LOST_MID": " killed, ",
        "BD_LOST_END": " captured.",
        "BD_NO_OUTCOME": "#weak —#!",
        "BD_MOST": " (most types)",
        "BD_NO_COMMANDER": "none",
        "BD_TRAITS": "General traits: ",
        "BD_NO_TRAITS": "No traits noted.",
        "BD_WON": "#P Victory#!",
        "BD_LOST": "#N Defeat#!",
        "BD_SEP": "\\n",
        "BD_BOMBARD": " ($game_concept_bombard_phase$)",
        "BD_BOMBARD_TT": "A roll of the [bombard_phase|E].",
        "BD_RIVER": ", $game_concept_river_crossing$",
        "BD_STRAIT": ", strait crossing",
        "BD_LANDING": ", landing from the sea",
    },
    "russian": {
        "BD_DETAILS": "Подробности боя",
        "BD_HIDE": "Потери",
        "BD_LOG_NOTE": "Новый бросок каждые 4 дня. Квадраты: фланги стороны, когда один рухнул или заполнился снова (зелёный в бою, жёлтый ждёт, красный пуст). Зелёным: пришедшие армии.",
        "BD_NO_LOG": "Бросков ещё не было.",
        "BD_NO_RECORD": "Не записан: наших армий в бою не было, или игру загрузили, пока он шёл.",
        "BD_STACK_WIPE": "Разгром без боя: армию уничтожили сразу, дней боя не было.",
        "BD_MORR_TITLE": "Восстановление в день:",
        "BD_MORMV_TITLE": "Потери при перемещении в день:",
        "BD_BASE_TAG": "Базовое значение для каждой",
        "BD_MORAT_TITLE": "Потери от [attrition|e] в день:",
        "BD_MORALE_START": "[morale|E] в начале (из макс.)",
        "BD_DICE_MODS": "Модификаторы [dice|e]",
        "BD_NO_DICE_MODS": "Модификаторов нет: бросок идёт как выпал.",
        "BD_RIVER_TERRAIN": "Река",
        "BD_TERRAIN_TITLE": "Местность",
        "BD_EXPERIENCE": "[experience|E] (средний по стране)",
        "BD_CAME": "#P +",
        "BD_CAME_END": "#!",
        "BD_LOSSES_TT": "Потери: [BattleUnitStats.GetDestroyed|K1] убито, [BattleUnitStats.GetImprisoned|K1] в плену.",
        "BD_LEFT": "Осталось к концу боя",
        "BD_POWER_TT": "Убитых в день при среднем броске, без учёта [discipline|e] противника. Ориентир.",
        "BD_LEVY_TAG": "@levy!",
        "BD_TAIL": "#!@army_strength",
        "BD_TAIL2": "@army_strength",
        "BD_JOURNAL": "Журнал сражений",
        "BD_JOURNAL_TT": "Последние 20 боёв этой сессии.",
        "BD_JOURNAL_NOTE": "Последние 20 боёв наших армий с запуска или загрузки игры: в сохранение не попадают.",
        "BD_JOURNAL_EMPTY": "В этой сессии наши армии ещё не сражались.",
        "BD_JOURNAL_ROW_TT": "Открыть отчёт о бое.",
        "BD_LOST_PRE": "Потери: ",
        "BD_LOST_MID": " убито, ",
        "BD_LOST_END": " в плену.",
        "BD_NO_OUTCOME": "#weak —#!",
        "BD_MOST": " (большинство типов)",
        "BD_NO_COMMANDER": "нет",
        "BD_TRAITS": "Черты полководца: ",
        "BD_NO_TRAITS": "Черты не записаны.",
        "BD_WON": "#P Победа#!",
        "BD_LOST": "#N Поражение#!",
        "BD_SEP": "\\n",
        "BD_BOMBARD": " ($game_concept_bombard_phase$)",
        "BD_BOMBARD_TT": "Бросок [bombard_phase|E].",
        "BD_RIVER": ", $game_concept_river_crossing$",
        "BD_STRAIT": ", переправа через пролив",
        "BD_LANDING": ", высадка с моря",
    },
}

SIDES = (("a", "Attacker"), ("d", "Defender"))


def write(path, text, bom=True):
    full = os.path.join(OUT, *path.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\n") as fh:
        fh.write(text)


def game_gui(name):
    with open(os.path.join(GAME, "in_game", "gui", name), encoding="utf-8-sig") as fh:
        return fh.read()


def indent(text, tabs):
    return "".join("\t" * tabs + line + "\n" if line else "\n" for line in text.splitlines())


# GUI variables: 'bd_<name>_<battle name>'. The recorder names the battle by Combat.GetNameWithNoTooltip, the result
# popup by BattleResult.GetName.
LIVE = "Combat.GetNameWithNoTooltip"
DONE = "BattleResultMessage.GetBattleResult.GetName"


def key(name, battle):
    return f"Concatenate('bd_{name}_', {battle})"


def get(name, battle):
    return f"GetVariableSystem.Get({key(name, battle)})"


def categories():
    """The unit categories (in_game/common/unit_categories), in the game's order."""
    folder = os.path.join(GAME, "in_game", "common", "unit_categories")
    cats = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt") and name != "readme.txt":
            with open(os.path.join(folder, name), encoding="utf-8-sig") as fh:
                cats += re.findall(r"^([a-z_]+)\s*=\s*\{", fh.read(), re.M)
    if not cats:
        raise SystemExit("no unit categories found")
    return cats


def pct(x):
    """A fixed point value as a whole percent with its sign: 0.152 -> '+15%'."""
    return (f"Concatenate3(Select_CString(GreaterThan_CFixedPoint({x}, '(CFixedPoint)0'), '+', ''), "
            f"ToString_int32(FixedPointToInt(Multiply_CFixedPoint({x}, '(CFixedPoint)100'))), '%')")


def morale_cost(x):
    """A morale cost a day (a fraction of the maximum) as a percent with two decimals, '' when nothing: 0.0123 ->
    '-1.23%'."""
    return (f"Select_CString(GreaterThan_CFixedPoint({x}, '(CFixedPoint)0'), "
            f"Concatenate3('-', {dec2(f'Multiply_CFixedPoint({x}, {chr(39)}(CFixedPoint)100{chr(39)})')}, '%'), '')")


def dec2(x):
    """A fixed point value of zero or more with two decimals: 2.5 -> '2.50'."""
    whole = f"FixedPointToInt({x})"
    frac = f"Subtract_int32(FixedPointToInt(Multiply_CFixedPoint({x}, '(CFixedPoint)100')), Multiply_int32({whole}, '(int32)100'))"
    return (f"Concatenate3(ToString_int32({whole}), '.', Select_CString(LessThan_int32({frac}, '(int32)10'), "
            f"Concatenate('0', ToString_int32({frac})), ToString_int32({frac})))")


def modifier(side, name):
    """A side's discipline or military tactics in this battle, its commander included (as the game's battle window)."""
    return f"{side}.GetCommander.GetCombatModifierNoFormat({side}.GetCountry, '{name}', Combat.IsNavalCombat)"


def sources(side, name):
    return f"{side}.GetCommander.GetCombatModifierDescription({side}.GetCountry, '{name}', Combat.IsNavalCombat)"


TERRAIN = ("Concatenate(Concatenate3(Combat.GetLocation.GetNameWithNoTooltip, ' — ', "
           "Concatenate3(Combat.GetLocation.GetTopography.GetNameWithNoTooltip, ', ', Combat.GetLocation.GetVegetation.GetNameWithNoTooltip)), "
           "Concatenate3(Select_CString(Combat.IsRiverCrossing, Localize('BD_RIVER'), ''), "
           "Select_CString(Combat.IsStraitCrossing, Localize('BD_STRAIT'), ''), "
           "Select_CString(Combat.IsSeaLanding, Localize('BD_LANDING'), '')))")

# a roll: both sides' dice (with their modifiers) and the phase; a new one is noted when this changes
ROLL = ("Concatenate(Concatenate3(ToString_int32(Combat.GetAttacker.GetDiceWithModifiers), ':', "
        "ToString_int32(Combat.GetDefender.GetDiceWithModifiers)), Select_CString(Combat.IsInBombardPhase, 'b', 'c'))")
def short_date():
    """'22 Apr' from the date's text ('22 April, 1337'): the month by its name (the engine's own month names), the day
    as the number it starts with ('~2 ' is not in '~22 April', so just one day matches). Each one is a flat join of
    checks: nested 31 deep, the game refused the statement."""
    months = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December")
    month = join([f"Select_CString(StringContains(GetDateString, Localize('CW_DATE_{m}')), "
                  f"Localize('CW_DATE_{'May' if m == 'May' else m[:3]}'), '')" for m in months])
    day = join([f"Select_CString(StringContains(Concatenate('~', GetDateString), '~{d} '), '{d}', '')" for d in range(1, 32)])
    return f"Concatenate3({day}, ' ', {month})"


ENTRY = ("Concatenate(Concatenate3(ToString_int32(Combat.GetAttacker.GetDiceWithModifiers), ' : ', "
         "ToString_int32(Combat.GetDefender.GetDiceWithModifiers)), Select_CString(Combat.IsInBombardPhase, Localize('BD_BOMBARD'), ''))")
BATTLE_ID = "Concatenate3(Combat.GetKey, '#', ToString_int32(Combat.GetID))"
# The running sums (damage) go by the battle's name and id: a second battle under the same name (at the same place)
# starts them afresh. The result popup knows the battle only by its name, and takes the id from the battle's notes.
# a revolt and a civil war are wars; risen rebels are added in case they fight before their war starts
AT_WAR = "Or(GetPlayer.GetDiplomacy.IsAtWar, Or(GetPlayer.HasActiveRebels, GetPlayer.IsInCivilWar))"
# The game gives a later battle the same id again (seen: two battles of Fràra both 33554433), so a battle is told by its
# name and id and the day it was first noted: one whose name and id were last noted today or on one of the two days
# before (bd_today / bd_yesterday, see battle_steps) goes on; else it is a new battle with a key of its own. Every chain of
# notes works it out first (battle_steps), so it doesn't matter which runs first; the result popup takes it from the
# battle's 'id' note.
BATTLE_SLOT = f"Concatenate({LIVE}, {BATTLE_ID})"
SEEN_DAY = f"GetVariableSystem.Get(Concatenate('bd_seenday_', {BATTLE_SLOT}))"
GOES_ON = (f"And(Not(StringIsEmpty({SEEN_DAY})), Or(EqualTo_string({SEEN_DAY}, GetDateString), "
           f"Or(EqualTo_string({SEEN_DAY}, GetVariableSystem.Get('bd_today')), EqualTo_string({SEEN_DAY}, GetVariableSystem.Get('bd_yesterday')))))")
SUMS_LIVE = "GetVariableSystem.Get('bd_tmp_battle')"
# The popup's battle. Its name may be that of a later battle at the same place by the time the popup is opened, so the
# last battles of each name are kept (bd_id<n>_<name>, newest first), each with its sides' countries (atg, dtg), and the
# popup takes the newest of them with its own two countries (the newest of all if none). Worked out as the popup opens
# into bd_popup (popup_match), and read from there.
NAMED = 5
SIDE_TAGS = {"atg": "Combat.GetAttacker.GetCountry.GetTag", "dtg": "Combat.GetDefender.GetCountry.GetTag"}


def popup_match():
    result = "BattleResultMessage.GetBattleResult"
    own = {"atg": f"{result}.GetAttacker.GetMainParticipant.GetTag", "dtg": f"{result}.GetDefender.GetMainParticipant.GetTag"}
    cand = lambda n: f"GetVariableSystem.Get(Concatenate('bd_id{n}_', {DONE}))"
    pick = cand(1)
    for n in range(NAMED, 0, -1):
        ok = f"And(EqualTo_string({get('atg', cand(n))}, {own['atg']}), EqualTo_string({get('dtg', cand(n))}, {own['dtg']}))"
        pick = f"Select_CString({ok}, {cand(n)}, {pick})"
    # first of all one noted on the last day or the one before that the notes ran: the popup comes as its battle ends,
    # and the countries noted are those of the sides' leading armies, an ally's at times, not the popup's
    for n in range(NAMED, 0, -1):
        day = get("day", cand(n))
        recent = (f"And(Not(StringIsEmpty({day})), Or(EqualTo_string({day}, GetVariableSystem.Get('bd_today')), "
                  f"EqualTo_string({day}, GetVariableSystem.Get('bd_yesterday'))))")
        pick = f"Select_CString({recent}, {cand(n)}, {pick})"
    return pick


def named_steps():
    """on_start calls of the recorder: a new battle goes first in the list of its name; each day its sides' countries."""
    new = "StringIsEmpty(GetVariableSystem.Get('bd_tmp_same'))"
    slot = lambda n: f"Concatenate('bd_id{n}_', {LIVE})"
    steps = [f"GetVariableSystem.Set({slot(n)}, Select_CString({new}, GetVariableSystem.Get({slot(n - 1)}), GetVariableSystem.Get({slot(n)})))"
             for n in range(NAMED, 1, -1)]
    steps.append(f"GetVariableSystem.Set({slot(1)}, Select_CString({new}, {SUMS_LIVE}, GetVariableSystem.Get({slot(1)})))")
    return steps + [f"GetVariableSystem.Set({key(k, SUMS_LIVE)}, {v})" for k, v in SIDE_TAGS.items()]


SUMS_DONE = "GetVariableSystem.Get('bd_popup')"


def battle_steps():
    """The battle's key into bd_tmp_battle. First the last two days any chain of notes ran (a widget of its own for
    them never ran again: its condition held from before the game loaded)."""
    token = f"Concatenate('bd_token_', {BATTLE_SLOT})"
    today = "GetVariableSystem.Get('bd_today')"
    return [f"GetVariableSystem.Set('bd_yesterday', Select_CString(EqualTo_string({today}, GetDateString), "
            f"GetVariableSystem.Get('bd_yesterday'), {today}))",
            "GetVariableSystem.Set('bd_today', GetDateString)",
            f"GetVariableSystem.Set('bd_tmp_battle', Select_CString({GOES_ON}, GetVariableSystem.Get({token}), "
            f"Concatenate3({BATTLE_SLOT}, '@', GetDateString)))",
            f"GetVariableSystem.Set({token}, {SUMS_LIVE})",
            f"GetVariableSystem.Set(Concatenate('bd_seenday_', {BATTLE_SLOT}), GetDateString)"]


def cat_key(s, category, battle, what="cat"):
    """A unit category's note goes by the category's name: the result popup knows its categories only as objects."""
    return f"Concatenate3('bd_{s}_{what}_', {category}.GetNameWithNoTooltip, {battle})"


# set in the recorder before the notes: '1' while the battle goes on (as for the morale), '' on its first day
SAME = "Not(StringIsEmpty(GetVariableSystem.Get('bd_tmp_same')))"


def kept(k, new):
    """A note that keeps the first value the battle gave it: a later day can't empty it (a category all killed)."""
    old = f"GetVariableSystem.Get({k})"
    return f"Select_CString(And({SAME}, Not(StringIsEmpty({old}))), {old}, {new})"


def snapshots(s, side):
    """key -> value copied for one side of a battle each day."""
    # only the categories the side has (the tooltip of a missing one says "No ... units in this Army"): as the battle
    # began (the first day a category is there), and as it ended (the last day)
    cats = {}
    for c in categories():
        category = f"GetSubUnitCategory('{c}')"
        units = f"Select_CString({side}.HasCategory({category}.Self), {side}.GetSubUnitsForCategoryTooltip({category}.Self), '')"
        cats[cat_key(s, category, SUMS_LIVE)] = kept(cat_key(s, category, SUMS_LIVE), units)
        cats[cat_key(s, category, SUMS_LIVE, "catend")] = units
    experience = f"Multiply_CFixedPoint({side}.GetCountry.GetAverageArmyExperience, '(CFixedPoint)100')"
    return cats | terrain_notes(s, side, s == "a") | {key(k, SUMS_LIVE): v for k, v in {
        f"{s}_dice": f"{side}.GetDiceWithModifiersTooltip",
        f"{s}_disc": pct(modifier(side, "discipline")),
        f"{s}_discs": sources(side, "discipline"),
        f"{s}_tac": dec2(modifier(side, "military_tactics")),
        f"{s}_tacs": sources(side, "military_tactics"),
        f"{s}_ca": pct(f"{side}.GetCombinedArmsBonus"),
        f"{s}_cas": f"{side}.GetCombinedArmsInfo",
        # the country's average army experience: the game gives none for an army as a number the GUI can keep
        f"{s}_exp": f"Concatenate({dec2(experience)}, '%')",
        f"{s}_exps": f"{side}.GetCountry.GetAverageArmyExperienceInfo",
        f"{s}_levy": pct(f"{side}.GetCountry.GetModifier('levy_combat_efficiency_modifier')"),
        f"{s}_levys": f"{side}.GetCountry.GetDescriptionFor('levy_combat_efficiency_modifier')",
        f"{s}_front": dec2(f"{side}.GetPossibleFrontage"),
        f"{s}_fronts": f"{side}.GetPossibleFrontageInfo",
    }.items()}


# The dice modifiers of a side (CombatModifier keys; 'dice' is the roll itself)
DICE_MODS = ("commander", "topography", "vegetation", "climate", "river_crossing", "strait_crossing", "sea_landing")


def parse_int(x, low=-6, high=6):
    """A small whole number written as text back to a number (the GUI has no such function): 0 if out of range."""
    expr = "'(int32)0'"
    for v in range(low, high + 1):
        if v:
            expr = f"Select_int32(EqualTo_string({x}, '{v}'), '(int32){v}', {expr})"
    return expr


def sum_key(s, which, battle):
    """A side's dice modifiers of the battle's last day noted: 'pos' the sum of the bonuses, 'neg' of the penalties,
    'day' the day they are of."""
    return f"Concatenate3('bd_{s}_m_', '{which}', {battle})"


def dice_recorder(s, name):
    """Each dice modifier of a side, noted once a day (a note per modifier and battle holds the day it was noted on, so
    two of our armies in the battle can't count it twice) and added to the day's sums. The sums start afresh on a new
    day. Keys per battle, not per day: the GUI's variables are many enough already."""
    # checked every frame: by the battle's key as noted (the scratch one is set only within a chain of notes, and
    # another battle's chain would show these anew)
    stable = f"GetVariableSystem.Get(Concatenate('bd_token_', {BATTLE_SLOT}))"
    noted = f"Concatenate3('bd_{s}_mg_', CombatModifier.GetKey, {stable})"
    is_dice = [f"EqualTo_string(CombatModifier.GetKey, '{m}')" for m in DICE_MODS]
    while len(is_dice) > 1:
        is_dice = [f"Or({is_dice[i]}, {is_dice[i + 1]})" if i + 1 < len(is_dice) else is_dice[i] for i in range(0, len(is_dice), 2)]
    value = f"Select_int32({is_dice[0]}, CombatModifier.GetValue, '(int32)0')"
    fresh = f"EqualTo_string(GetVariableSystem.Get({sum_key(s, 'day', SUMS_LIVE)}), GetDateString)"
    steps = battle_steps() + [f"GetVariableSystem.Set('bd_tmp_mv', ToString_int32({value}))"]
    for which, bound in (("pos", "Max_int32"), ("neg", "Min_int32")):
        k = sum_key(s, which, SUMS_LIVE)
        steps.append(f"GetVariableSystem.Set({k}, ToString_int32(Add_int32(Select_int32({fresh}, {parse_int(f'GetVariableSystem.Get({k})')}, '(int32)0'), "
                     f"{bound}({parse_int(tmp('mv'))}, '(int32)0'))))")
    steps += [f"GetVariableSystem.Set({sum_key(s, 'day', SUMS_LIVE)}, GetDateString)", f"GetVariableSystem.Set({noted}, GetDateString)"]
    starts = "".join(f'\t\ton_start = "[{st}]"\n' for st in steps)
    return (f'vbox = {{\n\tdatamodel = "[Combat.Get{name}.GetCombatModifiers]"\n\titem = {{\n'
            f'\t\twidget = {{\n\t\t\tsize = {{ 0 0 }}\n\t\t\tvisible = "[Not(EqualTo_string(GetVariableSystem.Get({noted}), GetDateString))]"\n'
            '\t\t\tvisible_at_creation = no\n\t\t\tstate = {\n\t\t\t\tname = _show\n' + indent(starts, 2)
            + '\t\t\t}\n\t\t}\n\t}\n}\n')


# terrain keys of the units' combat modifiers -> when the battle is fought there ('coastal' and 'inland' are left out)
TOPOGRAPHY = ("mountains", "wetlands", "hills", "plateau", "inland_sea", "narrows", "ocean", "deep_ocean")
VEGETATION = ("desert", "forest", "grasslands", "jungle", "sparse", "woods")
CLIMATE = ("arid",)


def terrain_check(t, attacker):
    loc = "Combat.GetLocation"
    if t in TOPOGRAPHY:
        return f"EqualTo_string({loc}.GetTopography.GetNameWithNoTooltip, Localize('{t}'))"
    if t in VEGETATION:
        return f"EqualTo_string({loc}.GetVegetation.GetNameWithNoTooltip, Localize('{t}'))"
    if t in CLIMATE:
        return f"EqualTo_string({loc}.GetClimate.GetNameWithNoTooltip, Localize('{t}'))"
    if t == "river":   # only who crosses it
        return "Combat.IsRiverCrossing" if attacker else None
    return None


def game_blocks(folder):
    """key -> body of the top-level blocks of the game's files in a folder (comments taken out)."""
    out = {}
    path = os.path.join(GAME, "in_game", "common", folder)
    for name in sorted(os.listdir(path)):
        if not name.endswith(".txt"):
            continue
        with open(os.path.join(path, name), encoding="utf-8-sig") as fh:
            text = re.sub(r"#.*", "", fh.read())
        for m in re.finditer(r"^([A-Za-z0-9_]+)\s*=\s*\{", text, re.M):
            depth, j = 1, m.end()
            while depth and j < len(text):
                depth += {"{": 1, "}": -1}.get(text[j], 0)
                j += 1
            out[m.group(1)] = text[m.end():j - 1]
    return out


def english_names():
    names = {}
    folder = os.path.join(GAME, "main_menu", "localization", "english")
    for root, _, files in os.walk(folder):
        for name in files:
            if name.endswith(".yml"):
                with open(os.path.join(root, name), encoding="utf-8-sig") as fh:
                    names |= dict(re.findall(r'^\s*([A-Za-z0-9_]+):\d*\s*"(.*)"', fh.read(), re.M))
    return names


def unit_terrain():
    """category -> [(unit type, terrain, value)]: each unit type's combat modifiers by terrain, as the game sums them
    along copy_from and with its category's. Types of one name and the same modifiers are listed once."""
    types = game_blocks("unit_types")
    cats = game_blocks("unit_categories")

    def field(body, name):
        m = re.search(rf"^\s*{name}\s*=\s*([A-Za-z0-9_]+)", body, re.M)
        return m.group(1) if m else None

    def combat(body):
        m = re.search(r"\bcombat\s*=\s*\{([^}]*)\}", body)
        return {k: float(v) for k, v in re.findall(r"([a-z_]+)\s*=\s*(-?[0-9.]+)", m.group(1))} if m else {}

    def resolved(key, seen=()):
        body = types[key]
        parent = field(body, "copy_from")
        base, cat = resolved(parent, seen + (key,)) if parent in types and parent not in seen else ({}, None)
        mods = dict(base)
        for k, v in combat(body).items():
            mods[k] = mods.get(k, 0) + v
        return mods, field(body, "category") or cat

    names = english_names()
    out, listed = {}, set()
    for key, body in types.items():
        if field(body, "empty") == "yes":
            continue
        mods, cat = resolved(key)
        if cat not in cats:
            continue
        for k, v in combat(cats[cat]).items():
            mods[k] = mods.get(k, 0) + v
        name = names.get(key, key)
        if (cat, name) not in listed:
            listed.add((cat, name))
            out.setdefault(cat, {})[key] = {t: round(v, 2) for t, v in mods.items() if round(v, 2)}
    return out


def power_types():
    """category -> [(unit type, levy, combat power, {terrain: modifier})] for every land unit type, its combat power and
    terrain modifiers as the game sums them along copy_from (and with its category's); one entry for a name (a levy is
    a regiment of the same type), the shorter names first (a row naming "Camel Pistoleers" holds "Pistoleers" too: the longer
    one, checked later, wins)."""
    types = game_blocks("unit_types")
    cats = game_blocks("unit_categories")
    names = english_names()

    def field(body, name):
        m = re.search(rf"^\s*{name}\s*=\s*([A-Za-z0-9_.]+)", body, re.M)
        return m.group(1) if m else None

    def combat(body):
        m = re.search(r"\bcombat\s*=\s*\{([^}]*)\}", body)
        return {k: float(v) for k, v in re.findall(r"([a-z_]+)\s*=\s*(-?[0-9.]+)", m.group(1))} if m else {}

    def resolved(key, seen=()):
        body = types[key]
        parent = field(body, "copy_from")
        if parent in types and parent not in seen:
            power, levy, mods, cat = resolved(parent, seen + (key,))
        else:
            power, levy, mods, cat = None, False, {}, None
        mods = dict(mods)
        for k, v in combat(body).items():
            mods[k] = mods.get(k, 0) + v
        own = field(body, "combat_power")
        return (float(own) if own else power, levy or field(body, "levy") == "yes", mods, field(body, "category") or cat)

    def shown_name(key):
        name = names.get(key, key)
        while name.startswith("$") and name.endswith("$") and name[1:-1] in names:
            name = names[name[1:-1]]
        return name

    out, listed = {}, set()
    for key, body in types.items():
        if field(body, "empty") == "yes" or not key.startswith("a_"):
            continue
        power, levy, mods, cat = resolved(key)
        if cat not in cats or not power:
            continue
        for k, v in combat(cats[cat]).items():
            mods[k] = mods.get(k, 0) + v
        mark = (cat, shown_name(key))
        if mark not in listed:
            listed.add(mark)
            out.setdefault(cat, []).append((key, levy, power, {t: v for t, v in mods.items() if round(v, 2)}, len(mark[1])))
    return {cat: [e[:4] for e in sorted(entries, key=lambda e: e[4])] for cat, entries in out.items()}


POWER_TYPES = power_types()
TERRAINS = sorted({t for entries in POWER_TYPES.values() for _, _, _, mods in entries for t in mods})


def flat_number(name, digits):
    """The number of the digits read into bd_tmp_<name>0.. (see read_digits), summed as a balanced tree: a flat one
    nests too deep for the statements it goes into."""
    def tree(parts, op):
        while len(parts) > 1:
            parts = [f"{op}({parts[i]}, {parts[i + 1]})" if i + 1 < len(parts) else parts[i] for i in range(0, len(parts), 2)]
        return parts[0]
    terms = []
    for k in range(digits):
        d = tmp(f"{name}{k}")
        value = tree([f"Select_int32(EqualTo_string({d}, '{v}'), '(int32){v}', '(int32)0')" for v in range(1, 10)], "Add_int32")
        terms.append(f"Multiply_int32({value}, '(int32){10 ** k}')")
    return tree(terms, "Add_int32")


def read_number(text, tail, name, digits, commas=False):
    """read_digits for `digits` digits, and with commas between thousands (a strength as the game writes it: 33,550)."""
    steps = [f"GetVariableSystem.Set('bd_tmp_s', {text})", f"GetVariableSystem.Set('bd_tmp_suf', {tail})"]
    for k in range(digits):
        if commas and k and k % 3 == 0:
            steps.append(f"GetVariableSystem.Set('bd_tmp_suf', Select_CString(StringContains({tmp('s')}, Concatenate(',', {tmp('suf')})), "
                         f"Concatenate(',', {tmp('suf')}), {tmp('suf')}))")
        digit = "''"
        for d in range(9, -1, -1):
            digit = f"Select_CString(StringContains({tmp('s')}, Concatenate('{d}', {tmp('suf')})), '{d}', {digit})"
        steps += [f"GetVariableSystem.Set('bd_tmp_{name}{k}', {digit})",
                  f"GetVariableSystem.Set('bd_tmp_suf', Concatenate({tmp(f'{name}{k}')}, {tmp('suf')}))"]
    return steps


# A combat power (per thousand men) of the regiments in the line as men killed a day: at an average roll (5.5, a dice
# impact of 10 + 2 x 4.5 = 19, as the wiki gives it) against an enemy of no discipline. Matched on five battles of 42
# regiments of pistoleers (1561-62), the share in the line as noted: the enemy's real losses over what 76 gave (its
# dice impact day by day / 19, its discipline and experience) were 0.27 (Wadi an-Natrun), 0.40 (Damanhur), 0.73
# (Tidah, Feb), 0.35 (Tidah, Apr), 0.44 (Minuf), 0.42 on average: 76 x 0.42 = 32. A rough guide: one battle may be
# off by half either way (the enemy's tactics, flanking, who stood where).
KILLS_PER_POWER = 32


def parse_share():
    """The side's share of regiments in the line read by power_steps (thousandths)."""
    return flat_number("h", 4)


def power_steps(s, name, c):
    """In the result popup, for a row of a unit category's units as noted (StringViewPair, 'N [type] men (pct)'): its
    combat power, added once to the category's and the side's (the keys of the popup's battle, tmp 'pu'):
    men / 1000 x the type's combat power x its terrain modifier here x (1 + the country's power of the category)
    x (1 + discipline, 10 points less for levies). The steps read the men digit by digit (the GUI can't turn text into
    numbers) and the type by its name, the longer names last."""
    row, levy = tmp("row"), f"Not(StringIsEmpty({tmp('lv')}))"
    country = f"BattleResultMessage.GetBattleResult.Get{name}.GetMainParticipant"
    steps = [f"GetVariableSystem.Set('bd_tmp_pu', {popup_match()})",
             "GetVariableSystem.Set('bd_tmp_row', StringViewPair.GetLeft.GetString)",
             f"GetVariableSystem.Set('bd_tmp_lv', Select_CString(StringContains({row}, Localize('BD_LEVY_TAG')), '1', ''))",
             "GetVariableSystem.Set('bd_tmp_cpi', '')", "GetVariableSystem.Set('bd_tmp_tfi', '')"]
    # the side's share of regiments in the line over the battle, thousandths: the average frontage taken (x100 a day)
    # over its regiments; all of them where it wasn't noted (a battle noted before)
    for note, digits_name, digits in (("eng", "e", 7), ("engd", "x", 4), ("regs", "r", 5)):
        old = f"GetVariableSystem.Get({side_total_key(repr(s), tmp('pu'), note)})"
        steps += read_number(f"Concatenate(Select_CString(StringIsEmpty({old}), '0', {old}), '~')", "'~'", digits_name, digits)
    eng, days, regs = flat_number("e", 7), flat_number("x", 4), flat_number("r", 5)
    steps.append(f"GetVariableSystem.Set('bd_tmp_sh', ToString_int32(Select_int32(Or(EqualTo_int32({days}, '(int32)0'), "
                 f"EqualTo_int32({regs}, '(int32)0')), '(int32)1000', Min_int32('(int32)1000', "
                 f"Divide_int32(Multiply_int32({eng}, '(int32)10'), Multiply_int32({days}, {regs}))))))")
    steps += read_number(f"Concatenate({tmp('sh')}, '~')", "'~'", "h", 4)
    # the men stand before the strength icon, with or without the end of the number's format code
    tail = "Select_CString(StringContains(GetVariableSystem.Get('bd_tmp_row'), Localize('BD_TAIL')), Localize('BD_TAIL'), Localize('BD_TAIL2'))"
    steps += read_number(row, tail, "n", 7, commas=True)
    for unit, is_levy, power, mods in POWER_TYPES.get(c, []):
        # by its name alone: a levy is a regiment of the same unit type, marked as a levy in the row
        match = f"StringContains({row}, Localize('{unit}'))"
        terrain = [f"Select_int32(EqualTo_string({get(f'tr_{s}_{t}', tmp('pu'))}, '1'), '(int32){round(v * 100)}', '(int32)0')"
                   for t, v in mods.items() if t in TERRAINS]
        pct = "'(int32)100'"
        for term in terrain:
            pct = f"Add_int32({pct}, {term})"
        steps += [f"GetVariableSystem.Set('bd_tmp_cpi', Select_CString({match}, '{round(power * 100)}', {tmp('cpi')}))",
                  f"GetVariableSystem.Set('bd_tmp_tfi', Select_CString({match}, ToString_int32({pct}), {tmp('tfi')}))"]
    steps += read_number(f"Concatenate(Select_CString(StringIsEmpty({tmp('cpi')}), '0', {tmp('cpi')}), '~')", "'~'", "c", 4)
    steps += read_number(f"Concatenate(Select_CString(StringIsEmpty({tmp('tfi')}), '0', {tmp('tfi')}), '~')", "'~'", "f", 3)
    pct = lambda m: f"FixedPointToInt(Multiply_CFixedPoint({country}.GetModifierRawValue('{m}'), '(CFixedPoint)100'))"
    discipline = f"Subtract_int32({pct('discipline')}, Select_int32({levy}, '(int32)10', '(int32)0'))"
    steps.append(f"GetVariableSystem.Set('bd_tmp_m', ToString_int32(Divide_int32(Multiply_int32(Add_int32('(int32)100', {pct(f'{c}_power')}), "
                 f"Add_int32('(int32)100', {discipline})), '(int32)100')))")
    steps += read_number(f"Concatenate({tmp('m')}, '~')", "'~'", "k", 3)
    value = (f"Divide_int32(Multiply_int32(Divide_int32(Multiply_int32(Divide_int32(Multiply_int32({flat_number('n', 7)}, {flat_number('c', 4)}), "
             f"'(int32)100'), {flat_number('f', 3)}), '(int32)100'), {flat_number('k', 3)}), '(int32)100')")
    steps.append(f"GetVariableSystem.Set('bd_tmp_v', ToString_int32({value}))")
    steps += read_number(f"Concatenate({tmp('v')}, '~')", "'~'", "v", 8)
    # once a row (the popup may be opened again)
    done = f"Concatenate3('bd_pwr_', Concatenate3({tmp('pu')}, '{s}{c}', {row}), '')"
    for k, total in ((cat_key(s, f"GetSubUnitCategory('{c}')", tmp("pu"), "pw"), "p"), (key(f"{s}_pw", tmp("pu")), "q")):
        old = f"GetVariableSystem.Get({k})"
        steps += read_number(f"Concatenate(Select_CString(StringIsEmpty({old}), '0', {old}), '~')", "'~'", total, 8)
        steps.append(f"GetVariableSystem.Set({k}, Select_CString(GetVariableSystem.Exists({done}), {old}, "
                     f"ToString_int32(Add_int32({flat_number(total, 8)}, {flat_number('v', 8)}))))")
        # and as shown: men killed a day, by the side's share of regiments in the line (tmp 'sh', thousandths)
        steps += read_number(f"Concatenate({old}, '~')", "'~'", total, 8)
        n = flat_number(total, 8)
        steps.append(f"GetVariableSystem.Set(Concatenate({k}, '_f'), ToString_int32(Divide_int32(Multiply_int32(Divide_int32("
                     f"Multiply_int32({n}, {parse_share()}), '(int32)1000'), '(int32){KILLS_PER_POWER}'), '(int32)1000')))")
    steps.append(f"GetVariableSystem.Set({done}, '1')")
    return steps


def power_recorder():
    """In the result popup: each row of each unit category's units as noted, as it is made (trigger_on_create: the rows
    come as the popup's battle is found), worked out by power_steps."""
    out = ""
    for s, name in SIDES:
        for c in POWER_TYPES:
            units = f"GetVariableSystem.Get({cat_key(s, f'GetSubUnitCategory({chr(39)}{c}{chr(39)})', popup_match())})"
            starts = "".join(f'\t\t\t\ton_start = "[{st}]"\n' for st in power_steps(s, name, c))
            out += (f'vbox = {{\n\tdatacontext = "[StringToStringPairList({units})]"\n\tdatamodel = "[StringPairList.GetRows]"\n'
                    '\titem = {\n\t\twidget = {\n\t\t\tsize = { 0 0 }\n\t\t\tstate = {\n\t\t\t\tname = bd_power\n\t\t\t\ttrigger_on_create = yes\n'
                    + starts + '\t\t\t}\n\t\t}\n\t}\n}\n')
    return out


def terrain_lines(cat, units):
    """A category's terrain modifiers as lines (unit type or None for the category, terrain, value): what most of its
    types have goes for the category, and a type with another value gets a line of its own. Written per type, they
    were too many for the GUI file."""
    lines = []
    for t in sorted({t for mods in units.values() for t in mods}):
        common = collections.Counter(mods.get(t, 0) for mods in units.values()).most_common(1)[0][0]
        if common:
            lines.append((None, t, common))
        lines += [(unit, t, mods.get(t, 0)) for unit, mods in units.items() if mods.get(t, 0) != common]
    return lines


def join(parts):
    """Concatenate any number of strings (the GUI joins 2 or 3 at a time)."""
    parts = list(parts) or ["''"]
    while len(parts) > 1:
        parts = [f"Concatenate3({', '.join(parts[i:i + 3])})" if len(parts[i:i + 3]) == 3 else
                 (f"Concatenate({', '.join(parts[i:i + 3])})" if len(parts[i:i + 3]) == 2 else parts[i])
                 for i in range(0, len(parts), 3)]
    return parts[0]


def terrain_notes(s, side, attacker):
    """For each unit category of a side: a line per unit type of it in the battle that fights better or worse on this
    battlefield, the bonuses ('+') in one note and the penalties ('−', U+2212) in another, for the green arrow's
    tooltip and the red one's."""
    notes = {}
    names = english_names()
    for cat, types in unit_terrain().items():
        units = f"{side}.GetSubUnitsForCategoryTooltip(GetSubUnitCategory('{cat}').Self)"
        lines = {"p": [], "n": []}
        # types of one name (a regiment and its levy) are found by that name alike: one line for them
        written = set()
        for unit, t, v in terrain_lines(cat, types):
            where = terrain_check(t, attacker)
            # a levy's name is often a reference to its regiment's ('$a_light_camelry_1$')
            name = names.get(unit, unit)
            while name and name.startswith("$") and name.endswith("$") and name[1:-1] in names:
                name = names[name[1:-1]]
            mark = (name, t, v)
            if not where or mark in written:
                continue
            written.add(mark)
            place = "Localize('BD_RIVER_TERRAIN')" if t == "river" else f"Localize('{t}')"
            value = f"'{'+' if v > 0 else '−'}{round(abs(v) * 100)}%'" if v else "'0%'"
            who = f"Localize('{unit}')" if unit else f"Concatenate(Localize('{cat}'), Localize('BD_MOST'))"
            line = join([who, "': '", place, "' '", value, "Localize('BD_SEP')"])
            present = f"StringContains({units}, Localize('{unit}'))" if unit else f"{side}.HasCategory(GetSubUnitCategory('{cat}').Self)"
            # a type at 0% (against its category's most types) goes with both
            for sign in ("p",) * (v >= 0) + ("n",) * (v <= 0):
                lines[sign].append(f"Select_CString(And({where}, {present}), {line}, '')")
        for sign, found in lines.items():
            if found:
                k = f"Concatenate3('bd_{s}_ter{sign}_', GetSubUnitCategory('{cat}').GetNameWithNoTooltip, {SUMS_LIVE})"
                notes[k] = kept(k, join(found))
    return notes


# The chain of a battle is kept by days: a day with anything to show gets a numbered entry (bd_days_<battle> counts
# them) with its date and fields: 'roll' the dice of a new roll, 'fa' / 'fd' the attacker's / defender's flanks the
# day one of them fell, 'ja' / 'jd' the armies that joined the attacker / defender.
DAYS = 40


def day_key(index, battle, what):
    return f"Concatenate3('bd_day{what}_', {index}, {battle})"


def day_event(when, field, value, battle, add_to=False):
    """on_start calls that note `value` in `field` of today's entry of a battle's chain when `when` holds, starting the
    entry if today has none yet. With add_to, a value already there is kept and the new one put on a line below."""
    count = f"Concatenate('bd_days_', {battle})"
    days = f"GetVariableSystem.Get({count})"
    last = f"Concatenate('bd_lastday_', {battle})"
    add = f"Not(StringIsEmpty({tmp('add')}))"
    new = f"Not(StringIsEmpty({tmp('new')}))"
    index = tmp("idx")
    old = f"GetVariableSystem.Get({day_key(index, battle, field)})"
    value = (f"Concatenate3({old}, Select_CString(StringIsEmpty({old}), '', Localize('BD_SEP')), {value})" if add_to else value)
    return ([f"GetVariableSystem.Set('bd_tmp_add', Select_CString({when}, '1', ''))",
             f"GetVariableSystem.Set('bd_tmp_new', Select_CString(And({add}, Not(EqualTo_string(GetVariableSystem.Get({last}), GetDateString))), '1', ''))"]
            + read_digits(f"Select_CString(StringIsEmpty({days}), '0{SUM_TAIL}', {days})", repr(SUM_TAIL), "n")
            + [f"GetVariableSystem.Set('bd_tmp_idx', ToString_int32(Add_int32({number('n')}, Select_int32({new}, '(int32)1', '(int32)0'))))",
               f"GetVariableSystem.Set({day_key(index, battle, 'date')}, Select_CString({new}, {short_date()}, "
               f"GetVariableSystem.Get({day_key(index, battle, 'date')})))",
               f"GetVariableSystem.Set({day_key(index, battle, field)}, Select_CString({add}, {value}, {old}))",
               f"GetVariableSystem.Set({last}, Select_CString({add}, GetDateString, GetVariableSystem.Get({last})))",
               f"GetVariableSystem.Set({count}, Concatenate({index}, '{SUM_TAIL}'))"])


# armies that join a side on one day with a line (and a tooltip) of their own; any more that day are not shown
ARRIVALS = 3


def arrivals():
    """Armies that join a battle after its first day, ours, allied or enemy: each army of a side (CombatSide.GetUnits)
    is noted once per battle, and one that appears after the day the battle began goes into that day of the chain: its
    men and country, on its side."""
    battle = SUMS_LIVE
    start = f"GetVariableSystem.Get(Concatenate('bd_start_', {battle}))"
    later = f"And(Not(StringIsEmpty({start})), Not(EqualTo_string({start}, GetDateString)))"
    army = join(["Localize('BD_CAME')", "Unit.GetVisualStrengthShort", "' ('", "Unit.GetCountry.GetNameWithNoTooltip", "')'",
                 "Localize('BD_CAME_END')"])
    lines = ""
    for s, name in SIDES:
        # checked every frame: by the battle's key as noted (the scratch one is set only within a chain of notes)
        seen = f"Concatenate3('bd_army_', ToString_int32(Unit.GetID), GetVariableSystem.Get(Concatenate('bd_token_', {BATTLE_SLOT})))"
        steps = battle_steps() + [f"GetVariableSystem.Set({seen}, '1')"] + day_event(later, f"j{s}", army, battle, add_to=True)
        # its regiments, added to its side's (for the share of them in the line: frontage_steps)
        steps += add_to_note(side_total_key(repr(s), battle, "regs"), "Unit.GetNumSubUnits", "g", 5)
        # and each army in a slot of its own that day (up to ARRIVALS a side), with its regiments for its tooltip
        index, add = tmp("idx"), "Not(StringIsEmpty(GetVariableSystem.Get('bd_tmp_add')))"
        free = lambda k: f"StringIsEmpty(GetVariableSystem.Get({day_key(index, battle, f'j{s}{k}t')}))"
        pick = "''"
        for k in range(ARRIVALS, 0, -1):
            pick = f"Select_CString({free(k)}, '{k}', {pick})"
        steps.append(f"GetVariableSystem.Set('bd_tmp_k', {pick})")
        # a list only if the army has such regiments (an empty one still shows its column heads)
        regs = "Select_CString(GreaterThan_float(Unit.GetTotalRegularCount, '(float)0'), Unit.GetRegularsTooltipText, '')"
        levies = "Select_CString(GreaterThan_float(Unit.GetTotalLevyCount, '(float)0'), Unit.GetLeviesTooltipText, '')"
        for f, value in (("t", army), ("r", regs), ("l", levies)):
            k = f"Concatenate3(Concatenate3('bd_dayj{s}', {tmp('k')}, '{f}_'), {index}, {battle})"
            steps.append(f"GetVariableSystem.Set({k}, Select_CString({add}, {value}, GetVariableSystem.Get({k})))")
        starts = "".join(f'\t\t\t\ton_start = "[{st}]"\n' for st in steps)
        lines += (f'vbox = {{\n\tdatamodel = "[Combat.Get{name}.GetUnits]"\n\titem = {{\n\t\twidget = {{\n\t\t\tsize = {{ 0 0 }}\n'
                  f'\t\t\tvisible = "[Not(GetVariableSystem.Exists({seen}))]"\n\t\t\tvisible_at_creation = no\n'
                  '\t\t\tstate = {\n\t\t\t\tname = _show\n' + starts + '\t\t\t}\n\t\t}\n\t}\n}\n')
    return lines


FLANKS = ("Left", "Center", "Right")
# the battle shown in the result popup, noted when its details are opened (see result_panel): read in each entry of
# the chain, the whole key made the file too big
SHOWN = "GetVariableSystem.Get('bd_shown')"


def add_to_note(k, value, name, digits):
    """on_start calls that add a whole number (an int32 expression) to a note kept as text."""
    old = f"GetVariableSystem.Get({k})"
    return (read_number(f"Concatenate(Select_CString(StringIsEmpty({old}), '0', {old}), '~')", "'~'", name, digits)
            + [f"GetVariableSystem.Set({k}, ToString_int32(Add_int32({flat_number(name, digits)}, {value})))"])


def frontage_steps():
    """Each day, for each side: the frontage its regiments in the line take (x100), added up, and the days counted: the
    battle's average share of a side's regiments in the line is the one over the other, over its regiments
    (arrivals). The combat power is scaled by it (power_steps)."""
    steps = []
    for s, name in SIDES:
        side = f"Combat.Get{name}"
        engaged = f"Add_CFixedPoint(Add_CFixedPoint({side}.GetLeft.GetEngagedFrontage, {side}.GetCenter.GetEngagedFrontage), {side}.GetRight.GetEngagedFrontage)"
        # the days of the main phase only: in the bombard phase the line doesn't fight
        steps += add_to_note(side_total_key(repr(s), SUMS_LIVE, "eng"), f"Select_int32(Combat.IsInBombardPhase, '(int32)0', "
                             f"FixedPointToInt(Multiply_CFixedPoint({engaged}, '(CFixedPoint)100')))", "g", 7)
        steps += add_to_note(side_total_key(repr(s), SUMS_LIVE, "engd"), "Select_int32(Combat.IsInBombardPhase, '(int32)0', '(int32)1')", "g", 4)
    return steps


def flank_rows():
    """Flanks that fell or filled again: when a flank of a side that had regiments the day before has none today, or
    the other way round, that day of the chain shows the side's three flanks as squares, as the game's map marker of a
    battle does (unit_marker_battle_side_flank): green with regiments fighting, yellow with regiments not engaged, red
    with none (GetSize counts the fled ones too).
    Whether each flank held men is noted every day."""
    steps = []
    bombard = "Combat.IsInBombardPhase"
    for s, name in SIDES:
        line = {f: f"Combat.Get{name}.Get{f}" for f in FLANKS}
        empty = {f: (f"Or(And3(Not({bombard}), IsDataModelEmpty({line[f]}.GetEngaged), IsDataModelEmpty({line[f]}.GetNonEngaged)), "
                     f"And({bombard}, IsDataModelEmpty({line[f]}.GetCanBombard)))") for f in FLANKS}
        fighting = {f: (f"Or(And(Not({bombard}), GreaterThan_CFixedPoint({line[f]}.GetEngagedFrontage, '(CFixedPoint)0')), "
                        f"And({bombard}, Not(IsDataModelEmpty({line[f]}.GetCanBombard))))") for f in FLANKS}
        has_men = {f: f"Not({empty[f]})" for f in FLANKS}
        held = {f: side_total_key(repr(s), SUMS_LIVE, f"fl{f}") for f in FLANKS}
        state = join([f"Select_CString({empty[f]}, '{f[0]}0', Select_CString({fighting[f]}, '{f[0]}1', '{f[0]}2'))" for f in FLANKS])
        # a flank that fell or filled again (reserves sent to it): each in a statement of its own, as one statement for
        # all of them broke the day's notes in the game
        for f in FLANKS:
            was = f"GetVariableSystem.Get({held[f]})"
            steps.append(f"GetVariableSystem.Set('bd_tmp_ch{f[0]}', Select_CString(And(Not(StringIsEmpty({was})), "
                         f"Not(EqualTo_string({was}, Select_CString({has_men[f]}, '1', '0')))), '1', ''))")
        steps += day_event(f"Not(StringIsEmpty(Concatenate3({tmp('chL')}, {tmp('chC')}, {tmp('chR')})))", f"f{s}", state, SUMS_LIVE)
        steps += [f"GetVariableSystem.Set({held[f]}, Select_CString({has_men[f]}, '1', '0'))" for f in FLANKS]
    return steps


def flank_squares(state):
    """Three squares, left, centre and right: green for a flank fighting, yellow for one with regiments not engaged, red
    for one without (`state` as 'L1C0R2')."""
    out = ""
    for f in FLANKS:
        # a near-white tile tinted: the game's coloured tiles came out dark on this background
        for held, colour in (("1", "{ 0.3 0.85 0.3 1 }"), ("2", "{ 0.95 0.8 0.25 1 }"), ("0", "{ 0.95 0.25 0.2 1 }")):
            out += (f'icon = {{\n\tsize = {{ 10 10 }}\n\ttexture = "gfx/interface/colors/whiteish.dds"\n\tcolor = {colour}\n'
                    f'\tvisible = "[StringContains({state}, \'{f[0]}{held}\')]"\n}}\n')
    return f'hbox = {{\n\tspacing = 2\n\tvisible = "[Not(StringIsEmpty({state}))]"\n' + indent(out, 1) + '}\n'


DATE_WIDTH = 46
SQUARES_WIDTH = 36
COLON_WIDTH = 12


# the height of the first line of a day in the chain
LINE = 18


def split_roll(a, d, bombard):
    """A roll as the attacker's number right-aligned up to the colon and the defender's left-aligned after it; one of
    the bombard phase with the artillery's icon at the end of the line, which tells so in its tooltip."""
    side = (ROLL_WIDTH - COLON_WIDTH) // 2
    part = lambda width, align, text: (f'text_single = {{\n\tminimumsize = {{ {width} {LINE} }}\n\tmaximumsize = {{ {width} {LINE} }}\n'
                                       f'\tfontsize = 14\n\talign = {align}|nobaseline\n\traw_text = "{text}"\n}}\n')
    body = part(side, "right", f"[{a}]") + part(COLON_WIDTH, "center", ":") + part(ROLL_WIDTH - COLON_WIDTH - side, "left", f"[{d}]")
    icon = (f'icon = {{\n\tsize = {{ 18 18 }}\n\tparentanchor = right|vcenter\n\tvisible = "[Not(StringIsEmpty({bombard}))]"\n'
            "\ttexture = \"[GetSubUnitCategoryIcon(GetSubUnitCategory('army_artillery').Self)]\"\n"
            '\talwaystransparent = no\n\ttooltip = "BD_BOMBARD_TT"\n}\n')
    return (f'widget = {{\n\tsize = {{ {ROLL_WIDTH} {LINE} }}\n\tvisible = "[Not(StringIsEmpty({a}))]"\n'
            + indent('hbox = {\n' + indent(body, 1) + '}\n' + icon, 1) + '}\n')


def log_block():
    """The chain of the battle, as a column between the two sides' cards (below the line of their names), a day a line:
    the date small on the left; then the attacker's flanks (the day one fell), the roll in the middle, the defender's
    flanks; and below, the armies that joined, each side's on its side."""
    days = ""
    for i in range(1, DAYS + 1):
        g = lambda what: f"GetVariableSystem.Get({day_key(repr(str(i)), SHOWN, what)})"
        # fixed widths, so the roll stands in the same place on every line, flanks or not
        # and one height for the first line of a day, whatever it holds, with the date in its middle
        slot = lambda state, anchor: (f'widget = {{\n\tsize = {{ {SQUARES_WIDTH} {LINE} }}\n'
                                      + indent(flank_squares(state).replace("hbox = {\n", f"hbox = {{\n\tparentanchor = {anchor}|vcenter\n", 1), 1) + '}\n')
        first = (f'hbox = {{\n\tvisible = "[Not(StringIsEmpty(Concatenate3({g("roll")}, {g("fa")}, {g("fd")})))]"\n'
                 + indent(slot(g("fa"), "left"), 1)
                 + f'\ttext_single = {{\n\t\tminimumsize = {{ {ROLL_WIDTH} {LINE} }}\n\t\tmaximumsize = {{ {ROLL_WIDTH} {LINE} }}\n\t\tfontsize = 14\n'
                 f'\t\talign = center|nobaseline\n\t\tvisible = "[StringIsEmpty({g("ra")})]"\n\t\ttext = "[{g("roll")}]"\n\t}}\n'
                 + indent(split_roll(g("ra"), g("rd"), g("rb")), 1)
                 + indent(slot(g("fd"), "right"), 1)
                 # the room on the right that matches the dates, so the line spans the column (a narrower one is centred)
                 + f'\twidget = {{\n\t\tsize = {{ {DATE_WIDTH} {LINE} }}\n\t}}\n}}\n')
        # the armies that joined, a line each, their regiments as they came in its tooltip
        joined = ""
        for s, align in (("a", "left"), ("d", "right")):
            for k in range(1, ARRIVALS + 1):
                line, regs, levies = (g(f"j{s}{k}{f}") for f in "trl")
                lists = "".join(f'TooltipColumnList = {{\n\tvisible = "[Not(StringIsEmpty({lst}))]"\n'
                                f'\tblockoverride "block_title" {{\n\t\ttext = "{title}"\n\t}}\n\ttextcontext = "[{lst}]"\n}}\n'
                                # the game's own block titles need the army, which is gone by now
                                for lst, title in ((regs, "[regulars|E]"), (levies, "[levies|E]")))
                joined += (f'text_single = {{\n\tminimumsize = {{ {LOG_WIDTH - DATE_WIDTH} -1 }}\n\tmaximumsize = {{ {LOG_WIDTH - DATE_WIDTH} -1 }}\n'
                           f'\talign = {align}|nobaseline\n\tfontsize = 13\n\tvisible = "[Not(StringIsEmpty({line}))]"\n'
                           f'\ttext = "[{line}]"\n\talwaystransparent = no\n'
                           + indent(tip(f"[{line}]", "[GetConceptTexture('combat')]", "[army|e]", lists), 1) + '}\n')
        days += (f'hbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tvisible = "[Not(StringIsEmpty({g("date")}))]"\n'
                 # the date at the top of its day, by its first line
                 f'\tvbox = {{\n\t\tlayoutpolicy_vertical = expanding\n'
                 f'\t\ttext_single = {{\n\t\t\tminimumsize = {{ {DATE_WIDTH} {LINE} }}\n\t\t\tmaximumsize = {{ {DATE_WIDTH} {LINE} }}\n'
                 '\t\t\tfontsize = 11\n\t\t\tdefault_format = "#weak"\n'
                 f'\t\t\talign = left|nobaseline\n\t\t\ttext = "[{g("date")}]"\n\t\t}}\n\t\texpand = {{}}\n\t}}\n'
                 '\tvbox = {\n\t\tlayoutpolicy_horizontal = expanding\n\t\tspacing = -1\n' + indent(first + joined, 2) + '\t}\n}\n')
    empty = f"StringIsEmpty(GetVariableSystem.Get(Concatenate('bd_days_', {SHOWN})))"
    # level with the sides' names: the dice, over the middle of the rolls
    body = (f'hbox = {{\n\twidget = {{\n\t\tsize = {{ {DATE_WIDTH + SQUARES_WIDTH} 24 }}\n\t}}\n'
            f'\twidget = {{\n\t\tsize = {{ {ROLL_WIDTH} 24 }}\n'
            f'\t\ticon = {{\n\t\t\tsize = {{ 22 22 }}\n\t\t\tparentanchor = center\n\t\t\ttexture = "{ICONS["dice"]}"\n'
            '\t\t\talwaystransparent = no\n\t\t\ttooltip = "BD_LOG_NOTE"\n\t\t}\n\t}\n'
            # the whole width of the column, as the lines below take it (a narrower line is centred in it)
            f'\twidget = {{\n\t\tsize = {{ {SQUARES_WIDTH + DATE_WIDTH} 24 }}\n\t}}\n}}\n'
            'vbox = {\n\tlayoutpolicy_horizontal = expanding\n\tignoreinvisible = yes\n\tspacing = -1\n' + indent(days, 1) + '}\n'
            f'text_multi = {{\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tmaximumsize = {{ {LOG_WIDTH} -1 }}\n'
            f'\talign = center|nobaseline\n\tfontsize = 13\n\tvisible = "[{empty}]"\n\ttext = "BD_NO_LOG"\n}}\n'
            'expand = {}\n')
    return (f'vbox = {{\n\tlayoutpolicy_vertical = expanding\n\tminimumsize = {{ {LOG_WIDTH} -1 }}\n\tmaximumsize = {{ {LOG_WIDTH} -1 }}\n'
            '\tspacing = 4\n' + indent(body, 1) + '}\n')


def recorder():
    """A battle changes only on the daily tick, so it is noted once a day: the one check made every frame is whether
    the battle's day note is today's. The notes are made in on_start, whose expressions are worked out only then. The
    first of our armies in the battle to see the new day notes it and sets the day, so the others don't."""
    same_battle = f"EqualTo_string({get('id', LIVE)}, {SUMS_LIVE})"
    # a new battle under an old name (a second battle at one place) starts its chain afresh
    old_last = f"Select_CString({same_battle}, {get('last', SUMS_LIVE)}, '')"
    notes = {"last": ROLL}
    # morale as the battle began: noted on its first day only
    for s, name in SIDES:
        side = f"Combat.Get{name}"
        notes |= {f"{s}_morv": f"Select_CString({same_battle}, {get(f'{s}_morv', SUMS_LIVE)}, Concatenate3("
                                f"{dec2(f'{side}.GetAverageMorale')}, ' / ', {dec2(f'{side}.GetMaxMorale')}))",
                  f"{s}_mor": f"Select_CString({same_battle}, {get(f'{s}_mor', SUMS_LIVE)}, {side}.GetMoraleTooltip)",
                  # what makes the maximum, of the side's leading army (as the game's army tooltip has it)
                  f"{s}_mors": f"Select_CString({same_battle}, {get(f'{s}_mors', SUMS_LIVE)}, {side}.GetLeadingUnit.GetMaxMoraleInfo)"}
        # whether it began below its maximum (1% off at least), and then what raises and lowers morale a day
        unit = f"{side}.GetLeadingUnit"
        low = f"LessThan_CFixedPoint({side}.GetAverageMorale, Multiply_CFixedPoint({side}.GetMaxMorale, '(CFixedPoint)0.99'))"
        for k, v in (("mrs", dec2(f"{side}.GetAverageMorale")), ("mrm", dec2(f"{side}.GetMaxMorale")),
                     ("morlow", f"Select_CString({low}, '1', '')"), ("morrp", f"Concatenate3('+', {dec2(f'Multiply_CFixedPoint({unit}.GetMoraleRecoveryPercent, {chr(39)}(CFixedPoint)100{chr(39)})')}, '%')"),
                     ("morr", f"{unit}.GetMoraleRecoveryInfo"), ("mormv", f"{unit}.GetMovementMoraleCostInfo"),
                     ("morat", f"{unit}.GetAttritionMoraleCostInfo"),
                     # the day's losses to moving and to attrition, as percents of the maximum; none when nothing
                     ("mmvv", morale_cost(f"{unit}.GetMovementMoraleCost")), ("matv", morale_cost(f"{unit}.GetAttritionMoraleCost"))):
            notes[f"{s}_{k}"] = f"Select_CString({same_battle}, {get(f'{s}_{k}', SUMS_LIVE)}, {v})"
    # the calls are made in order: the battle's id after all that read it (same_battle)
    notes |= {"id": SUMS_LIVE, "terr": TERRAIN}
    # the battlefield's terrain, per side (a river is crossed by the attacker only), for the combat power (power_steps)
    for t in TERRAINS:
        for s, attacker in (("a", True), ("d", False)):
            where = terrain_check(t, attacker)
            if where:
                notes[f"tr_{s}_{t}"] = f"Select_CString({where}, '1', '')"
    notes = {key(k, LIVE if k == 'id' else SUMS_LIVE): v for k, v in notes.items()}
    for s, name in SIDES:
        notes |= snapshots(s, f"Combat.Get{name}")
    notes[key("day", SUMS_LIVE)] = "GetDateString"
    start = f"Concatenate('bd_start_', {SUMS_LIVE})"
    notes[start] = f"Select_CString(StringIsEmpty(GetVariableSystem.Get({start})), GetDateString, GetVariableSystem.Get({start}))"
    starts = "".join(f'\t\ton_start = "[{st}]"\n' for st in battle_steps()
                     + [f"GetVariableSystem.Set('bd_tmp_same', Select_CString({same_battle}, '1', ''))"])
    if DEBUG:
        # TEST: the chain began (the day's note is set at its end: the two apart tell a chain cut short), and the last
        # chain of the session, with the battle it went to
        starts += (f'\t\ton_start = "[GetVariableSystem.Set(Concatenate(\'bd_fired_\', {SUMS_LIVE}), GetDateString)]"\n'
                   f'\t\ton_start = "[GetVariableSystem.Set(\'bd_lastfire\', Concatenate3(GetDateString, \' \', {SUMS_LIVE}))]"\n'
                   # whether a new variable can still be made (a cap on their number would stop the notes silently)
                   '\t\ton_start = "[GetVariableSystem.Set(Concatenate(\'bd_probe_\', GetDateString), \'1\')]"\n'
                   '\t\ton_start = "[GetVariableSystem.Set(\'bd_probe_ok\', Select_CString(GetVariableSystem.Exists('
                   'Concatenate(\'bd_probe_\', GetDateString)), GetDateString, GetVariableSystem.Get(\'bd_probe_ok\')))]"\n')
    starts += f'\t\ton_start = "[GetVariableSystem.Set(\'bd_tmp_date\', {short_date()})]"\n'
    starts += "".join(f'\t\ton_start = "[{st}]"\n' for st in journal_steps() + named_steps())
    if DEBUG:
        # TEST: every battle seen this session (before the id is noted, while same_battle still tells a new one)
        seen = "GetVariableSystem.Get('bd_seen')"
        starts += (f'\t\ton_start = "[GetVariableSystem.Set(\'bd_seen\', Select_CString({same_battle}, {seen}, '
                   f'Concatenate3({seen}, \' | \', {LIVE})))]"\n')
    # a new roll is a row of the chain (before 'last' is noted, while old_last still holds the one before)
    roll_row = day_event(f"Not(EqualTo_string({old_last}, {ROLL}))", "roll", ENTRY, SUMS_LIVE)
    # and its two numbers apart, so the colon stands in the same place on every line; a roll of the bombard phase
    # marked (rb), for the artillery icon by it
    split = "Not(StringIsEmpty(GetVariableSystem.Get('bd_tmp_add')))"
    for field, value in (("ra", "ToString_int32(Combat.GetAttacker.GetDiceWithModifiers)"),
                         ("rd", "ToString_int32(Combat.GetDefender.GetDiceWithModifiers)"),
                         ("rb", "Select_CString(Combat.IsInBombardPhase, '1', '')")):
        k = day_key(tmp("idx"), SUMS_LIVE, field)
        roll_row.append(f"GetVariableSystem.Set({k}, Select_CString({split}, {value}, GetVariableSystem.Get({k})))")
    starts += "".join(f'\t\ton_start = "[{st}]"\n' for st in roll_row + flank_rows() + frontage_steps())
    starts += "".join(f'\t\ton_start = "[GetVariableSystem.Set({k}, {v})]"\n' for k, v in notes.items())
    # Not inside a widget hidden with no battle, and checked by the army alone (whether it is in a battle, and its day
    # note), never by the battle: with no battle a check by the battle can't be worked out, and the widget kept its
    # last state, so the next battle of the army never showed it anew. Two of our armies in one battle both note it.
    unit_day = "Concatenate('bd_uday_', ToString_int32(Unit.GetID))"
    starts = f'\t\ton_start = "[GetVariableSystem.Set({unit_day}, GetDateString)]"\n' + starts
    # A widget made anew while its check already holds never shows anew, and its note never runs again: the game
    # remakes the list's widgets whenever the list of armies changes (many times a day at times), and the notes of a
    # battle stopped there. So a widget, when made, marks its army noted today: it hides, and the next day shows it
    # anew (a day lost at most).
    made = f'\t\ton_start = "[GetVariableSystem.Set({unit_day}, GetDateString)]"\n'
    if DEBUG:
        made += ("\t\ton_start = \"[GetVariableSystem.Set('bd_remade', Concatenate(GetDateString, "
                 "Select_CString(EqualTo_string(GetVariableSystem.Get('bd_remade_day'), GetDateString), ' (again)', '')))]\"\n"
                 "\t\ton_start = \"[GetVariableSystem.Set('bd_remade_day', GetDateString)]\"\n")
    # Two of them, one for the odd days and one for the even: each hides the next day by the date alone, so one stuck
    # shown without its note having run (it happened on the 1st of a month, the monthly tick's lag) shows anew two
    # days on, and the other runs the note the day between. The first to run sets the day, so the other doesn't.
    odd = "Or(Or3(StringContains(GetDateString, '1 '), StringContains(GetDateString, '3 '), StringContains(GetDateString, '5 ')), " \
          "Or(StringContains(GetDateString, '7 '), StringContains(GetDateString, '9 ')))"
    note = "".join(
        f'widget = {{\n\tsize = {{ 0 0 }}\n\tdatacontext = "[Unit.GetCombat]"\n'
        f'\tvisible = "[And3(Unit.GetCombat.IsValid, Not(EqualTo_string(GetVariableSystem.Get({unit_day}), GetDateString)), {parity})]"\n'
        f'\tvisible_at_creation = no\n\tstate = {{\n\t\tname = _show\n{starts}\t}}\n'
        f'\tstate = {{\n\t\tname = bd_made\n\t\ttrigger_on_create = yes\n{made}\t}}\n}}\n'
        for parity in (odd, f"Not({odd})"))
    return ("# Battle Details (see bd_build.py): notes every battle of the player's armies while it goes on, once a day.\n"
            "# Nothing here is shown. In peace (no war, revolt, civil war or risen rebels) only the first check is made.\n"
            "widget = {\n\tname = \"bd_recorder\"\n\tsize = { 0 0 }\n"
            f"\tvisible = \"[{AT_WAR}]\"\n"
            +
            # not datamodel_reuse_widgets: with it, the notes stopped on the 1st of a month
            "\tvbox = {\n\t\tdatamodel = \"[AccessPlayerUnits]\"\n"
            # armies only: naval battles are left alone
            "\t\titem = {\n\t\t\twidget = {\n\t\t\t\tsize = { 0 0 }\n\t\t\t\tvisible = \"[Unit.IsArmy]\"\n" + indent(note, 4)
            + "\t\t\t\twidget = {\n\t\t\t\t\tsize = { 0 0 }\n\t\t\t\t\tvisible = \"[Unit.GetCombat.IsValid]\"\n"
            "\t\t\t\t\tdatacontext = \"[Unit.GetCombat]\"\n"
            + indent(dice_recorder("a", "Attacker") + dice_recorder("d", "Defender") + arrivals(), 5)
            + "\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n")


# Damage done, per side and unit category. The game gives a regiment's strength damage of the day only as text
# ('...13#!@army_strength!...' for "Strength Damage Done: 13"), and the GUI can't turn text into a number. So the
# number is read digit by digit from the right: the last digit is the d for which the text holds 'd#!@army_strength',
# the one before it the d for 'd<digits found>#!@army_strength', and so on. The sums are kept as text ending in '~'
# and read back the same way. The steps go through scratch variables, in order.
SUM_TAIL = "~"
DIGITS = 6


def tmp(name):
    return f"GetVariableSystem.Get('bd_tmp_{name}')"


def read_digits(text, tail, name):
    """on_start calls that put the digits of the number standing before the text `tail` (an expression) in `text`
    into bd_tmp_<name>0.. (ones first); a digit not there is left empty."""
    steps = [f"GetVariableSystem.Set('bd_tmp_s', {text})", f"GetVariableSystem.Set('bd_tmp_suf', {tail})"]
    for k in range(DIGITS):
        digit = "''"
        for d in range(9, -1, -1):
            digit = f"Select_CString(StringContains({tmp('s')}, Concatenate('{d}', {tmp('suf')})), '{d}', {digit})"
        steps += [f"GetVariableSystem.Set('bd_tmp_{name}{k}', {digit})",
                  f"GetVariableSystem.Set('bd_tmp_suf', Concatenate({tmp(f'{name}{k}')}, {tmp('suf')}))"]
    return steps


def number(name):
    """The number of the digits read into bd_tmp_<name>0.."""
    value = "'(int32)0'"
    for k in range(DIGITS):
        digit = "'(int32)0'"
        for d in range(1, 10):
            digit = f"Select_int32(EqualTo_string({tmp(f'{name}{k}')}, '{d}'), '(int32){d}', {digit})"
        value = f"Add_int32({value}, Multiply_int32({digit}, '(int32){10 ** k}'))"
    return value


def side_total_key(side, battle, what="all"):
    return f"Concatenate3('bd_', {side}, Concatenate('_{what}_', {battle}))"


ICON = "gfx/interface/icons/"
ICONS = {"dice": ICON + "combat_modifiers/chance.dds", "morale": ICON + "military_army/army_morale.dds",
         "discipline": ICON + "military_army/discipline.dds", "tactics": ICON + "military_army/military_tactics.dds",
         "combined": ICON + "military_army/combined_arms.dds", "frontage": ICON + "unit_types/frontage.dds",
         "levy": ICON + "modifier_types/levy_combat_efficiency.dds", "experience": ICON + "unit_view/experience.dds"}


def tip(title, icon, concept, content):
    """A tooltip laid out as the game's (ContextualTooltipType): a title with an icon, then the content."""
    return ('tooltipwidget = {\n\tContextualTooltipType = {\n'
            f'\t\tblockoverride "title_text" {{\n\t\t\ttext = "{title}"\n\t\t}}\n'
            f'\t\tblockoverride "title_icon" {{\n\t\t\ticon = {{\n\t\t\t\tusing = tooltip_title_icon_size\n\t\t\t\ttexture = "{icon}"\n\t\t\t}}\n\t\t}}\n'
            f'\t\tblockoverride "concept_link" {{\n\t\t\ttext = "{concept}"\n\t\t}}\n'
            '\t\tblockoverride "tooltip_content" {\n' + indent(content, 3) + '\t\t}\n\t}\n}\n')


def pair_list(string, title=None, visible=None):
    """A string list (as the game's tooltips get them) in a tooltip."""
    vis = f'\tvisible = "[{visible}]"\n' if visible else ""
    head = (f'\tblockoverride "block_title" {{\n\t\ttext = "{title}"\n\t}}\n' if title
            else '\tblockoverride "block_title" {\n\t\tvisible = no\n\t}\n')
    return f'TooltipStringPairList = {{\n{vis}{head}\ttextcontext = "[{string}]"\n}}\n'


def fogged(country, string):
    """Sources of an enemy's modifiers only with enough intel on that country, as in the game's tooltips."""
    intel = f"HasCombatModifiersIntelOn({country}.Self)"
    return (pair_list(string, "LIST_TITLE_SOURCES", intel)
            + f'text_single = {{\n\tvisible = "[Not({intel})]"\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = no\n'
            '\talign = right|nobaseline\n\ttagtooltip_enabled = yes\n\ttext = "INTEL_FOG_COMBAT_MODIFIERS_UNKNOWN"\n}\n')


def dice_row(s, string):
    """The dice modifiers in a row, without the roll: the sum of the bonuses and of the penalties on the last day
    (noted by dice_recorder); each one in the tooltip, where in the game's dice list they are the rows with a bullet."""
    modifier = "StringContains(StringViewPair.GetLeft.GetString, '•')"
    rows = f'\tdatacontext = "[StringToStringPairList({string})]"\n\tdatamodel = "[StringPairList.GetRows]"\n'
    pos = f"GetVariableSystem.Get({sum_key(s, 'pos', SHOWN)})"
    neg = f"GetVariableSystem.Get({sum_key(s, 'neg', SHOWN)})"
    values = (f'text_single = {{\n\tfontsize = 15\n\tdefault_format = "#P"\n\ttext = "[Concatenate(\'+\', Select_CString(StringIsEmpty({pos}), \'0\', {pos}))]"\n}}\n'
              f'text_single = {{\n\tfontsize = 15\n\tdefault_format = "#N"\n\ttext = "[Select_CString(Or(StringIsEmpty({neg}), EqualTo_string({neg}, \'0\')), \'-0\', {neg})]"\n}}\n')
    listed = ('vbox = {\n\tlayoutpolicy_horizontal = expanding\n\tminimumsize = { 260 -1 }\n' + rows + '\titem = {\n'
              f'\t\thbox = {{\n\t\t\tvisible = "[{modifier}]"\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\tmargin = {{ 8 2 }}\n'
              '\t\t\ttext_single = {\n\t\t\t\ttext = "[StringViewPair.GetLeft.GetStringView]"\n\t\t\t}\n\t\t\texpand = {}\n'
              '\t\t\ttext_single = {\n\t\t\t\ttext = "[StringViewPair.GetRight.GetStringView]"\n\t\t\t}\n\t\t}\n\t}\n}\n'
              f'text_single = {{\n\tvisible = "[Not(StringContains({string}, \'•\'))]"\n\tmargin = {{ 8 2 }}\n\ttext = "BD_NO_DICE_MODS"\n}}\n')
    return ('hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tmargin = { 6 2 }\n\tspacing = 6\n\tusing = bg_text_mask_container_brown\n'
            f'\ticon = {{\n\t\tsize = {{ 24 24 }}\n\t\ttexture = "{ICONS["dice"]}"\n\t}}\n'
            '\ttext_single = {\n\t\tfontsize = 15\n\t\ttext = "BD_DICE_MODS"\n\t}\n\texpand = {}\n'
            + indent(values, 1)
            + indent(tip("BD_DICE_MODS", ICONS["dice"], "[battle|e]", listed), 1) + '}\n')


def stat(icon, label, value, tooltip="", visible=None):
    """A row: icon, heading, value; what makes the value in its tooltip."""
    vis = f'\tvisible = "[{visible}]"\n' if visible else ""
    icon_part = (f'\tblockoverride "icon" {{\n\t\ticon = {{\n\t\t\tsize = {{ 24 24 }}\n\t\t\ttexture = "{icon}"\n\t\t}}\n\t}}\n'
                 if icon else "")
    return (f'bd_row = {{\n{vis}{icon_part}\tblockoverride "label" {{\n\t\ttext = "{label}"\n\t}}\n'
            f'\tblockoverride "value" {{\n\t\ttext = "{value}"\n\t}}\n' + indent(tooltip, 1) + '}\n')


# the roll between the sides' flanks, and the dates on the left matched by as much room on the right, so that the
# rolls stand in the middle between the cards
ROLL_WIDTH = 72
LOG_WIDTH = 2 * DATE_WIDTH + 2 * SQUARES_WIDTH + ROLL_WIDTH


def log_title():
    """The heading of the rolls, a line above the sides' names: attacker : defender (how the chain is kept is in the
    tooltip of the dice over the rolls)."""
    # the colon over the rolls' colons (and the dice), the words running from it either way past the column if longer
    colon = DATE_WIDTH + SQUARES_WIDTH + ROLL_WIDTH // 2
    word = lambda anchor, x, text: (f'\ttext_single = {{\n\t\tparentanchor = {anchor}|vcenter\n\t\tposition = {{ {x} 0 }}\n'
                                    f'\t\tfontsize = 18\n\t\tdefault_format = "#high"\n\t\ttext = "{text}"\n\t}}\n')
    return (f'widget = {{\n\tsize = {{ {LOG_WIDTH} 24 }}\n'
            + word("right", -(LOG_WIDTH - colon + 6), "[attacker|E]")
            + f'\ttext_single = {{\n\t\tsize = {{ 12 24 }}\n\t\tposition = {{ {colon - 6} 0 }}\n\t\tautoresize = no\n\t\talign = center|nobaseline\n'
            '\t\tfontsize = 18\n\t\tdefault_format = "#high"\n\t\traw_text = ":"\n\t}\n'
            + word("left", colon + 6, "[defender|E]") + '}\n')


def terrain_arrows(s, category):
    """On a unit category's icon, at its right edge: a green arrow up at the top if a unit type of it in the battle
    fights better on this battlefield, a red one down at the bottom if worse (both if both); which and how much in
    their tooltip (noted by terrain_notes)."""
    arrows = ""
    for which, sign, texture, color, corner in (("p", "+", "arrow_up", "{ 0.35 0.85 0.35 1 }", "top"),
                                                ("n", "−", "arrow_down", "{ 0.95 0.3 0.3 1 }", "bottom")):
        notes = f"GetVariableSystem.Get(Concatenate3('bd_{s}_ter{which}_', {category}.GetNameWithNoTooltip, {SHOWN}))"
        arrows += (f'icon = {{\n\tsize = {{ 11 11 }}\n\tparentanchor = right|{corner}\n\ttexture = "{ICON}flat_icons/{texture}.dds"\n\tcolor = {color}\n'
                   f'\tvisible = "[StringContains({notes}, \'{sign}\')]"\n\talwaystransparent = no\n'
                   + indent(tip("BD_TERRAIN_TITLE", f"{ICON}flat_icons/{texture}.dds", "[topography|e]",
                                f'TooltipTextBlock = {{\n\tblockoverride "text" {{\n\t\ttext = "[{notes}]"\n\t}}\n}}\n'), 1) + '}\n')
    return arrows


def fmt_k(x):
    """A number of men (fixed point) as thousands with two decimals: 1234 -> '1.23K'."""
    n = f"FixedPointToInt({x})"
    frac = f"Divide_int32(Modulo_int32({n}, '(int32)1000'), '(int32)10')"
    return join([f"ToString_int32(Divide_int32({n}, '(int32)1000'))", "'.'",
                 f"Select_CString(LessThan_int32({frac}, '(int32)10'), Concatenate('0', ToString_int32({frac})), ToString_int32({frac}))", "'K'"])


# what the result popup tells of a unit category, noted as it opens (popup_record) for the journal
UNIT_STATS = {"usz": "BattleUnitStats.GetSize", "uls": "Add_CFixedPoint(BattleUnitStats.GetDestroyed, BattleUnitStats.GetImprisoned)",
              "ude": "BattleUnitStats.GetDestroyed", "uim": "BattleUnitStats.GetImprisoned"}


def unit_icons(s, name, journal=False):
    """The unit categories the side had, each as its icon and men at the start (from the popup's own stats); its units
    (count, type, strength) as the battle began in its tooltip, and as it ended in the tooltip of the losses. In the
    journal the six categories of an army one by one, with the popup's stats as noted."""
    if journal:
        items = [unit_item(s, f"GetSubUnitCategory('{c}')", True) for c in categories()[:6]]
        return unit_rows(["".join(items[:4]), "".join(items[4:])])
    return unit_item(s, "BattleUnitStats.GetCategory", False, name)


def unit_item(s, category, journal, name=None):
    """One unit category (see unit_icons); in the popup the rows of the categories over its datamodel."""
    noted = lambda what: f"GetVariableSystem.Get({cat_key(s, category, SHOWN, what)})"
    string = f"GetVariableSystem.Get({cat_key(s, category, SHOWN)})"
    # a category got by its key needs .Self here, as the game's own files have it
    texture = f"[GetSubUnitCategoryIcon({category}.Self)]" if journal else f"[GetSubUnitCategoryIcon({category})]"
    units_tip = indent(tip(f"[{category}.GetNameWithNoTooltip]", texture, "[army|e]", pair_list(string)), 1)
    # the losses, and the units left as the battle ended
    left = f"GetVariableSystem.Get({cat_key(s, category, SHOWN, 'catend')})"
    # in the journal the popup's stats as noted, in the popup its own
    if journal:
        visible = f"Not(Or(StringIsEmpty({noted('usz')}), EqualTo_string({noted('usz')}, '0.00K')))"
        size, lost = f"[{noted('usz')}]", f"-[{noted('uls')}]"
        parts = ["Localize('BD_LOST_PRE')", noted("ude"), "Localize('BD_LOST_MID')", noted("uim"), "Localize('BD_LOST_END')"]
        lost_text = f"[{join(parts)}]"
    else:
        visible = "Not(EqualTo_CFixedPoint(BattleUnitStats.GetSize, '(CFixedPoint)0'))"
        size, lost = "[BattleUnitStats.GetSize|K1]", "-[Add_CFixedPoint(BattleUnitStats.GetDestroyed, BattleUnitStats.GetImprisoned)|K1]"
        lost_text = "BD_LOSSES_TT"
    losses_tip = tip(f"[{category}.GetNameWithNoTooltip]", texture, "[army|e]",
                     f'TooltipTextBlock = {{\n\tblockoverride "text" {{\n\t\ttext = "{lost_text}"\n\t}}\n}}\n'
                     + pair_list(left, "BD_LEFT", f"Not(StringIsEmpty({left}))"))
    power = f"GetVariableSystem.Get(Concatenate({cat_key(s, category, SHOWN, 'pw')}, '_f'))"
    item = (f'hbox = {{\n\tvisible = "[{visible}]"\n\tspacing = 2\n'
            # the icon and the men at the start: its units in the tooltip
            # with the terrain arrows on its right edge
            + f'\twidget = {{\n\t\tsize = {{ 28 28 }}\n'
            f'\t\ticon = {{\n\t\t\tsize = {{ 28 28 }}\n\t\t\ttexture = "{texture}"\n\t\t\talwaystransparent = no\n' + indent(units_tip, 1) + '\t\t}\n'
            + indent(terrain_arrows(s, category), 2)
            + '\t}\n'
            # in a column, each with its own tooltip: the men at the start, the losses (killed and captured); all to
            # the right, so that their digits line up, in a column of a set width (right-aligned lines give it none),
            # as wide as '-18.3K', the same for every category so that the two rows line up
            + '\tvbox = {\n\t\tminimumsize = { 40 -1 }\n\t\tmaximumsize = { 40 -1 }\n\t\tspacing = -4\n'
            # its combat power (power_steps), yellow, with the game's icon
            + f'\t\thbox = {{\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\tspacing = 2\n\t\t\talwaystransparent = no\n\t\t\ttooltip = "BD_POWER_TT"\n'
            f'\t\t\tvisible = "[Not(StringIsEmpty({power}))]"\n\t\t\texpand = {{}}\n'
            f'\t\t\ticon = {{\n\t\t\t\tsize = {{ 12 12 }}\n\t\t\t\ttexture = "{ICON}unit_types/combat_power.dds"\n\t\t\t}}\n'
            f'\t\t\ttext_single = {{\n\t\t\t\tfontsize = 13\n\t\t\t\tdefault_format = "#color_yellow"\n\t\t\t\ttext = "[{power}]"\n\t\t\t}}\n\t\t}}\n'
            + '\t\ttext_single = {\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\talign = right|nobaseline\n\t\t\tfontsize = 13\n'
            f'\t\t\tdefault_format = "#high"\n\t\t\ttext = "{size}"\n\t\t\talwaystransparent = no\n'
            + indent(units_tip, 2) + '\t\t}\n'
            '\t\ttext_single = {\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\talign = right|nobaseline\n\t\t\tfontsize = 13\n\t\t\tdefault_format = "#N"\n'
            f'\t\t\traw_text = "{lost}"\n'
            '\t\t\talwaystransparent = no\n' + indent(losses_tip, 2) + '\t\t}\n\t}\n}\n')
    if journal:
        return item
    # the six categories in two rows, the first four (infantry and cavalry) and the rest (artillery and auxiliary), so
    # that all fit the card (a dynamicgridbox here crashed the game)
    stats = f"BattleResultMessage.Get{name}.GetUnitStats"
    out = unit_rows([f'datamodel = "[{part}]"\nitem = {{\n' + indent(item, 1) + '}\n'
                     for part in (f"DataModelFirst({stats}, '(int32)4')", f"DataModelSkipFirst({stats}, '(int32)4')")])
    if DEBUG:
        # TEST: the rows of each category's units as noted, left and right, to see what they hold
        out += (f'vbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tdatamodel = "[{stats}]"\n\titem = {{\n'
                f'\t\tvbox = {{\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\tdatacontext = "[StringToStringPairList({string})]"\n'
                '\t\t\tdatamodel = "[StringPairList.GetRows]"\n\t\t\titem = {\n\t\t\t\ttext_single = {\n\t\t\t\t\tfontsize = 11\n'
                '\t\t\t\t\traw_text = "TEST L<[StringViewPair.GetLeft.GetString]> R<[StringViewPair.GetRight.GetString]>"\n'
                '\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n')
    return out


def unit_rows(rows):
    """The unit categories' block of a card: its two rows (each the contents of an hbox) to the right."""
    out = "".join(f'hbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tspacing = 6\n\tignoreinvisible = yes\n\texpand = {{}}\n'
                  f'\thbox = {{\n\t\tspacing = 6\n\t\tignoreinvisible = yes\n' + indent(row, 2) + '\t}\n}\n' for row in rows)
    return ('vbox = {\n\tlayoutpolicy_horizontal = expanding\n\tmargin = { 6 2 }\n\tspacing = 2\n\tignoreinvisible = yes\n'
            '\tusing = bg_text_mask_container_brown\n' + indent(out, 1) + '}\n')


# modifiers that change how a commander's battle goes: a trait of another category with one of them (a ruler's Craven,
# Strict...) is shown with the general traits
COMBAT_MODIFIER = re.compile(r"^(commander_combat_bonus|military_tactics|discipline|land_morale_modifier|army_[a-z_]+_power"
                             r"|possible_frontage_modifier|army_initiative|[a-z_]*morale_damage[a-z_]*)$")


def combat_traits():
    """category -> the keys of its traits with a combat modifier, for every category but general (all shown) and
    admiral (the mod is about land battles)."""
    out = {}
    for key, body in game_blocks("traits").items():
        category = re.search(r"\bcategory\s*=\s*(\w+)", body)
        if category and category.group(1) not in ("general", "admiral") and any(
                COMBAT_MODIFIER.match(k) for k in re.findall(r"([a-z_]+)\s*=\s*-?[0-9.]+", body)):
            out.setdefault(category.group(1), []).append(key)
    return out


def trait_lists(character):
    """(datamodel, condition on the Trait or None) for the traits of a character shown with its commander: all its
    general ones, and of the others those with a combat modifier."""
    lists = [(f"{character}.GetTraitsByCategory('general')", None)]
    for category, keys in sorted(combat_traits().items()):
        names = [f"EqualTo_string(Trait.GetNameWithNoTooltip, Localize('{k}'))" for k in keys]
        while len(names) > 1:
            names = [f"Or({names[i]}, {names[i + 1]})" if i + 1 < len(names) else names[i] for i in range(0, len(names), 2)]
        lists.append((f"{character}.GetTraitsByCategory('{category}')", names[0]))
    return lists


def commander(s=None):
    """The commander's name and abilities (administrative / diplomatic / military) with the game's icons; for the
    journal (side `s`) as the popup noted them."""
    if s:
        name = get(f"{s}_cmd", SHOWN)
        valid = f"Not(StringIsEmpty({name}))"
        shown = f"Select_CString({valid}, {name}, Localize('BD_NO_COMMANDER'))"
        ability = lambda a: get(f"{s}_{a}", SHOWN)
        context = ""
        # the character is gone: its general traits by name, as the popup noted them, in the name's tooltip
        traits = get(f"{s}_trt", SHOWN)
        name_tip = (f'\t\talwaystransparent = no\n\t\ttooltip = "[Select_CString(StringIsEmpty({traits}), Localize(\'BD_NO_TRAITS\'), '
                    f'Concatenate(Localize(\'BD_TRAITS\'), {traits}))]"\n')
        trait_icons = ""
    else:
        valid = "BattleSide.GetCommander.IsValid"
        shown = "Select_CString(BattleSide.GetCommander.IsValid, BattleSide.GetCommander.GetNameWithNoTooltip, Localize('BD_NO_COMMANDER'))"
        ability = lambda a: f"BattleSide.GetCommander.GetAbility('{a}')"
        context = '\t\tdatacontext = "[BattleSide.GetCommander]"\n'
        name_tip = ""
        # the general traits and the others with a combat modifier (trait_lists), as the game draws traits, with their
        # tooltip
        trait_icons = "".join(
            f'hbox = {{\n\tspacing = 2\n\tignoreinvisible = yes\n\tdatamodel = "[{model}]"\n'
            '\titem = {\n\t\twidget = {\n\t\t\tsize = { 20 20 }\n' + (f'\t\t\tvisible = "[{shown_if}]"\n' if shown_if else '')
            + '\t\t\tusing = trait_item\n\t\t\tblockoverride "trait_item_size" {\n\t\t\t\tsize = { 20 20 }\n\t\t\t}\n\t\t}\n\t}\n}\n'
            for model, shown_if in trait_lists("Character"))
    # the game's ability icons take their colour from the character, which the journal has no more: a plain one there
    ability_icon = (lambda a: f'icon = {{\n\tsize = {{ 22 22 }}\n\ttexture = "{ICON}abilities/{a}_silver.dds"\n}}\n') if s else (
        lambda a: f'widget = {{\n\tsize = {{ 22 22 }}\n\tusing = icon_{a}_alt\n}}\n')
    abilities = trait_icons + "".join(
        ability_icon(a)
        + f'text_single = {{\n\tfontsize = 15\n\tdefault_format = "#high"\n\ttext = "[{ability(a)}]"\n}}\n'
        for a in ("adm", "dip", "mil"))
    # the heading as the general's icon, not words: the row has the traits to hold too
    return ('hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tmargin = { 6 2 }\n\tspacing = 6\n\tusing = bg_text_mask_container_brown\n'
            '\ticon = {\n\t\tsize = { 22 22 }\n\t\ttexture = "gfx/interface/icons/character_roles/general.dds"\n'
            '\t\talwaystransparent = no\n\t\ttooltip = "[commander|E]"\n\t}\n\texpand = {}\n'
            f'\ttext_single = {{\n\t\tfontsize = 15\n\t\tdefault_format = "#high"\n\t\ttext = "[{shown}]"\n{name_tip}\t}}\n'
            f'\thbox = {{\n\t\tvisible = "[{valid}]"\n{context}\t\tspacing = 3\n'
            + indent(abilities, 2) + '\t}\n}\n')


def morale_row(g):
    """Morale at the start of max, each number with its own tooltip: the start's the game's morale tooltip and, if it
    was below the maximum, what raised and lowered it a day; the maximum's what makes it. (A battle noted before the
    two were kept apart shows them as one.)"""
    # the modifiers alone: not the base value, nor attrition's multiplier (MORALE_ATTRITION_SCALING, English in every
    # language)
    left = "StringViewPair.GetLeft.GetString"
    is_modifier = f"Not(Or(StringContains({left}, Localize('BD_BASE_TAG')), StringContains({left}, 'Multiplied by')))"

    def rates(info, title, total, shown, filtered=True):
        row_shown = is_modifier if filtered else f"Not(StringContains({left}, 'Multiplied by'))"
        rows = (f'vbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tminimumsize = {{ 300 -1 }}\n\tvisible = "[{shown}]"\n'
                f'\ttext_single = {{\n\t\tmargin = {{ 8 4 }}\n\t\tdefault_format = "#high"\n'
                f'\t\ttext = "[Concatenate3(Localize(\'{title}\'), \' \', {total})]"\n\t}}\n'
                f'\tvbox = {{\n\t\tlayoutpolicy_horizontal = expanding\n\t\tdatacontext = "[StringToStringPairList({info})]"\n'
                '\t\tdatamodel = "[StringPairList.GetRows]"\n\t\titem = {\n'
                f'\t\t\thbox = {{\n\t\t\t\tvisible = "[{row_shown}]"\n\t\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\t\tmargin = {{ 8 2 }}\n'
                '\t\t\t\ttext_single = {\n\t\t\t\t\ttext = "[StringViewPair.GetLeft.GetStringView]"\n\t\t\t\t}\n\t\t\t\texpand = {}\n'
                '\t\t\t\ttext_single = {\n\t\t\t\t\ttext = "[StringViewPair.GetRight.GetStringView]"\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n')
        return rows

    low = f"EqualTo_string({g('morlow')}, '1')"
    start = tip("game_concept_morale", ICONS["morale"], "[morale|e]",
                # recovery with its base value (the most of it), the losses without (it is multiplied away)
                rates(g("morr"), "BD_MORR_TITLE", g("morrp"), low, filtered=False)
                + rates(g("mormv"), "BD_MORMV_TITLE", g("mmvv"), f"And({low}, Not(StringIsEmpty({g('mmvv')})))")
                + rates(g("morat"), "BD_MORAT_TITLE", g("matv"), f"And({low}, Not(StringIsEmpty({g('matv')})))"))
    maximum = tip("game_concept_morale", ICONS["morale"], "[morale|e]", pair_list(g("mors"), "MAX_MORALE_DUE_TO"))
    split = f"Not(StringIsEmpty({g('mrs')}))"
    value = lambda text, tooltip, when, tip_when=None: (
        f'\ttext_single = {{\n\t\tfontsize = 15\n\t\tdefault_format = "#high"\n\t\tvisible = "[{when}]"\n'
        f'\t\traw_text = "{text}"\n\t\talwaystransparent = no\n'
        + (f'\t\ttooltip_enabled = "[{tip_when}]"\n' if tip_when else '') + indent(tooltip, 2) + '\t}\n')
    # the start's tooltip only when it began below its maximum (there is nothing else in it); a battle noted before
    # the numbers were kept apart shows them as one, with the maximum's tooltip
    return ('hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tmargin = { 6 2 }\n\tspacing = 6\n\tusing = bg_text_mask_container_brown\n'
            f'\ticon = {{\n\t\tsize = {{ 24 24 }}\n\t\ttexture = "{ICONS["morale"]}"\n\t}}\n'
            '\ttext_single = {\n\t\tfontsize = 15\n\t\ttext = "BD_MORALE_START"\n\t}\n\texpand = {}\n'
            + value(f"[{g('mrs')}]", start, split, low)
            + f'\ttext_single = {{\n\t\tfontsize = 15\n\t\tdefault_format = "#high"\n\t\tvisible = "[{split}]"\n\t\traw_text = " / "\n\t}}\n'
            + value(f"[{g('mrm')}]", maximum, split)
            + value(f"[{g('morv')}]", maximum, f"Not({split})") + '}\n')


def result_side(s, name, journal=False):
    """One side in the result popup, from the notes (datacontext BattleSide); in the journal all as noted, the country
    by its tag."""
    g = lambda k: get(f"{s}_{k}", SHOWN)
    country = f"GetCountry({g('tag')})" if journal else "BattleSide.GetMainParticipant"
    country_name = g("cn") if journal else f"{country}.GetName"
    body = (
        'hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tspacing = 6\n\texpand = {}\n'
        f'\tcountry_flag_small = {{\n\t\tdatacontext = "[{country}]"\n' + (f'\t\tvisible = "[Not(StringIsEmpty({g("tag")}))]"\n' if journal else '')
        + '\t}\n'
        f'\ttext_single = {{\n\t\talign = nobaseline\n\t\tfontsize = 16\n\t\tdefault_format = "#high"\n\t\ttext = "[{country_name}]"\n\t}}\n'
        '\texpand = {}\n}\n'
        + commander(s if journal else None)
        + dice_row(s, g("dice"))
        + morale_row(g)
        + stat(ICONS["discipline"], "[discipline|E]", f"[{g('disc')}]",
               tip("game_concept_discipline", ICONS["discipline"], "[discipline|e]", fogged(country, g("discs"))))
        + stat(ICONS["tactics"], "[military_tactics|E]", f"[{g('tac')}]",
               tip("game_concept_military_tactics", ICONS["tactics"], "[military_tactics|e]", fogged(country, g("tacs"))))
        + stat(ICONS["experience"], "BD_EXPERIENCE", f"[{g('exp')}]",
               tip("game_concept_experience", ICONS["experience"], "[experience|e]", pair_list(g("exps"))))
        + stat(ICONS["levy"], "[levy_combat_efficiency|E]", f"[{g('levy')}]",
               tip("game_concept_levy_combat_efficiency", ICONS["levy"], "[levy_combat_efficiency|e]", fogged(country, g("levys"))))
        + stat(ICONS["frontage"], "[frontage|E]", f"[{g('front')}]",
               tip("POSSIBLE_FRONTAGE", ICONS["frontage"], "[frontage|e]", pair_list(g("fronts"), "LIST_TITLE_SOURCES")))
        + stat(ICONS["combined"], "[combined_arms|E]", f"[{g('ca')}]",
               tip("game_concept_combined_arms", ICONS["combined"], "[combined_arms|e]", pair_list(g("cas"))),
               f"Not(StringIsEmpty({g('cas')}))")
        + unit_icons(s, name, journal)
        + "expand = {}\n"
    )
    context = "" if journal else f'\tdatacontext = "[BattleResultMessage.GetBattleResult.Get{name}]"\n'
    return 'vbox = {\n\tusing = bd_column\n' + context + indent(body, 1) + "}\n"


def outcome(s, journal=False):
    """'Victory' or 'Defeat' over a side's card, as the popup's own header tells it: the player's side won when the
    player won. In the journal by the winner the popup noted (nothing if it was never opened)."""
    if journal:
        winner = get("won", SHOWN)
        won, lost = f"EqualTo_string({winner}, '{s}')", f"And(Not(StringIsEmpty({winner})), Not(EqualTo_string({winner}, '{s}')))"
    else:
        w, pa, pd = "BattleResultMessage.IsPlayerWinner", "BattleResultMessage.IsPlayerAttacker", "BattleResultMessage.IsPlayerDefender"
        own, other = (pa, pd) if s == "a" else (pd, pa)
        won = f"Or(And({w}, {own}), And(Not({w}), {other}))"
        lost = f"Not({won})"
    out = "".join(f'text_single = {{\n\tparentanchor = center\n\talign = nobaseline\n\tfontsize = 26\n\tvisible = "[{when}]"\n\ttext = "{key}"\n}}\n'
                  for when, key in ((won, "BD_WON"), (lost, "BD_LOST")))
    return f'widget = {{\n\tsize = {{ {CARD_WIDTH} 48 }}\n' + indent(out, 1) + '}\n'


def report(journal=False):
    """A battle's report: each side's outcome over its card, the battlefield and the rolls' heading between them; then
    the sides next to each other, both from the top, and the rolls between them. In the journal all as noted."""
    head = ("hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tspacing = 10\n\texpand = {}\n"
            + indent(outcome("a", journal), 1)
            + f'\tvbox = {{\n\t\tminimumsize = {{ {LOG_WIDTH} -1 }}\n\t\tspacing = 4\n'
            # the battlefield's line is wider than the column: let it run over the sides (where the outcome stands in
            # the middle of its card) rather than be shrunk to fit
            f'\t\twidget = {{\n\t\t\tsize = {{ {LOG_WIDTH} 20 }}\n'
            f'\t\t\ttext_single = {{\n\t\t\t\tparentanchor = center\n\t\t\t\talign = nobaseline\n\t\t\t\tfontsize = 14\n'
            f'\t\t\t\ttext = "[{get("terr", SHOWN)}]"\n\t\t\t}}\n\t\t}}\n'
            + indent(log_title(), 2) + "\t}\n"
            + indent(outcome("d", journal), 1) + "\texpand = {}\n}\n")
    sides = ("hbox = {\n\tlayoutpolicy_horizontal = expanding\n\tspacing = 10\n\texpand = {}\n"
             + indent(result_side("a", "Attacker", journal) + log_block() + result_side("d", "Defender", journal), 1)
             + "\texpand = {}\n}\n")
    return head + sides


WIPE = "EqualTo_CFixedPoint(BattleResultMessage.GetBattleResult.GetWinner.GetTotalLossesValue, '(CFixedPoint)0')"


def result_panel():
    recorded = f"Not(StringIsEmpty({get('id', DONE)}))"
    body = (
        # the battle shown, for the rows of its chain (SHOWN)
        'widget = {\n\tsize = { 0 0 }\n\tvisible = "[GetVariableSystem.Exists(\'bd_result\')]"\n\tvisible_at_creation = no\n'
        f'\tstate = {{\n\t\tname = _show\n\t\ton_start = "[GetVariableSystem.Set(\'bd_shown\', {SUMS_DONE})]"\n\t}}\n}}\n'
        # not recorded: a stack wipe (the winner lost no one: there were no days of fighting), or no battle of ours
        + "".join(f'text_multi = {{\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tmaximumsize = {{ 700 -1 }}\n'
                  f'\talign = center|nobaseline\n\tfontsize = 14\n\tvisible = "[And(Not({recorded}), {when})]"\n\ttext = "{text}"\n}}\n'
                  for when, text in ((WIPE, "BD_STACK_WIPE"), (f"Not({WIPE})", "BD_NO_RECORD")))
        # TEST: this battle's name, and every battle the recorder has seen this session
        + (f'text_multi = {{\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tmaximumsize = {{ 900 -1 }}\n'
           f'\talign = center|nobaseline\n\tfontsize = 12\n\tvisible = "[Not({recorded})]"\n'
           f'\traw_text = "TEST this \'[{DONE}]\', seen: [GetVariableSystem.Get(\'bd_seen\')]"\n}}\n' if DEBUG else '')
        + f'vbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tspacing = 4\n\tvisible = "[{recorded}]"\n'
        + indent(report(), 1)
        # TEST: the battle shown (its key), the last day the recorder noted it, and how many days its chain has
        + (f'\ttext_single = {{\n\t\tlayoutpolicy_horizontal = expanding\n\t\talign = center|nobaseline\n\t\tfontsize = 11\n'
           f'\t\traw_text = "TEST [{SHOWN}], last fired [GetVariableSystem.Get(Concatenate(\'bd_fired_\', {SHOWN}))], '
           f'last noted [{get("day", SHOWN)}], days [GetVariableSystem.Get(Concatenate(\'bd_days_\', {SHOWN}))]; '
           f'power: men [{tmp("n6")}{tmp("n5")}{tmp("n4")}{tmp("n3")}{tmp("n2")}{tmp("n1")}{tmp("n0")}] cp [{tmp("cpi")}] terrain [{tmp("tfi")}] '
           f'country [{tmp("m")}] levy [{tmp("lv")}] value [{tmp("v")}] in [{tmp("pu")}]; '
           f'last chain [GetVariableSystem.Get(\'bd_lastfire\')]; new keys made until [GetVariableSystem.Get(\'bd_probe_ok\')]; '
           f'seen [GetVariableSystem.Get(\'bd_seen\')]"\n\t}}\n'
           if DEBUG else '')
        + "}\n"
    )
    return ("type bd_result_details = widget {\n\tsize = { 100% 100% }\n\tvbox = {\n\t\tsize = { 100% 100% }\n"
            "\t\tmargin = { 30 0 }\n\t\tmargin_top = 40\n\t\tmargin_bottom = 52\n"
            "\t\tvbox = {\n\t\t\tusing = layoutpolicy_expanding\n\t\t\tusing = bg_age_event_inner\n\t\t\tusing = bg_age_event_frame\n"
            "\t\t\talwaystransparent = no\n\t\t\tscroll_list = {\n\t\t\t\tblockoverride \"scroll_list_layout\" {\n"
            "\t\t\t\t\tvbox = {\n\t\t\t\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\t\t\t\tmargin = { 10 8 }\n\t\t\t\t\t\tspacing = 4\n"
            + indent(body, 6) + "\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n}\n")


COMMON_TYPES = """# a row: icon, heading and value, with what makes the value in its tooltip
type bd_row = hbox {
	layoutpolicy_horizontal = expanding
	margin = { 6 2 }
	spacing = 6
	using = bg_text_mask_container_brown
	block "icon" {}
	text_single = {
		fontsize = 15
		block "label" {}
	}
	expand = {}
	text_single = {
		fontsize = 15
		default_format = "#high"
		block "value" {}
	}
}
"""

# wide enough for four unit categories in a row
CARD_WIDTH = 430
TEMPLATES = f"""template bd_column {{
	layoutpolicy_vertical = expanding
	minimumsize = {{ {CARD_WIDTH} -1 }}
	maximumsize = {{ {CARD_WIDTH} -1 }}
	spacing = 3
}}
"""


def types():
    return ("# Battle Details (see bd_build.py): the details panel of the battle result popup.\n"
            + TEMPLATES + "\ntypes BattleDetailsTypes {\n" + indent(COMMON_TYPES + "\n" + result_panel(), 1) + "}\n")


RESULT_HOOK = """# Battle Details: the button and the details over the losses; land battles only
widget = {
	size = { 100% 100% }
	visible = "[And(GetVariableSystem.Exists('bd_result'), BattleResultMessage.GetBattleResult.IsLand)]"
	bd_result_details = {}
}
button_regular_diamond = {
	visible = "[BattleResultMessage.GetBattleResult.IsLand]"
	parentanchor = bottom|left
	position = { 40 -22 }
	using = button_resize_to_fit_text
	tooltip_enabled = no
	text = "[SelectLocalization(GetVariableSystem.Exists('bd_result'), 'BD_HIDE', 'BD_DETAILS')]"
	onclick = "[GetVariableSystem.Toggle('bd_result')]"
}

"""


def result_popup():
    """The vanilla result popup with our button and panel, put before its close button (so drawn over the rest)."""
    text = game_gui("battle_result.gui")
    close = text.find('name = "dummy_button"')
    start = text.rfind("\t\twidget = {\n", 0, close)
    if close < 0 or text.count('name = "dummy_button"') != 1 or start < 0:
        raise SystemExit("battle_result.gui: the close button is not where the panel expects it")
    return text[:start] + indent(journal_outcome() + RESULT_HOOK, 2) + text[start:]


# The journal: the last JOURNAL battles of the session, newest first, each a numbered entry ('bd_j<field>_<n>'): its
# key (t, the token its notes go by), name, the day it began, the attacker's and the defender's country. A new battle
# moves the others one down. The outcome and the losses are noted by the result popup, when it is opened, by the key.
JOURNAL = 20
JOURNAL_FIELDS = {"t": SUMS_LIVE, "n": LIVE, "d": "GetVariableSystem.Get('bd_tmp_date')",
                  "a": "Combat.GetAttacker.GetCountry.GetNameWithNoTooltip", "f": "Combat.GetDefender.GetCountry.GetNameWithNoTooltip"}


def journal_steps():
    """on_start calls of the recorder that put a battle into the journal on its first day."""
    new = "StringIsEmpty(GetVariableSystem.Get('bd_tmp_same'))"
    steps = []
    for i in range(JOURNAL, 1, -1):
        for f in JOURNAL_FIELDS:
            steps.append(f"GetVariableSystem.Set('bd_j{f}_{i}', Select_CString({new}, GetVariableSystem.Get('bd_j{f}_{i - 1}'), "
                         f"GetVariableSystem.Get('bd_j{f}_{i}')))")
    for f, value in JOURNAL_FIELDS.items():
        steps.append(f"GetVariableSystem.Set('bd_j{f}_1', Select_CString({new}, {value}, GetVariableSystem.Get('bd_j{f}_1')))")
    return steps


def journal_outcome():
    """In the result popup, as it opens: what the journal's report takes from the popup alone, by the battle's key
    (bd_tmp_journal): whether we won (for the list) and which side did, each side's country, commander and unit
    categories (men, losses), and the damage that went to no category."""
    result = "BattleResultMessage.GetBattleResult"
    token = tmp("journal")
    w, pa, pd = "BattleResultMessage.IsPlayerWinner", "BattleResultMessage.IsPlayerAttacker", "BattleResultMessage.IsPlayerDefender"
    recorded = f"Not(StringIsEmpty({get('id', DONE)}))"
    steps = [f"GetVariableSystem.Set('bd_popup', {popup_match()})",
             f"GetVariableSystem.Set('bd_tmp_journal', {SUMS_DONE})",
             f"GetVariableSystem.Set(Concatenate('bd_jw_', {token}), Select_CString({w}, 'W', 'L'))",
             f"GetVariableSystem.Set(Concatenate('bd_jl_', {token}), "
             + join(["'-'", fmt_k(f"Multiply_CFixedPoint({result}.GetAttacker.GetTotalLossesValue, '(CFixedPoint)1000')"), "' / -'",
                     fmt_k(f"Multiply_CFixedPoint({result}.GetDefender.GetTotalLossesValue, '(CFixedPoint)1000')")]) + ")",
             f"GetVariableSystem.Set({key('won', token)}, Select_CString(Or(And({w}, {pa}), And(Not({w}), {pd})), 'a', 'd'))"]
    units = ""
    for s, name in SIDES:
        side = f"{result}.Get{name}"
        commander = f"{side}.GetCommander"
        steps += [f"GetVariableSystem.Set({key(f'{s}_tag', token)}, {side}.GetMainParticipant.GetTag)",
                  f"GetVariableSystem.Set({key(f'{s}_cn', token)}, {side}.GetMainParticipant.GetNameWithNoTooltip)",
                  f"GetVariableSystem.Set({key(f'{s}_cmd', token)}, Select_CString({commander}.IsValid, {commander}.GetNameWithNoTooltip, ''))"]
        steps += [f"GetVariableSystem.Set({key(f'{s}_{a}', token)}, ToString_int32({commander}.GetAbility('{a}')))" for a in ("adm", "dip", "mil")]
        # each its own match first: they may come before the popup's is noted
        stats = f'\t\t\t\ton_start = "[GetVariableSystem.Set(\'bd_tmp_pu\', {popup_match()})]"\n'
        stats += "".join(f'\t\t\t\ton_start = "[GetVariableSystem.Set({cat_key(s, "BattleUnitStats.GetCategory", tmp("pu"), what)}, {fmt_k(value)})]"\n'
                         for what, value in UNIT_STATS.items())
        units += (f'vbox = {{\n\tdatamodel = "[BattleResultMessage.Get{name}.GetUnitStats]"\n\titem = {{\n\t\twidget = {{\n\t\t\tsize = {{ 0 0 }}\n'
                  f'\t\t\tvisible = "[{recorded}]"\n\t\t\tvisible_at_creation = no\n'
                  '\t\t\tstate = {\n\t\t\t\tname = _show\n' + stats + '\t\t\t}\n\t\t}\n\t}\n}\n')
        # the commander's general traits by name, each once (the popup may be opened again)
        noted = f"GetVariableSystem.Get({key(f'{s}_trt', tmp('pu'))})"
        trait = "Trait.GetNameWithNoTooltip"
        add = (f"Select_CString(StringContains({noted}, {trait}), {noted}, "
               f"Concatenate3({noted}, Select_CString(StringIsEmpty({noted}), '', ', '), {trait}))")
        traits = (f'\t\t\t\ton_start = "[GetVariableSystem.Set(\'bd_tmp_pu\', {popup_match()})]"\n'
                  f'\t\t\t\ton_start = "[GetVariableSystem.Set({key(f"{s}_trt", tmp("pu"))}, {add})]"\n')
        for model, shown_if in trait_lists(f"{side}.GetCommander"):
            when = f"And({recorded}, {shown_if})" if shown_if else recorded
            units += (f'vbox = {{\n\tdatamodel = "[{model}]"\n\titem = {{\n\t\twidget = {{\n'
                      f'\t\t\tsize = {{ 0 0 }}\n\t\t\tvisible = "[{when}]"\n\t\t\tvisible_at_creation = no\n'
                      '\t\t\tstate = {\n\t\t\t\tname = _show\n' + traits + '\t\t\t}\n\t\t}\n\t}\n}\n')
    starts = "".join(f'\t\ton_start = "[{st}]"\n' for st in steps)
    return (f'widget = {{\n\tsize = {{ 0 0 }}\n\tvisible = "[{recorded}]"\n\tvisible_at_creation = no\n'
            '\tstate = {\n\t\tname = _show\n' + starts + '\t}\n}\n'
            + units + power_recorder())


JOURNAL_LIST_WIDTH = 290
# the report as in the popup: two cards, the rolls between them; its rows' spacing of 10 stands also between the
# stretches on either end and the cards
REPORT_WIDTH = 2 * CARD_WIDTH + LOG_WIDTH + 4 * 10


def journal():
    """The journal as a panel on the left, framed as the game's own (a header, back and close buttons): the battles a
    line each, newest first; a click opens the battle's report (journal_report). Back goes to the Military panel."""
    rows = ""
    for i in range(1, JOURNAL + 1):
        g = lambda f: f"GetVariableSystem.Get('bd_j{f}_{i}')"
        token = g("t")
        won = f"GetVariableSystem.Get(Concatenate('bd_jw_', {token}))"
        lost = f"GetVariableSystem.Get(Concatenate('bd_jl_', {token}))"
        text = lambda width, txt, fmt="", size=14: (f'\t\ttext_single = {{\n\t\t\tminimumsize = {{ {width} -1 }}\n\t\t\tmaximumsize = {{ {width} -1 }}\n'
                                                    f'\t\t\talign = left|nobaseline\n\t\t\tfontsize = {size}\n'
                                                    + (f'\t\t\tdefault_format = "{fmt}"\n' if fmt else '') + f'\t\t\ttext = "{txt}"\n\t\t}}\n')
        outcome_text = f"[SelectLocalization(EqualTo_string({won}, 'W'), 'BD_WON', SelectLocalization(EqualTo_string({won}, 'L'), 'BD_LOST', 'BD_NO_OUTCOME'))]"
        rows += ('button = {\n\tlayoutpolicy_horizontal = expanding\n\tsize = { -1 30 }\n\tusing = bg_text_mask_container_brown\n'
                 f'\tvisible = "[Not(StringIsEmpty({token}))]"\n'
                 f'\tdown = "[And(GetVariableSystem.Exists(\'bd_report\'), EqualTo_string(GetVariableSystem.Get(\'bd_shown\'), {token}))]"\n'
                 f'\tonclick = "[GetVariableSystem.Set(\'bd_shown\', {token})]"\n'
                 '\tonclick = "[GetVariableSystem.Set(\'bd_report\', \'1\')]"\n'
                 '\ttooltip = "BD_JOURNAL_ROW_TT"\n'
                 '\thbox = {\n\t\tsize = { 100% 100% }\n\t\tmargin = { 8 0 }\n\t\tspacing = 8\n'
                 # fixed columns but the name's, which takes what is left: the line never runs past the panel
                 + text(46, f"[{g('d')}]", "#weak", 12)
                 + f'\t\ttext_single = {{\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\tminimumsize = {{ 100 -1 }}\n'
                 f'\t\t\talign = left|nobaseline\n\t\t\tfontsize = 14\n\t\t\tdefault_format = "#high"\n\t\t\ttext = "[{g("n")}]"\n\t\t}}\n'
                 # the countries as the result popup names them (its main participants) once it was opened, else as noted
                 # (the side's leading army's country, which may be an ally)
                 + text(150, " – ".join(
                     f"[Select_CString(StringIsEmpty({get(f'{s}_cn', token)}), {g(f)}, {get(f'{s}_cn', token)})]"
                     for s, f in (("a", "a"), ("d", "f"))))
                 + text(70, outcome_text)
                 + text(105, f"[{lost}]", "#N", 13).replace("align = left|nobaseline", "align = right|nobaseline")
                 + '\t}\n}\n')
    empty = "StringIsEmpty(GetVariableSystem.Get('bd_jt_1'))"
    content = ('text_multi = {\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tfontsize = 12\n\tdefault_format = "#weak"\n'
               '\ttext = "BD_JOURNAL_NOTE"\n}\n'
               f'text_multi = {{\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tvisible = "[{empty}]"\n\tfontsize = 14\n'
               '\ttext = "BD_JOURNAL_EMPTY"\n}\n'
               + rows + (debug_lines() if DEBUG else '') + 'expand = {}\n')
    back = ('button_back_alt = {\n\tblockoverride "back_onclick" {\n\t\taction_tooltip = {\n\t\t\tclick_type = left\n\t\t\ttitle = "BACK"\n'
            '\t\t\ton_action = "[GetVariableSystem.Clear(\'bd_journal\')]"\n\t\t\ton_action = "[GetVariableSystem.Clear(\'bd_report\')]"\n'
            '\t\t\ton_action = "[OpenLateralView(\'unit_overview\')]"\n\t\t}\n\t}\n}\n')
    close = ('button_close_alt = {\n\tblockoverride "close_on_action" {\n\t\ton_action = "[GetVariableSystem.Clear(\'bd_journal\')]"\n'
             '\t\ton_action = "[GetVariableSystem.Clear(\'bd_report\')]"\n\t}\n}\n')
    return ("# Battle Details (see bd_build.py): the journal of this session's battles, a panel on the left.\n"
            'widget = {\n\tname = "bd_journal"\n\tusing = lateralview_left_setup\n'
            '\tvisible = "[GetVariableSystem.Exists(\'bd_journal\')]"\n'
            '\tvbox = {\n\t\tusing = layoutpolicy_expanding\n\t\tusing = lateralview_margins\n'
            '\t\tvbox = {\n\t\t\tusing = layoutpolicy_expanding\n\t\t\talwaystransparent = no\n\t\t\tusing = bg_lateralview\n'
            '\t\t\twindow_header_alt = {\n\t\t\t\tblockoverride "header_text" {\n\t\t\t\t\ttext = "BD_JOURNAL"\n\t\t\t\t}\n'
            '\t\t\t\tblockoverride "window_header_alt_color_texture" {\n\t\t\t\t\tusing = color_military_texture\n\t\t\t\t}\n\t\t\t}\n'
            # the panel's frame takes a strip on the right
            '\t\t\tvbox = {\n\t\t\t\tusing = layoutpolicy_expanding\n\t\t\t\tmargin = { 12 10 }\n\t\t\t\tmargin_right = 20\n'
            '\t\t\t\tspacing = 3\n\t\t\t\tignoreinvisible = yes\n'
            + indent(content, 4) + '\t\t\t}\n\t\t}\n\t}\n'
            '\twidget = {\n\t\tsize = { 100% 40 }\n'
            '\t\twidget = {\n\t\t\tsize = { 40 40 }\n' + indent(back, 3) + '\t\t}\n'
            '\t\twidget = {\n\t\t\tparentanchor = right\n\t\t\tsize = { 40 40 }\n' + indent(close, 3) + '\t\t}\n\t}\n}\n')


def journal_report():
    """A battle of the journal, its report as the result popup shows it, in a window of its own over the map."""
    close = ('button_close = {\n\tblockoverride "close_properties" {}\n'
             '\tblockoverride "close_on_action" {\n\t\ton_action = "[GetVariableSystem.Clear(\'bd_report\')]"\n\t}\n}\n')
    body = ('hbox = {\n\tlayoutpolicy_horizontal = expanding\n\texpand = {}\n' + indent(close, 1) + '}\n'
            + report(True) + 'expand = {}\n')
    return ("# Battle Details (see bd_build.py): the report of a battle of the journal.\n"
            f'widget = {{\n\tname = "bd_report"\n\tlayer = top\n\tparentanchor = center\n\tsize = {{ {REPORT_WIDTH + 40} 640 }}\n'
            '\tvisible = "[And(GetVariableSystem.Exists(\'bd_journal\'), GetVariableSystem.Exists(\'bd_report\'))]"\n\talwaystransparent = no\n'
            '\tusing = bg_age_event_inner\n\tusing = bg_age_event_frame\n'
            '\tvbox = {\n\t\tsize = { 100% 100% }\n\t\tmargin = { 20 12 }\n\t\tspacing = 4\n' + indent(body, 2) + '\t}\n}\n')


JOURNAL_BUTTON = """# Battle Details: the journal of this session's battles
widget = {
	size = { 45 45 }
	header_button_left = {
		parentanchor = center
		size = { 80% 80% }
		blockoverride "button_icon_stretch_sprite" {}
		blockoverride "header_button_frame_inner" { visible = no }
		blockoverride "header_button_icon_size" { size = { 30 30 } }
		blockoverride "header_button_text_layout" {}
		blockoverride "icon_overlay" {}
		blockoverride "icon_texture" {
			size = { 100% 100% }
			texture = "[GetConceptTexture('combat')]"
		}
		# in place of this panel, as the game's panels open one another
		onclick = "[GetVariableSystem.Set('bd_journal', '1')]"
		onclick = "[LateralView.Close]"
		tooltip = "BD_JOURNAL_TT"
	}
}
"""


PEACE_BUTTON = """
	# Battle Details: the journal of this session's battles
	button_regular_diamond = {
		parentanchor = bottom|left
		position = { 40 -22 }
		using = button_resize_to_fit_text
		tooltip = "BD_JOURNAL_TT"
		text = "BD_JOURNAL"
		onclick = "[GetVariableSystem.Set('bd_journal', '1')]"
	}
"""


def peace_popup():
    """The vanilla messages with the journal's button in the peace popup (the end of a war)."""
    text = game_gui("messages.gui")
    anchor = '\tname = "peace_message_popup"\n'
    if text.count(anchor) != 1:
        raise SystemExit("messages.gui: the peace popup is not where the journal's button expects it")
    at = text.find(anchor) + len(anchor)
    return text[:at] + PEACE_BUTTON + text[at:]


def military_panel():
    """The vanilla Military panel with the journal's button next to the armies' objective button."""
    text = game_gui("unit_overview.gui")
    anchor = 'datacontext = "[UnitOverview.GetSelectObjectiveArmyAction]"\n'
    at = text.find(anchor)
    end = text.find("}\n", at) + 2 if at >= 0 else -1
    if text.count(anchor) != 1 or end < 2:
        raise SystemExit("unit_overview.gui: the objective button is not where the journal's button expects it")
    return text[:end] + indent(JOURNAL_BUTTON, 6) + text[end:]


def debug_lines():
    """TEST, local build only: at the bottom of the journal, a line for each of our armies in a battle, with what the
    recorder checks (the battle, the day its note last ran for this army, today), to see why a note stops."""
    line = ("[Unit.GetNameWithNoTooltip] in [Unit.GetCombat.GetNameWithNoTooltip]: noted "
            "[GetVariableSystem.Get(Concatenate('bd_uday_', ToString_int32(Unit.GetID)))], today [GetDateString], "
            "army [Select_CString(Unit.IsArmy, 'yes', 'no')], war [Select_CString(" + AT_WAR + ", 'yes', 'no')]")
    return ('text_multi = {\n\tlayoutpolicy_horizontal = expanding\n\tautoresize = yes\n\tfontsize = 11\n'
            "\traw_text = \"TEST [GetDateString]; last chain [GetVariableSystem.Get('bd_lastfire')]; "
            "new keys made until [GetVariableSystem.Get('bd_probe_ok')]; recorder widgets made on [GetVariableSystem.Get('bd_remade')]\"\n}\n"
            'vbox = {\n\tlayoutpolicy_horizontal = expanding\n\tdatamodel = "[AccessPlayerUnits]"\n\titem = {\n'
            '\t\ttext_multi = {\n\t\t\tvisible = "[Unit.GetCombat.IsValid]"\n\t\t\tlayoutpolicy_horizontal = expanding\n'
            f'\t\t\tautoresize = yes\n\t\t\tfontsize = 11\n\t\t\traw_text = "TEST {line}"\n\t\t}}\n\t}}\n}}\n')


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    write("in_game/gui/bd_types.gui", types())
    write("in_game/gui/bd_recorder.gui", recorder())
    # a widget of its own file is made only when listed here
    write("in_game/gui/bd_journal.gui", journal())
    write("in_game/gui/bd_report.gui", journal_report())
    write("in_game/gui/scripted_widgets/bd_scripted_widgets.txt",
          "gui/bd_recorder.gui = bd_recorder\ngui/bd_journal.gui = bd_journal\ngui/bd_report.gui = bd_report\n")
    write("in_game/gui/battle_result.gui", result_popup())
    write("in_game/gui/unit_overview.gui", military_panel())
    write("in_game/gui/messages.gui", peace_popup())
    for lang in LANGS:
        lines = TEXT.get(lang, TEXT["english"])
        write(f"main_menu/localization/{lang}/bd_l_{lang}.yml", f"l_{lang}:\n" + "".join(f' {k}: "{v}"\n' for k, v in lines.items()))
    meta = {"name": "Battle Details" if RELEASE else "Battle Details [LOCAL]", "id": "grackbox.battle_details", "version": "0.1.1", "game_id": "eu5",
            "supported_game_version": "1.4.*",
            "short_description": "The battle window and the battle result laid open: dice and their sources, morale, discipline, tactics, and every roll.",
            "tags": ["User Interface", "Military", "1.4"],
            "relationships": [], "game_custom_data": {}}
    write(".metadata/metadata.json", json.dumps(meta, indent=4, ensure_ascii=False) + "\n")
    # the launcher's picture of the mod: the Workshop cover (make_cover.py)
    shutil.copyfile(os.path.join(HERE, "cover.png"), os.path.join(OUT, ".metadata", "thumbnail.png"))
    print("->", OUT)


if __name__ == "__main__":
    main()

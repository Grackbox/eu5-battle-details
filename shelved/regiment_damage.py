"""Shelved: the damage each regiment did in a battle, by unit category (and whom it hit), and Other kills.

Taken out of bd_build.py because it slowed big battles down and, with many regiments (after armies joined), the
recorder's daily note stopped firing. Each regiment in the line had a hidden widget (type bd_regiment_damage) checked
every frame, and on each new day it read its strength damage digit by digit from SubUnit.GetCombatDetails and added it
to its side's sum per category (~60 statements a regiment a day).

To bring it back, rework it first: note the damage less often (every few days) or per category at once, not per
regiment per day. The pieces as they were, with the places they plugged into:
- recorder(): `+ damage_recorder()` after the dice recorders, inside the per-army combat widget;
- types(): `damage_type()` in the BattleDetailsTypes block;
- unit_item(): `dealt = GetVariableSystem.Get(damage_key(repr(s), category, SHOWN, 'dmgk'))` and the sword line below;
- result_side(): `+ uncounted(s, journal)` after unit_icons;
- journal_outcome(): `steps += uncounted_steps(s)`;
- the loc keys below in TEXT (English and Russian).
"""
def thousands_of_digits(name):
    """The number read into bd_tmp_<name>0.. as thousands with two decimals, from its digits: 1234 -> '1.23K'."""
    d = lambda k: tmp(f"{name}{k}")
    or_zero = lambda x: f"Select_CString(StringIsEmpty({x}), '0', {x})"
    whole = join([d(k) for k in range(DIGITS - 1, 2, -1)])
    return join([or_zero(whole), "'.'", or_zero(d(2)), or_zero(d(1)), "'K'"])


def damage_key(side, category, battle, what):
    """A side's damage note for a unit category; `side` is an expression giving 'a' or 'd'."""
    return f"BD_Concatenate3(BD_Concatenate3('bd_', {side}, '_{what}_'), {category}.GetNameWithNoTooltip, {battle})"


TARGETS = ("army_light_infantry", "army_heavy_infantry", "army_light_cavalry", "army_heavy_cavalry",
           "army_artillery", "army_auxiliary")
UNCLEAR = "unclear"


def target_key(side, category, target, battle, what):
    """The damage a side's unit category did to one enemy category (`target` an expression giving its key)."""
    return (f"BD_Concatenate3(BD_Concatenate3('bd_', {side}, '_{what}_'), BD_Concatenate3({category}.GetNameWithNoTooltip, '_', {target}), "
            f"{battle})")


def side_total_key(side, battle, what="all"):
    return f"BD_Concatenate3('bd_', {side}, Concatenate('_{what}_', {battle}))"


def damage_steps(side, category, battle):
    """on_start calls that add a regiment's damage of the day (its SubUnit.GetCombatDetails) to the sums of its side
    in a battle: per unit category (shown as thousands), per enemy category it hit, and the side's whole, whose digits
    are kept one by one so the result popup can read it as a number (see uncounted)."""
    total = f"GetVariableSystem.Get({damage_key(side, category, battle, 'dmg')})"
    whole = f"GetVariableSystem.Get({side_total_key(side, battle)})"
    or_zero = lambda x: f"Select_CString(StringIsEmpty({x}), '0{SUM_TAIL}', {x})"
    return (read_digits("SubUnit.GetCombatDetails", DAMAGE_TAIL, "a")
            + read_digits(or_zero(total), repr(SUM_TAIL), "b")
            + [f"GetVariableSystem.Set({damage_key(side, category, battle, 'dmg')}, "
               f"Concatenate(ToString_int32(Add_int32({number('a')}, {number('b')})), '{SUM_TAIL}'))"]
            # shown as thousands, put together from the new sum's digits (as numbers, the statement was too big)
            + read_digits(total, repr(SUM_TAIL), "c")
            + [f"GetVariableSystem.Set({damage_key(side, category, battle, 'dmgk')}, {thousands_of_digits('c')})"]
            + target_steps(side, category, battle)
            + read_digits(or_zero(whole), repr(SUM_TAIL), "g")
            + [f"GetVariableSystem.Set({side_total_key(side, battle)}, "
               f"Concatenate(ToString_int32(Add_int32({number('a')}, {number('g')})), '{SUM_TAIL}'))"]
            + read_digits(whole, repr(SUM_TAIL), "h")
            + [f"GetVariableSystem.Set({side_total_key(side, battle, f'all{k}')}, {tmp(f'h{k}')})" for k in range(DIGITS)])


def target_steps(side, category, battle):
    """Whom the regiment hit: the enemy unit category whose icon its text holds (the icon's mark taken from the game,
    GetIcon: written out, '@' would not be found). The icon of a regiment that attacks it is in that text too (when
    just one does): with two categories found, which one was hit can't be told, and the day's damage goes to
    'unclear', as when none is found. The day's damage (digits a) is added to that pair's sum."""
    found = {c: f"StringContains(SubUnit.GetCombatDetails, GetSubUnitCategory('{c}').GetIcon)" for c in TARGETS}
    count = "'(int32)0'"
    for f in found.values():
        count = f"Add_int32({count}, Select_int32({f}, '(int32)1', '(int32)0'))"
    which = join([f"Select_CString({f}, '{c}', '')" for c, f in found.items()])
    target = tmp("tgt")
    total = f"GetVariableSystem.Get({target_key(side, category, target, battle, 'tgt')})"
    return ([f"GetVariableSystem.Set('bd_tmp_tgt', Select_CString(EqualTo_int32({count}, '(int32)1'), {which}, '{UNCLEAR}'))"]
            + read_digits(f"Select_CString(StringIsEmpty({total}), '0{SUM_TAIL}', {total})", repr(SUM_TAIL), "e")
            + [f"GetVariableSystem.Set({target_key(side, category, target, battle, 'tgt')}, "
               f"Concatenate(ToString_int32(Add_int32({number('a')}, {number('e')})), '{SUM_TAIL}'))"]
            + read_digits(total, repr(SUM_TAIL), "f")
            + [f"GetVariableSystem.Set({target_key(side, category, target, battle, 'tgtk')}, {thousands_of_digits('f')})"])


def target_tooltip(s, category):
    """The damage tooltip of a unit category in the result popup: what the number is, then whom it hit."""
    lines = ""
    for t in TARGETS + (UNCLEAR,):
        value = f"GetVariableSystem.Get({target_key(repr(s), category, repr(t), SHOWN, 'tgtk')})"
        name = "BD_UNCLEAR" if t == UNCLEAR else t
        lines += (f'hbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tmargin = {{ 8 1 }}\n\tvisible = "[Not(StringIsEmpty({value}))]"\n'
                  f'\ttext_single = {{\n\t\ttext = "{name}"\n\t}}\n\texpand = {{}}\n'
                  f'\ttext_single = {{\n\t\tdefault_format = "#color_yellow"\n\t\ttext = "[{value}]"\n\t}}\n}}\n')
    content = ('TooltipTextBlock = {\n\tblockoverride "text" {\n\t\ttext = "BD_DAMAGE_TT"\n\t}\n}\n'
               'text_single = {\n\tmargin = { 8 4 }\n\tdefault_format = "#high"\n\ttext = "BD_TARGETS_TITLE"\n}\n'
               'vbox = {\n\tlayoutpolicy_horizontal = expanding\n\tminimumsize = { 260 -1 }\n' + indent(lines, 1) + '}\n')
    return tip(f"[{category}.GetNameWithNoTooltip]", f"{ICON}abilities/mil_gold.dds", "[strength|e]", content)


def uncounted(s, journal=False):
    """The damage of a side that went to no unit category (see uncounted_steps): in the popup worked out when the
    details are opened, in the journal as noted."""
    value = f"GetVariableSystem.Get({side_total_key(repr(s), SHOWN if journal else SUMS_DONE, 'unc')})"
    work = "" if journal else (
        'widget = {\n\tsize = { 0 0 }\n\tvisible = "[GetVariableSystem.Exists(\'bd_result\')]"\n\tvisible_at_creation = no\n'
        '\tstate = {\n\t\tname = _show\n' + "".join(f'\t\ton_start = "[{st}]"\n' for st in uncounted_steps(s)) + '\t}\n}\n')
    return (work + f'hbox = {{\n\tlayoutpolicy_horizontal = expanding\n\tmargin = {{ 6 0 }}\n\tspacing = 2\n'
            f'\tvisible = "[And(Not(StringIsEmpty({value})), Not(EqualTo_string({value}, \'0.00K\')))]"\n'
            '\talwaystransparent = no\n\ttooltip = "BD_UNCOUNTED_TT"\n'
            '\ttext_single = {\n\t\tfontsize = 12\n\t\tdefault_format = "#weak"\n\t\ttext = "BD_UNCOUNTED"\n\t}\n\texpand = {}\n'
            f'\ticon = {{\n\t\tsize = {{ 11 11 }}\n\t\ttexture = "{ICON}abilities/mil_gold.dds"\n\t}}\n'
            f'\ttext_single = {{\n\t\tfontsize = 13\n\t\tdefault_format = "#color_yellow"\n\t\ttext = "[{value}]"\n\t}}\n}}\n')


def uncounted_steps(s):
    """In the result popup: on_start calls that work out the damage of a side that went to no unit category: the men
    the other side lost killed (losses less those this side captured) less its damage counted. It is the battle's last
    day (fought on the tick that ends the battle; after it no regiment's text holds it, ours neither) and the killing in
    the pursuit."""
    other = "Defender" if s == "a" else "Attacker"
    lost = f"BattleResultMessage.GetBattleResult.Get{other}"
    took = f"BattleResultMessage.GetBattleResult.Get{'Attacker' if s == 'a' else 'Defender'}"
    # the result gives them in thousands; a side's losses hold the men it lost captured, and the captured are counted
    # with the side that took them (GetTotalImprisoned)
    killed = (f"FixedPointToInt(Multiply_CFixedPoint(Subtract_CFixedPoint({lost}.GetTotalLossesValue, {took}.GetTotalImprisoned), "
              "'(CFixedPoint)1000'))")
    counted = "'(int32)0'"
    for k in range(DIGITS):
        d = f"GetVariableSystem.Get({side_total_key(repr(s), tmp('battle'), f'all{k}')})"
        digit = "'(int32)0'"
        for v in range(1, 10):
            digit = f"Select_int32(EqualTo_string({d}, '{v}'), '(int32){v}', {digit})"
        counted = f"Add_int32({counted}, Multiply_int32({digit}, '(int32){10 ** k}'))"
    rest = f"Max_int32(Subtract_int32({killed}, {counted}), '(int32)0')"
    shown = side_total_key(repr(s), SUMS_DONE, "unc")
    # the battle's key once, so the statement stays within the depth the game takes
    steps = ([f"GetVariableSystem.Set('bd_tmp_battle', {SUMS_DONE})", f"GetVariableSystem.Set('bd_tmp_rest', Concatenate(ToString_int32({rest}), '{SUM_TAIL}'))"]
             + read_digits(tmp("rest"), repr(SUM_TAIL), "r")
             + [f"GetVariableSystem.Set({shown}, {thousands_of_digits('r')})"])
    return steps


def damage_type():
    """A regiment in a battle's line (datacontext SubUnit, within CombatSubUnitArray and Combat): each day it is
    engaged, its strength damage of the day is added to its side's sum for its category. A note per regiment and day
    keeps it from being added twice when two of our armies are in the battle."""
    side = "Select_CString(CombatSubUnitArray.GetCombatSide.IsAttacker, 'a', 'd')"
    category = "SubUnit.GetDefinition.GetCategory"
    # one note a regiment, holding the day (a regiment is in one battle a day): not one per battle, the GUI's variables
    # are many enough already
    done = "Concatenate('bd_rd_', ToString_int32(SubUnit.GetID))"
    # the battle's key once, so the steps stay within the depth the game takes
    steps = ([f"GetVariableSystem.Set({done}, GetDateString)"] + battle_steps()
             + damage_steps(side, category, tmp("battle")))
    starts = "".join(f'\t\ton_start = "[{st}]"\n' for st in steps)
    return ("# Battle Details: a regiment's daily damage, added to its side's sum (see bd_build.py, damage_type)\n"
            "type bd_regiment_damage = widget {\n\tsize = { 0 0 }\n"
            f'\tvisible = "[And(SubUnit.IsEngaged, Not(EqualTo_string(GetVariableSystem.Get({done}), GetDateString)))]"\n'
            "\tvisible_at_creation = no\n\tstate = {\n\t\tname = _show\n" + starts + "\t}\n}\n")


def damage_recorder():
    """Every engaged regiment of both sides (as the game's battle window lists them: GetSubUnits gives no items), on
    land only."""
    lines = ""
    for name in ("Attacker", "Defender"):
        for flank in ("Left", "Center", "Right"):
            lines += (f'vbox = {{\n\tdatacontext = "[Combat.Get{name}.Get{flank}]"\n\tdatamodel = "[CombatSubUnitArray.GetEngaged]"\n'
                      '\titem = {\n\t\tbd_regiment_damage = {}\n\t}\n}\n')
    return f'widget = {{\n\tsize = {{ 0 0 }}\n\tvisible = "[Not(Combat.IsNavalCombat)]"\n' + indent(lines, 1) + '}\n'




# The tail comes from the localisation (BD_TAIL): written in an on_start, a text with '#' or '@' is never found.
DAMAGE_TAIL = "Localize('BD_TAIL')"


# loc:         "BD_UNCOUNTED": "Other kills",
        "BD_UNCOUNTED": "Прочие убитые",


# loc:         "BD_UNCOUNTED_TT": "The enemy's killed men that the unit categories above don't account for: the days before our armies joined the battle (it is noted only while one of them is in it), the battle's last day (fought on the tick that ends the battle, after which no regiment holds it any more), and the killing in the pursuit.",
        "BD_UNCOUNTED_TT": "Убитые у противника, которых не покрывают рода войск выше: дни до прихода наших армий (бой записывается, только пока в нём есть наша армия), последний день боя (он идёт на тике, который закрывает бой, и после этого его нет ни у одного полка) и убитые при преследовании.",


# loc:         "BD_TARGETS_TITLE": "Whom it hit:",
        "BD_TARGETS_TITLE": "Кого били:",


# loc:         "BD_UNCLEAR": "unclear (two kinds of enemy at it that day)",
        "BD_UNCLEAR": "неясно (в тот день рядом враги двух родов войск)",


# loc:         "BD_TAIL": "#!@army_strength",
        "BD_TAIL": "#!@army_strength",


# loc:         "BD_DAMAGE_TT": "[strength|E] damage these units did in the battle: added up day by day from what the game counts for each regiment. The last day of the battle is not in it.",
        "BD_DAMAGE_TT": "Урон по [strength|e] противника, нанесённый этими войсками в бою: сложен по дням из того, что игра считает для каждого полка. Последнего дня боя в нём нет.",


# the sword line of a unit category in the card:
            + ((f'\t\thbox = {{\n\t\t\tlayoutpolicy_horizontal = expanding\n\t\t\tspacing = 2\n\t\t\talwaystransparent = no\n'
                f'\t\t\texpand = {{}}\n'
                f'\t\t\ticon = {{\n\t\t\t\tsize = {{ 11 11 }}\n\t\t\t\ttexture = "{ICON}abilities/mil_gold.dds"\n\t\t\t}}\n'
                f'\t\t\ttext_single = {{\n\t\t\t\tfontsize = 13\n\t\t\t\tdefault_format = "#color_yellow"\n'
                f'\t\t\t\ttext = "[Select_CString(StringIsEmpty({dealt}), \'0.00K\', {dealt})]"\n\t\t\t}}\n'
                + indent(target_tooltip(s, category), 3) + '\t\t}\n') if DAMAGE else '')


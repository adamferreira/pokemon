from numpy import floor
from typing import Dict, Union, Optional
import pandas as pd
from pypkm.data import PokeData

class BattleData():      
    def __init__(self, data:PokeData) -> None:
        self.data = data

    def apply_stats(self, base_stats:pd.DataFrame, nature:str = "Hardy", level:int = 100, IVs:Dict[str, int] = {}, EVs:Dict[str, int] = {}) -> pd.Series:
        """
        Given a DataFrame 'base_stats', apply the given level, nature and EVs/IVs the pokemon's stats.
        The dataframe 'base_stats' should be of the form of PokeData.base_stats.
        """
        
        # Stats are computed using the formula from generation 3 and onward
        # Source: https://bulbapedia.bulbagarden.net/wiki/Stat
        def _HP(base, ev, iv, level, nature_bonus) -> int:
            num = (2 * base + iv + floor(ev/4)) * level
            return floor(num/100) + level + 10

        def _STAT(base, ev, iv, level, nature_bonus) -> int:
            num = (2 * base + iv + floor(ev/4)) * level
            return floor((floor(num/100) + 5) * nature_bonus)
        
        stats = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
        # Base IVs and EVs are 0 be default
        base_EVs = {stat: 0 for stat in stats}
        base_IVs = {stat: 0 for stat in stats}
        # Update pokemon's IVs and EVs with what's given in parameter
        base_EVs.update(EVs)
        base_IVs.update(IVs)
        # Get nature bonuses from database
        nature_bonuses = self.data.natures[self.data.natures["Nature"] == nature].iloc[0]
        #
        df = base_stats
        # Update stats with given parameters
        for stat in stats:
            if stat == "HP":
                df = df.assign(HP = lambda x: _HP(x["HP"], base_EVs["HP"], base_IVs["HP"], level, nature_bonuses["HP"]))
            else:
                df = df.assign(**{stat: lambda x: _STAT(x[stat], base_EVs[stat], base_IVs[stat], level, nature_bonuses[stat])})

        df = df.assign(Total = lambda x: sum([x[stat] for stat in stats]))
        # Add Level as it could become usefull later for Damage calculation
        df = df.assign(Level = lambda x: level)
        return df



    def matchup(self, atk_pokemon:pd.Series, def_pokemon:pd.Series) -> pd.DataFrame:
        """
        The Series 'atk_pokemon' should be of the form of PokeData.base_stats.
        The Series 'def_pokemon' should be of the form of PokeData.base_stats.
        """
        # Moveset of the attacking pokemon
        atk_moveset = self.data.pretty_moveset(atk_pokemon["Name"])
        # Only keep damaging moves
        atk_moveset = atk_moveset[~atk_moveset["Power"].isna()]
        # Add Pokemon name to the moveset df to merge later on
        atk_moveset = atk_moveset.assign(Pokemon = lambda x: atk_pokemon["Name"])
        # Merge the two datasets to have atk_pokemon stats along with the moveset
        atk_moveset = pd.merge(atk_moveset, atk_pokemon.to_frame().transpose(), left_on="Pokemon", right_on="Name", how="outer")

        def damage(Level, A, D, Power, STAB, Type, Targets=1, PB=1, Weather=1, GlaiveRush=1, Critical=1, random=1, Burn=1, other=1, ZMove=1, TeraShield=1):
            """
            Source: https://bulbapedia.bulbagarden.net/wiki/Damage

            Formula:

            - `level` is the level of the attacking Pokémon.

            - `A` is the effective Attack stat of the attacking Pokémon if the used move is a physical move,
                or the effective Special Attack stat of the attacking Pokémonif the used move is a special move (ignoring negative stat stages for a critical hit).
            - `D` is the effective Defense stat of the target if the used move is a physical move or a special move that uses the target's Defense stat,
                or the effective Special Defense of the target if the used move is an other special move (ignoring positive stat stages for a critical hit).
            - `Power` is the effective power of the used move.
            - `Targets` is 0.75 (0.5 in Battle Royals) if the move has more than one target when the move is executed, and 1 otherwise.
            - `PB` is 0.25 (0.5 in Generation VI) if the move is the second strike of Parental Bond, and 1 otherwise.
            - `Weather` is 1.5 if a Water-type move is being used during rain or a Fire-type move during harsh sunlight, 
                and 0.5 if a Water-type move other than Hydro Steam is used during harsh sunlight or a Fire-type move during rain, 
                and 1 otherwise or if any Pokémon on the field have the Ability Cloud Nine or Air Lock.
            - `GlaiveRush` is 2 if the target used the move Glaive Rush in the previous turn, or 1 otherwise.
            - `Critical` is 1.5 (2 in Generation V) for a critical hit, and 1 otherwise. Decimals are rounded down to the nearest integer. 
                It is always 1 if the target's Ability is Battle Armor or Shell Armor or if the target is under the effect of Lucky Chant.
                - Conversely, unless critical hits are prevented entirely by one of the above effects, 
                    Critical will always be 1.5 (or 2 in Generation V) if the used move is 
                    Storm Throw, Frost Breath, Zippy Zap, Surging Strikes, Wicked Blow, or Flower Trick, the target is poisoned and the attacker's 
                    Ability is Merciless, or if the user is under the effect of Laser Focus.
            - `random` is a random factor. Namely, it is recognized as a multiplication from a random integer between 85 and 100, inclusive, then divided by 100. 
                Decimals are rounded down to the nearest integer.
                If the battle is taking place as a Pokéstar Studios film, random is always 1.
            - `STAB` is the same-type attack bonus. 
                This is equal to 1.5 if the move's type matches any of the user's types, 2 if the user of the move additionally has Adaptability, 
                and 1 otherwise or if the attacker and/or used move is typeless. If the used move is a combination Pledge move, 
                STAB is always 1.5 (or 2 if the user's Ability is Adaptability). When Terastalized, STAB is (if not 1):
                - 1.5 if the move's type matches either the Pokemon's original type(s) or a different Tera Type from its original types, 
                    and the attacker's Ability is not Adaptability.
                - 2 if the move's type matches the same Tera Type as one of the Pokemon's original types and the attacker's Ability is not 
                    Adaptability, or the situation above, if the attacker's Ability is Adaptability.
                - However, if STAB only applies from the attacker's original type(s), not its Tera Type, STAB will always be 1.5, even if the attacker's Ability is Adaptability.
                - 2.25 if the move's type matches the same Tera Type as one of the Pokemon's original types and the attacker's Ability is Adaptability.
            - `Type` is the type effectiveness. This can be 0.125, 0.25, 0.5 (not very effective); 1 
                (normally effective); 2, 4, or 8 (super effective), depending on both the move's and target's types. The 0.125 and 8 can 
                potentially be obtained on a Pokémon under the effect of Forest's Curse or Trick-or-Treat. If the used move is Struggle or typeless
                Revelation Dance, or the target is typeless, Type is always 1. 
                Decimals are rounded down to the nearest integer. Certain effects can modify this, namely:
                - If the target is an ungrounded Flying-type that is not being grounded by any other effect and is holding an Iron Ball or under the effect of Thousand Arrows, Type is equal to 1.
                - If the target is a grounded Flying-type (unless grounded by an Iron Ball or Thousand Arrows, as above), treat Ground's matchup against Flying as 1.
                - If the target is holding a Ring Target and the used move is of a type it would otherwise be immune to, treat that particular type matchup as 1.
                - If the attacker's Ability is Scrappy, treat Normal and Fighting's type matchups against Ghost as 1.
                - If the target is under the effect of Foresight, Odor Sleuth or Miracle Eye, and the target is of a type that would otherwise grant immunity to the used move, treat that particular type matchup as 1.
                - If the used move is Freeze-Dry, treat the move's type's matchup against Water as 2.
                - If the used move is Flying Press, consider both the move's type effectiveness and the Flying type's against the target, and multiply them together.
                - If strong winds are in effect and the used move would be super effective against Flying, treat the type matchup against Flying as 1 instead.
                - If the target is under the effect of Tar Shot and the used move is Fire-type, multiply Type by 2.
            - `Burn` is 0.5 if the attacker is burned, its Ability is not Guts, and the used move is a physical move (other than Facade from Generation VI onward), and 1 otherwise.
            - `other` is 1 in most cases, and a different multiplier when specific interactions of moves, Abilities, or items take effect, in this order (and if multiple moves, Abilities, or items take effect, they do so in the order of the out-of-battle Speed stats of the Pokémon with them):
                If multiple effects influence the other value, their values stack multiplicatively, in the order listed above. This is done by starting at 4096, multiplying it by each number above in the order listed above, and whenever there is a decimal, standard rounding it and rounding up at 0.5. When the final value is obtained, it is divided by 4096, and this becomes other.
            - `ZMove` is 0.25 if the move is a Z-Move, Max Move, or G-Max Move being used into a protection move (Protect, Detect, King's Shield, Spiky Shield, Mat Block, Baneful Bunker, or Obstruct, or potentially Wide Guard or W if the move has multiple targets or is given priority, respectively; if the move triggers the "couldn't fully protect" message, the multiplier will be applied), and 1 otherwise.
            - `TeraShield` is applied in Tera Raid Battles when the Raid boss's shield is active, and is 0.2 if the player's Pokémon is not Terastallized, 0.35 if it is but the used move is not of its Tera Type, and 0.75 if it is and the used move is of its Tera Type. The result is subject to standard rounding, rounding up at 0.5.
            """
            hum = (((2*Level)/5)+2) * Power * (A/D)
            return ((hum/50)+2)*Targets*PB*Weather*GlaiveRush*Critical*random*STAB*Type*Burn*other*ZMove*TeraShield

        print(atk_moveset)


def test():
    data = PokeData(gen = 9)
    battle = BattleData(data)
    # Source https://bulbapedia.bulbagarden.net/wiki/Stat
    """
    Consider a Level 78 Garchomp with the following IVs and EVs and an Adamant nature:
                HP	Attack	Defense	Sp.Atk	Sp.Def	Speed	Total
    Base stat	108	130	    95	    80	    85	    102	    600
    IV	        24	12	    30	    16	    23	    5	    110
    EV	        74	190	    91	    48	    84	    23	    510
    """
    garchomp = battle.apply_stats(
        battle.data.base_stats("Garchomp"),
        level = 78,
        nature = "Adamant",
        IVs = {"HP": 24, "Attack": 12, "Defense": 30, "Sp. Atk": 16, "Sp. Def": 23, "Speed": 5},
        EVs = {"HP": 74, "Attack": 190, "Defense": 91, "Sp. Atk": 48, "Sp. Def": 84, "Speed": 23}
    ).iloc[0]

    """
    In the end, this Garchomp's stats are as follows:
                HP	Attack	Defense	Sp.Atk	Sp.Def	Speed
    Base stat	108	130	    95	    80	    85	    102
    IV	        24	12	    30	    16	    23	    5
    EV	        74	190	    91	    48	    84	    23
    Total	    289	278	    193	    135	    171	    171
    """
    assert garchomp["HP"] == 289
    assert garchomp["Attack"] == 278
    assert garchomp["Defense"] == 193
    assert garchomp["Sp. Atk"] == 135
    assert garchomp["Sp. Def"] == 171
    assert garchomp["Speed"] == 171

if __name__ == "__main__":
    test()

    data = PokeData(gen = 9)
    battle = BattleData(data)
    garchomp = battle.apply_stats(
        battle.data.base_stats("Garchomp"),
        level = 78,
        nature = "Adamant",
        IVs = {"HP": 24, "Attack": 12, "Defense": 30, "Sp. Atk": 16, "Sp. Def": 23, "Speed": 5},
        EVs = {"HP": 74, "Attack": 190, "Defense": 91, "Sp. Atk": 48, "Sp. Def": 84, "Speed": 23}
    ).iloc[0]

    tinkaton = battle.apply_stats(
        battle.data.base_stats("Tinkaton"),
        level = 80,
        nature = "Naughty",
        IVs = {"HP": 24, "Attack": 12, "Defense": 30, "Sp. Atk": 16, "Sp. Def": 23, "Speed": 5},
        EVs = {"HP": 74, "Attack": 190, "Defense": 91, "Sp. Atk": 48, "Sp. Def": 84, "Speed": 23}
    ).iloc[0]
    battle.matchup(garchomp, tinkaton)
import pandas as pd
import itertools
from typing import Union, List
from pypkm.data import(
    stats_file,
    moves_file,
    movesets_file,
    items_file,
    key_items_file,
    abilities_file,
    types_matrix_file
)

class PokeData():
    def __init__(self, gen:str) -> None:
        self.gen = gen
        # Load pokemon data
        self.pokemons: pd.DataFrame = pd.read_csv(stats_file(gen="all"), sep=";")
        self.moves: pd.DataFrame = pd.read_csv(moves_file(gen="all"), sep=";")
        self.movesets: pd.DataFrame = pd.read_csv(movesets_file(gen=self.gen), sep=";")
        self.abilities: pd.DateOffset = pd.read_csv(abilities_file(), sep=";")
        self.types_matix: pd.DataFrame = pd.read_csv(types_matrix_file(), sep = ";")#.set_index("Attack Type")

    def __c_as_type(self, t:str):
        return (self.pokemons["Type1"] == t) | (self.pokemons["Type2"] == t)
    
    def __c_as_types(self, t1:str, t2:str):
        return self.__c_as_type(t1) & self.__c_as_type(t2)
    
    def as_type(self, t:str) -> pd.DataFrame:
        """
        Return the pokemon stats dataframe restrited to pokemons that have at leat `t` as their type
        """
        return self.pokemons[self.__c_as_type(t)]
    
    def as_types(self, t1:str, t2:str) -> pd.DataFrame:
        """
        Return the pokemon stats dataframe restrited to pokemons that have `t1` and `t2` as their type
        (Any order)
        """
        return self.pokemons[self.__c_as_types(t1,t2)]
    
    def __c_pokemon(self, pokemon:Union[int,str]):
        if isinstance(pokemon, int):
            return self.pokemons["PokedexId"] == pokemon
        if isinstance(pokemon, str):
            return self.pokemons["Name"] == pokemon
        
    def moveset(self, pokemon:Union[int,str]) -> pd.DataFrame:
        """
        Return the moveset information of `pokemon`
        The moveset is the move name and how the pokemon can learn it
        """
        pkmane = self.pokemons[self.__c_pokemon(pokemon)].iloc[0]["Name"]
        return self.movesets[self.movesets["Pokemon"] == pkmane]
    
    def detailed_moveset(self, pokemon:Union[int,str]) -> pd.DataFrame:
        """
        Return the detailled moveset information of `pokemon`
        The detailled moveset is the complete moveset information with battle information for each moves (PP, Power, Prob, Type, etc)
        """
        moveset = self.moveset(pokemon)
        return pd.merge(
            moveset,
            self.moves,
            how = "left",
            left_on = "Move",
            right_on = "Name"
        ).rename({"Name": "Move"})
    
    def pretty_moveset(self, pokemon:Union[int,str]) -> pd.DataFrame:
        """
        Return the pretty moveset information of `pokemon`
        The pretty moveset is the detailled moveset with only columns "Move", "Type", "Category", "Power", "Accuracy", "PP", "Prob. (%)"
        And "Move" as index
        """
        return self.detailed_moveset(pokemon)[
            ["Move", "Type", "Category", "Power", "Accuracy", "PP", "Prob. (%)"]
        ].set_index("Move")


    def defensive_matrix(self) -> pd.DataFrame:
        types = self.types_matix["Attack Type"].to_list()
        for (t1, t2) in itertools.product(types, types):
            typestr = f"{t1} {t2}" if t1 != t2 else t1
            defense_vector = (self.types_matix[t1] * self.types_matix[t2]).to_list() if t1 != t2 else self.types_matix[t1].to_list()
            print(typestr, defense_vector)
        return types

if __name__ == "__main__":
    data = PokeData(gen = 9)
    #print(data.pretty_moveset("Miraidon"))
    #print(data.types_matix[["Fairy", "Water"]])
    #print((data.types_matix["Fairy"] * data.types_matix["Water"]).to_list())
    print(data.defensive_matrix())
import pandas as pd
import itertools
from typing import Union, Optional, List, Tuple
from pypkm.data import(
    stats_file,
    moves_file,
    movesets_file,
    items_file,
    key_items_file,
    abilities_file,
    types_matrix_file,
    natures_file
)

class PokeData():
    def __init__(self, gen:str) -> None:
        self.gen = gen
        # Load pokemon data
        self.pokemons: pd.DataFrame = pd.read_csv(stats_file(gen="all"), sep=";")
        self.moves: pd.DataFrame = pd.read_csv(moves_file(gen="all"), sep=";")
        self.movesets: pd.DataFrame = pd.read_csv(movesets_file(gen=self.gen), sep=";")
        self.abilities: pd.DateOffset = pd.read_csv(abilities_file(), sep=";")
        self.types_matix: pd.DataFrame = pd.read_csv(types_matrix_file(), sep = ";")
        self.natures: pd.DataFrame = pd.read_csv(natures_file(), sep = ";")

    def _c_of_type(self, t:str):
        return (self.pokemons["Type1"] == t) | (self.pokemons["Type2"] == t)
    
    def _c_of_types(self, t1:str, t2:Optional[str] = None):
        if t2 is None:
            return self._c_of_type(t1)
        return self._c_of_type(t1) & self._c_of_type(t2)
    
    @staticmethod
    def type_to_key(t1:str, t2:Optional[str] = None) -> Union[str, Tuple[str, str]]:
        """
        Given two type, get the dual-type key as a sorted tuple
        This is to avoid duplicates dual-types keys such as (Fire, Normal) and (Normal, Fire)
        Also, single types are returned as (t1, None):
        (Fire, Fire) -> (Fire, None)
        """
        if t1 == t2:
            return t1
        else:
            return f"{sorted((t1,t2))[0]} {sorted((t1,t2))[1]}"
        
    @staticmethod
    def key_to_type(key:str) -> Tuple[str, Optional[str]]:
        types = key.split(" ")
        if len(types) == 1:
            return (types[0], None)
        
        return (types[0], types[1])
    
    def of_types(self, t1:str, t2:Optional[str] = None) -> pd.DataFrame:
        """
        Return the pokemon stats dataframe restrited to pokemons that have `t1` and `t2` as their type
        If t2 is None, pokemon with types `t1` as first or second type
        (Any order)
        """
        return self.pokemons[self._c_of_types(t1,t2)]
    
    def __c_pokemon(self, pokemon:Union[int,str]):
        if isinstance(pokemon, int):
            return self.pokemons["PokedexId"] == pokemon
        if isinstance(pokemon, str):
            return self.pokemons["Name"] == pokemon
        
    def base_stats(self, pokemon:Union[int,str]) -> pd.DataFrame:
        return self.pokemons[self.__c_pokemon(pokemon)]
        
    def moveset(self, pokemon:Union[int,str]) -> pd.DataFrame:
        """
        Return the moveset information of `pokemon`
        The moveset is the move name and how the pokemon can learn it
        """
        pkmane = self.base_stats(pokemon).iloc[0]["Name"]
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
        ]#.set_index("Move")


    def defensive_matrix(self) -> pd.DataFrame:
        """
        For each type and double-types compination,
        Return the defensive matrix with the damage factor for each attack type.
        Example of a row of the defensive matrix for the defense type Ground-Dragon (Garchomp)

        Type Defense      Normal  Fire  Water  Electric  Grass  Ice  Fighting  ...  Bug  Rock  Ghost  Dragon  Dark  Steel  Fairy
        (Dragon, Ground)     1.0   0.5    1.0       0.0    1.0  4.0       1.0  ...  1.0   0.5    1.0     2.0   1.0    1.0    2.0
        """
        types = self.types_matix["Attack Type"].to_list()
        defensive_matrix = {}
        for (t1, t2) in itertools.product(types, types):
            # Monotypes
            if t1 == t2:
                defense_vector = self.types_matix[t1].to_list()
            # Dual types
            else:
                defense_vector = (self.types_matix[t1] * self.types_matix[t2]).to_list()
            
            defensive_matrix[PokeData.type_to_key(t1, t2)] = defense_vector
            
        #defensive_matrix["Type Defense"] = types
        df = pd.DataFrame(defensive_matrix)
        df = df.transpose()
        df = df.rename(columns={i : types[i] for i in range(len(types))})
        #df = df.set_index("Type Defense")
        #df = df.reset_index().rename(columns={"level_0": "Type Defense"})
        return df#.transpose()#.rename_axis(["Type Defense"]).reset_index()
    
    def best_defense_types(self) -> pd.DataFrame:
        return self.defensive_matrix().transpose().sum().sort_values(ascending=True)
    

    def __defensive_comparison(self, sense:str, types:List[str]) -> pd.DataFrame:
        if len(types) == 0:
            return pd.Dataframe()
        m = self.defensive_matrix()
        if sense == ">":
            joined = m[m[types[0]] > 1.0]
        if sense == "<":
            joined = m[m[types[0]] < 1.0]

        if len(types) == 1:
            return joined
        
        # Inner join by type weaknesses to ha ve a big logic AND
        for i in range(1, len(types)):
            if sense == ">":
                joined = joined[joined[types[i]] > 1.0]
            if sense == "<":
                joined = joined[joined[types[i]] < 1.0]

        return joined

    def weak_against(self, types:List[str]) -> pd.DataFrame:
        """
        List of defensive types combination that are weak againts all types (if they were attacks) given in parameters.
        i.e. All defensive types combination with a coeficient > 1.0 for the given types in the defensive matrix.
        Meaning the given types would be 'super effective' againts the defensive types combination.
        """
        # Comparison sign is inverted as we are using a defensive matrix
        return self.__defensive_comparison(">", types)

    def resist_against(self, types:List[str]) -> pd.DataFrame:
        """
        List of defensive types combination that resists all types (if they were attacks) given in parameters.
        i.e. All defensive types combination with a coeficient < 1.0 for the given types in the defensive matrix.
        Meaning the given types would be 'not very effective' againts the defensive types combination.
        """
        # Comparison sign is inverted as we are using a defensive matrix
        return self.__defensive_comparison("<", types)
    
    def best_against(self, types:List[str]) -> pd.Series:
        """
        Sorted list of best best defensive counter for the types given in parameter
        This is the sum of the defensive score of each types in parameters, for each defending types
        """
        return self.resist_against(types)[types].transpose().sum().sort_values(ascending=True)
    


if __name__ == "__main__":
    data = PokeData(gen = 9)
    #print(data.pretty_moveset("Miraidon"))
    #print(data.types_matix[["Fairy", "Water"]])
    #print((data.types_matix["Fairy"] * data.types_matix["Water"]).to_list())
    #print(data.defensive_matrix())
    #print(data.best_defense_types())
    #print(data.strong_against(["Fire"]))
    #print(data.strong_against(["Fire", "Fighting"]))
    #print(data.best_against(["Fire", "Fighting"]))
    #print("------------------------")
    #print(data.best_against(["Fire", "Normal"]))
    #print("------------------------")
    #print(data.of_types("Ghost", "Fire"))
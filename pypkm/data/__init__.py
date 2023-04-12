from .scrapping.pokemondatabase import (
    STATS_DIR,
    MOVES_DIR,
    ITEMS_DIR,
    ABILITIES_DIR,
    stats_file,
    moves_file,
    movesets_file,
    items_file,
    key_items_file,
    abilities_file,
    types_matrix_file
)

from .pokemon_data import PokeData

def of_types(df, t1, t2):
    return df[
        (df["Type1"] == t1) & (df["Type2"] == t2)
        |
        (df["Type1"] == t2) & (df["Type2"] == t1)
    ]
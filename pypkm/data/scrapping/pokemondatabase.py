import os
import pandas as pd
import scrapy
import itertools
from scrapy.crawler import CrawlerRunner
# Reactor restart
from crochet import setup, wait_for
from pypkm.data.scrapping.utils import HTMLTable
import traceback

# Get directory of this file
DATA_DIR = os.path.dirname(os.path.realpath(__file__))

# Constants
CSV_SEP = ';'
SUPPORTED_GENS = list(range(1, 9+1))

# Setup Crochet
setup()

# Setup data folder structure
STATS_DIR = os.path.join(DATA_DIR, "stats")
MOVES_DIR = os.path.join(DATA_DIR, "moves")
ITEMS_DIR = os.path.join(DATA_DIR, "items")
ABILITIES_DIR = os.path.join(DATA_DIR, "abilities")

for d in [STATS_DIR, MOVES_DIR, ITEMS_DIR, ABILITIES_DIR]:
    if not os.path.isdir(d):
        os.mkdir(d)

# Util function (to be imported)
def stats_file(gen: int) -> str:
    """
    Pokemon Name, Id and statistics
    """
    return os.path.join(STATS_DIR, f"stats_gen_{gen}.csv")

def moves_file(gen: int) -> str:
    """
    List of moves available in each game generation
    """
    return os.path.join(MOVES_DIR, f"moves_gen_{gen}.csv")

def movesets_file(gen: int) -> str:
    """
    List of moves available in each game generation
    """
    return os.path.join(MOVES_DIR, f"movesets_gen_{gen}.csv")

def items_file() -> str:
    """
    List of items for all game generations
    """
    return os.path.join(ITEMS_DIR, f"items.csv")

def key_items_file() -> str:
    """
    List of items for all game generations
    """
    return os.path.join(ITEMS_DIR, f"items.csv")

def abilities_file() -> str:
    """
    List of items for all game generations
    """
    return os.path.join(ABILITIES_DIR, f"abilities.csv")

def types_matrix_file() -> str:
    """
    List of items for all game generations
    """
    return os.path.join(STATS_DIR, f"types_matrix_gen6plus.csv")


def try_parse(x, xtype, default):
    try:
        return xtype(x)
    except Exception as e:
        return default

class TableToCsv(scrapy.Spider):
    """
    A class that have an internal DataFrame and saves it as CSV on closing
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.df = pd.DataFrame()

    # Called at end
    def closed(self, reason):
        # Save the dataframe as a csv file
        self.df.to_csv(f"{self.root}", sep=';')

    @staticmethod
    def as_dataframe(table: HTMLTable):
        df = pd.DataFrame()
        for d in table.as_dicts():
            try:
                # Append global dataframe with the modified row
                df = pd.concat([df, pd.DataFrame([d])], ignore_index=True)
            except Exception as e:
                print(e)
                return
        return df

class PokemonStats(TableToCsv):
    """
    Parse Complete Pokémon Pokédex from pokemondb.net
    And stores it in a CSV
    """
    name = "PokemonStats"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gen = kwargs["gen"]
        if self.gen == "all":
            self.start_urls = ["https://pokemondb.net/pokedex/all"]
        else:
            self.start_urls = [f"https://pokemondb.net/pokedex/stats/gen{self.gen}"]

        self.root = stats_file(self.gen)

    @staticmethod
    def as_dataframe(table: HTMLTable):
        df = pd.DataFrame()
        for d in table.as_dicts():
            try:
                # Split 'Type' column into subtypes
                types = d["Type"].split(" ")
                if len(types) == 1:
                    d["Type1"] = types[0]
                    d["Type2"] = None
                else:
                    d["Type1"] = types[0]
                    d["Type2"] = types[1]
                del d["Type"]

                # Clean "#" col
                d["PokedexId"] = d["#"]
                del d["#"]

                # Append global dataframe with the modified row
                df = pd.concat([df, pd.DataFrame([d])], ignore_index=True)
            except Exception as e:
                print(e)
                return
        return df

    # Called for each urls in self.start_urls
    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return
            print(f"Scrapping pokemon stats for generation {self.gen}")
            # Get the html table from "https://pokemondb.net/pokedex/all" with id "pokedex"
            pokedex_table = HTMLTable(response.xpath('//*[@id="pokedex"]'))
            # Transform the html table into a cleaned dataframe
            pokedex_df = PokemonStats.as_dataframe(pokedex_table)
            # Concat global df
            self.df = pd.concat([self.df, pokedex_df], ignore_index=True)
            # Set index to avoid saving a column full of row numbers
            self.df = self.df.set_index("Name")
        except Exception as e:
            print(f"Failed scrapping pokemon stats for generation {self.gen}", e)
            return



class Moves(TableToCsv):
    """
    Parse Pokémon move list from pokemondb.net
    And stores it in a CSV
    """
    name = "Moves"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gen = kwargs["gen"]
        gen = "all" if self.gen == "all" else f"generation/{self.gen}"
        self.start_urls = [f"https://pokemondb.net/move/{gen}"]
        self.root = moves_file(self.gen)

    @staticmethod
    def as_dataframe(table: HTMLTable):
        df = pd.DataFrame()
        for d in table.as_dicts():
            try:
                # Clean int columns where values are '-' or 'infinite' in th file
                d["Power"] = try_parse(d["Power"], int, None)
                d["PP"] = try_parse(d["PP"], int, None)
                if d["Acc."] == "∞":
                    d["Acc."] = float("inf")
                else:
                    d["Acc."] = try_parse(d["Acc."], int, None)
                if "Prob. (%)" in d:
                    d["Prob. (%)"] = try_parse(d["Prob. (%)"], int, None)

                # Append global dataframe with the modified row
                df = pd.concat([df, pd.DataFrame([d])], ignore_index=True)
            except Exception as e:
                print(e)
                return
        return df

    # Called for each urls in self.start_urls
    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return
            print(f"Scrapping moves for generation {self.gen}")
            # Parse 'moves' html table
            table = HTMLTable(response.xpath('//*[@id="moves"]'))
            # Convert it to a dataframe with appropriate move catagory column
            df = Moves.as_dataframe(table)
            # Rename some cols for conveniency
            df = df.rename(columns={"Cat.": "Category", "Acc." : "Accuracy"})
            # Concat global df
            self.df = pd.concat([self.df, df], ignore_index=True)
            # Set index to avoid saving a column full of row numbers
            self.df = self.df.set_index("Name")
        except Exception as e:
            print(f"Failed scrapping moves for generation {self.gen}", e)
            return


class MoveSets(TableToCsv):
    name = "MoveSets"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gen = kwargs["gen"]

        # retrieve all pokemon names (from stats file)
        pokemons = pd.read_csv(stats_file(gen = "all"), sep=";")["Name"].to_list()
        self.url_dict = {
            f"https://pokemondb.net/pokedex/{pokemon.lower().replace(' ', '-')}/moves/{self.gen}" : pokemon
            for pokemon in pokemons
        }
        self.start_urls = list(self.url_dict.keys())
        self.root = movesets_file(self.gen)

    # Called for each urls in self.start_urls
    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return

            # Get Pokemon name from url
            pokemon = self.url_dict[response.url]
            # Get Gen number from the urls
            gen = response.url.split("/")[-1:][0]
            print(f"Scrapping movesets for {pokemon} for generation {gen}, {response.url}")

            # Find all data table in the page
            title_tables = {}
            for table in response.xpath('.//*[@class="data-table"]'):
                # For each table that we found in the page, we are looking for its title
                # We have the following hierarchy:
                # <div class="grid-col span-lg-6">
                #   <h3>Moves learnt by level up</h3> 
                # <p class="text-small"><em>Butterfree</em> learns the following moves in Pokémon Red &amp; Blue at the levels specified.</p> 
                # <div class="resp-scroll">
                #   <table class="data-table"> ...

                # We could also have
                # <div class="grid-col span-lg-6">
                #   <h3>Moves learnt by HM</h3> 
                #   <p><em>Butterfree</em> does not learn any HMs in Pokémon Red &amp; Blue.</p> 
                # <h3>Moves learnt by TM</h3> 
                # <p class="text-small"><em>Butterfree</em> is compatible with these Technical Machines in Pokémon Red &amp; Blue:</p> 
                # <div class="resp-scroll">
                #   <table class="data-table">

                # So the are looking to the closest h3 selector up to this table
                # Wich is the first preceding-sibling of the table's parent for the bottom-up
                titles = table.xpath('..').xpath("preceding-sibling::h3/text()")
                # So the last title of the list
                title = titles[-1:].get()
                if title not in title_tables:
                    title_tables[title] = table
                # All title visited, we break to avoid treating doublons of tables
                else:
                    break

            # TODO: Add Moves learnt on evolution ? and by TR : Moves learnt by TR ? (https://pokemondb.net/pokedex/sharpedo/moves/8)

            # Move learned by leveling up
            if "Moves learnt by level up" in title_tables:
                by_level = TableToCsv.as_dataframe(HTMLTable(title_tables["Moves learnt by level up"]))[["Move", "Lv."]]
            else:
                by_level = pd.DataFrame(columns=["Move", "Lv."])
            # Move learned from pre-evolutions of the pokemon
            if "Pre-evolution moves" in title_tables:
                by_preevol = TableToCsv.as_dataframe(HTMLTable(title_tables["Pre-evolution moves"]))
                # Set 'PreEvol' col as true if pre-evol moves were found
                by_preevol.insert(len(by_preevol.columns), "PreEvol", [True for i in range(len(by_preevol))])
                by_preevol = by_preevol[["Move", "PreEvol"]]
            else:
                by_preevol = pd.DataFrame(columns=["Move", "PreEvol"])
            # Move learned by HM
            if "Moves learnt by HM" in title_tables:
                by_hm = TableToCsv.as_dataframe(HTMLTable(title_tables["Moves learnt by HM"]))[["Move", "HM"]]
            else:
                by_hm = pd.DataFrame(columns=["Move", "HM"])
            # Move learned by HM
            if "Moves learnt by TM" in title_tables:
                by_tm = TableToCsv.as_dataframe(HTMLTable(title_tables["Moves learnt by TM"]))[["Move", "TM"]]
            else:
                by_tm = pd.DataFrame(columns=["Move", "TM"])
            # Move learned from reproduction
            if "Egg moves" in title_tables:
                by_egg = TableToCsv.as_dataframe(HTMLTable(title_tables["Egg moves"]))
                # Set 'Egg' col as true if egg moves were found
                by_egg.insert(len(by_egg.columns), "Egg", [True for i in range(len(by_egg))])
                by_egg = by_egg[["Move", "Egg"]]
            else:
                by_egg = pd.DataFrame(columns=["Move", "Egg"])
            # Move learned by the tutor
            if "Move Tutor moves" in title_tables:
                by_tutor = TableToCsv.as_dataframe(HTMLTable(title_tables["Move Tutor moves"]))
                # Set 'Tutor' col as true if tutor moves were found
                by_tutor.insert(len(by_tutor.columns), "Tutor", [True for i in range(len(by_tutor))])
                by_tutor = by_tutor[["Move", "Tutor"]]
            else:
                by_tutor = pd.DataFrame(columns=["Move", "Tutor"])
            # Technical Records in Pokémon Sword & Shield
            if "Moves learnt by TR" in title_tables:
                by_tr = TableToCsv.as_dataframe(HTMLTable(title_tables["Moves learnt by TR"]))[["Move", "TR"]]
            else:
                by_tr = pd.DataFrame(columns=["Move", "TR"])
            # Transfer-only moves
            # TODO: Moves learnt after transfer It must be taught the moves in the appropriate game and then transferred to


            # Merge all dataframes to have all columns
            joined = by_level
            joined = pd.merge(joined, by_preevol, on="Move", how="outer")
            joined = pd.merge(joined, by_hm, on="Move", how="outer")
            joined = pd.merge(joined, by_tm, on="Move", how="outer")
            joined = pd.merge(joined, by_egg, on="Move", how="outer")
            joined = pd.merge(joined, by_tutor, on="Move", how="outer")
            joined = pd.merge(joined, by_tr, on="Move", how="outer")

            # Add current pokemon name as a column
            joined["Name"] = [pokemon for i in range(len(joined))]
            # For cols 'Egg', 'PreEvol' and 'Tutor', replace NaN (missing info) by false
            joined["Egg"] = joined["Egg"].fillna(False)
            joined["PreEvol"] = joined["PreEvol"].fillna(False)
            joined["Tutor"] = joined["Tutor"].fillna(False)
            # Rename some cols for conveniency
            joined = joined.rename(columns={"Name": "Pokemon", "Lv." : "Lvl"})
            # Concat global df
            self.df = pd.concat([self.df, joined], ignore_index=True)

        except Exception as e:
            print(f"Failed scrapping movesets for {pokemon} for generation {gen}", e)
            pass

class Items(TableToCsv):
    name = "Items"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ["https://pokemondb.net/item/all"]
        self.root = items_file()

    # Called for each urls in self.start_urls
    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return
            print(f"Scrapping items")
            # Parse 'moves' html table
            table = HTMLTable(response.xpath('//*[@class="data-table block-wide"]'))
            # Convert it to a dataframe with appropriate move catagory column
            df = TableToCsv.as_dataframe(table)
            # Concat global df
            self.df = pd.concat([self.df, df], ignore_index=True)
            # Set index to avoid saving a column full of row numbers
            self.df = self.df.set_index("Name")
        except Exception as e:
            print(f"Failed scrapping items", e, traceback.print_exc())
            return

class KeyItems(Items):
    name = "Items"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ["https://pokemondb.net/item/type/key"]
        self.root = key_items_file()


# Class used to retrieve Abilities names !
class TMPAbilities(TableToCsv):
    name = "TMPAbilities"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ["https://pokemondb.net/ability"]
        self.root = abilities_file()

    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return
            print(f"Scrapping abilities")
            # Parse 'abilities' html table
            table = HTMLTable(response.xpath('//*[@id="abilities"]'))
            # Convert it to a dataframe with appropriate move catagory column
            df = TableToCsv.as_dataframe(table)[["Name", "Gen."]]
            # Rename some cols for conveniency
            df = df.rename(columns={"Name": "Ability", "Gen.": "Gen"})
            # Concat global df
            self.df = pd.concat([self.df, df], ignore_index=True)
            # Set index to avoid saving a column full of row numbers
            self.df = self.df.set_index("Ability")
        except Exception as e:
            print(f"Failed scrapping abilities", e)
            return

class Abilities(TableToCsv):
    name = "Abilities"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get abilities names and gen from TMPAbilities file
        self.abilities = pd.read_csv(abilities_file(), sep=";")
        # Delete ability file as the will override it
        os.unlink(abilities_file())
        self.root = abilities_file()  

        # Get ulr for each ability dedails
        self.url_dict = {
            f"https://pokemondb.net/ability/{ability.lower().replace(' ', '-')}" : ability
            for ability in self.abilities["Ability"].to_list()
        }
        self.start_urls = list(self.url_dict.keys())

    @staticmethod
    def as_dataframe(table: HTMLTable, ability):
        df = pd.DataFrame()
        for d in table.as_dicts():
            try:

                # Clean cols who have '\n` inside for some reason
                for c in d:
                    d[c] = d[c].replace('\n', '')
                
                # Clean 2nd ability col
                if "2nd ability" in d:
                    d["Second ability"] = d["2nd ability"]
                    del d["2nd ability"]

                # Clean int columns where values are '-' or 'infinite' in th file
                d["Second ability"] = None if d["Second ability"] == "—" else d["Second ability"]
                d["Hidden ability"] = None if d["Hidden ability"] == "—" else d["Hidden ability"]

                # Add ability Columns
                d["Ability"] = ability

                # Append global dataframe with the modified row
                df = pd.concat([df, pd.DataFrame([d])], ignore_index=True)
            except Exception as e:
                print(e)
                return
        return df

    def parse(self, response):
        try:
            if response.status != 200:
                print(f"Cannot contact url {response.url}")
                return
            # Get ability name from url
            ability = self.url_dict[response.url]
            print(f"Scrapping ability {ability}, {response.url}")

            # Find all data table in the page
            title_tables = {}
            for table in response.xpath('.//*[@class="data-table"]'):
                titles = table.xpath('..').xpath("preceding-sibling::h2/text()")
                # So the last title of the list
                title = titles[-1:].get()
                if title not in title_tables:
                    title_tables[title] = table
                # All title visited, we break to avoid treating doublons of tables
                else:
                    break
            
            if f"Pokémon with {ability}" in title_tables:
                # Get data from the table after 'Pokémon with <Ability Name>'
                # Some page do not have this title nor table (ex: https://pokemondb.net/ability/zen-mode)
                df = Abilities.as_dataframe(HTMLTable(title_tables[f"Pokémon with {ability}"]), ability)
                # Rename some cols for conveniency
                df = df.rename(columns={"Name": "Pokemon", "#" : "PokedexId"})
                # Concat global df
                self.df = pd.concat([self.df, df], ignore_index=True)
        except Exception as e:
            print(f"Failed scrapping ability {ability}", e)
            return
        

class Types(TableToCsv):
    name = "Types"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ["https://pokemondb.net/ability"]
        self.root = types_matrix_file()
        self.df = pd.DataFrame({
            "Attack Type": ["Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"],
            "Normal":   [1.0,1.0,1.0,1.0,1.0,1.0,2.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,1.0,1.0,1.0],
            "Fire":     [1.0,0.5,2.0,1.0,0.5,0.5,1.0,1.0,2.0,1.0,1.0,0.5,2.0,1.0,1.0,1.0,0.5,0.5],
            "Water":    [1.0,0.5,0.5,2.0,2.0,0.5,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.5,1.0],
            "Electric": [1.0,1.0,1.0,0.5,1.0,1.0,1.0,1.0,2.0,0.5,1.0,1.0,1.0,1.0,1.0,1.0,0.5,1.0],
            "Grass":    [1.0,2.0,0.5,0.5,0.5,2.0,1.0,2.0,0.5,2.0,1.0,2.0,1.0,1.0,1.0,1.0,1.0,1.0],
            "Ice":      [1.0,2.0,1.0,1.0,1.0,0.5,2.0,1.0,1.0,1.0,1.0,1.0,2.0,1.0,1.0,1.0,2.0,1.0],
            "Fighting": [1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,2.0,2.0,0.5,0.5,1.0,1.0,0.5,1.0,2.0],
            "Poison":   [1.0,1.0,1.0,1.0,0.5,1.0,0.5,0.5,2.0,1.0,2.0,0.5,1.0,1.0,1.0,1.0,1.0,0.5],
            "Ground":   [1.0,1.0,2.0,0.0,2.0,2.0,1.0,0.5,1.0,1.0,1.0,1.0,0.5,1.0,1.0,1.0,1.0,1.0],
            "Flying":   [1.0,1.0,1.0,2.0,0.5,2.0,0.5,1.0,0.0,1.0,1.0,0.5,2.0,1.0,1.0,1.0,1.0,1.0],
            "Psychic":  [1.0,1.0,1.0,1.0,1.0,1.0,0.5,1.0,1.0,1.0,0.5,2.0,1.0,2.0,1.0,2.0,1.0,1.0],
            "Bug":      [1.0,2.0,1.0,1.0,0.5,1.0,0.5,1.0,0.5,2.0,1.0,1.0,2.0,1.0,1.0,1.0,1.0,1.0],
            "Rock":     [0.5,0.5,2.0,1.0,2.0,1.0,2.0,0.5,2.0,0.5,1.0,1.0,1.0,1.0,1.0,1.0,2.0,1.0],
            "Ghost":    [0.0,1.0,1.0,1.0,1.0,1.0,0.0,0.5,1.0,1.0,1.0,0.5,1.0,2.0,1.0,2.0,1.0,1.0],
            "Dragon":   [1.0,0.5,0.5,0.5,0.5,2.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,2.0,1.0,1.0,2.0],
            "Dark":     [1.0,1.0,1.0,1.0,1.0,1.0,2.0,1.0,1.0,1.0,0.0,2.0,1.0,0.5,1.0,0.5,1.0,2.0],
            "Steel":    [0.5,2.0,1.0,1.0,0.5,0.5,2.0,0.0,2.0,0.5,0.5,0.5,0.5,1.0,0.5,1.0,0.5,0.5],
            "Fairy":    [1.0,1.0,1.0,1.0,1.0,1.0,0.5,2.0,1.0,1.0,1.0,0.5,1.0,1.0,0.0,0.5,2.0,1.0]
        }).set_index("Attack Type")

        [1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0],

@wait_for(3600)
def run_spider1():
    crawler = CrawlerRunner()
    """
    for i in ["all"] + SUPPORTED_GENS:
        d = crawler.crawl(Moves, gen = i)
        d = crawler.crawl(PokemonStats, gen = i)
    
    #d = crawler.crawl(Items)
    #d = crawler.crawl(KeyItems)
    d = crawler.crawl(TMPAbilities)
    """
    d = crawler.crawl(Types)
    return d

@wait_for(3600)
def run_spider2():
    # Run in separate function as we need stats_gen_all.csv for all pokemon names
    crawler = CrawlerRunner()
    for i in SUPPORTED_GENS:
        d = crawler.crawl(MoveSets, gen = i)

    d = crawler.crawl(Abilities)
    return d

if __name__ == "__main__":
    import time
    run_spider1()
    #time.sleep(30)
    # Will run after spider 1 as
    # MoveSets needs PokemonStats to have written its file
    # Abilities needs Abilities.TMPAbilities to have written its file
    #run_spider2()
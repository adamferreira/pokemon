import os
import pandas as pd
import scrapy
from scrapy.crawler import CrawlerRunner
# Reactor restart
from crochet import setup, wait_for
from utils import HTMLTable

# Get directory of this file
DATA_DIR = os.path.dirname(os.path.realpath(__file__))

# Constants
CSV_SEP = ';'

# Setup Crochet
setup()

# Setup data folder structure
STATS_DIR = os.path.join(DATA_DIR, "pokemon_stats")
MOVES_DIR = os.path.join(DATA_DIR, "moves")
ITEMS_DIR = os.path.join(DATA_DIR, "items")

for d in [STATS_DIR, MOVES_DIR, ITEMS_DIR]:
    if not os.path.isdir(d):
        os.mkdir(d)


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
        self.df.to_csv(f"{self.root}.csv", sep=';')

class CompletePokedexWithStats(TableToCsv):
    """
    Parse Complete Pokémon Pokédex from pokemondb.net
    And stores it in a CSV
    """
    name = "CompletePokedexWithStats"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ["https://pokemondb.net/pokedex/all"]
        self.root = os.path.join(STATS_DIR, "all")

    # Called for each urls in self.start_urls
    def parse(self, response):
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

        # Get the html table from "https://pokemondb.net/pokedex/all" with id "pokedex"
        pokedex_table = HTMLTable(response.xpath('//*[@id="pokedex"]'))
        # Transform the html table into a cleaned dataframe
        pokedex_df = as_dataframe(pokedex_table)
        # Concat global df
        self.df = pd.concat([self.df, pokedex_df], ignore_index=True)


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
        self.root = os.path.join(MOVES_DIR, f"gen_{self.gen}")

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
        # Parse 'moves' html table
        table = HTMLTable(response.xpath('//*[@id="moves"]'))
        # Convert it to a dataframe with appropriate move catagory column
        df = Moves.as_dataframe(table)
        # Concat global df
        self.df = pd.concat([self.df, df], ignore_index=True)


class MovesByPokemon(TableToCsv):
    name = "MovesByPokemon"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gen = int(kwargs["gen"])

        # retrieve all pokemon names
        pokemons = pd.read_csv(os.path.join(STATS_DIR, "all.csv"), sep=";")["Name"].to_list()
        pokemons = ["Butterfree"]
        self.url_dict = {
            f"https://pokemondb.net/pokedex/{pokemon.lower()}/moves/{self.gen}" : pokemon
            for pokemon in pokemons
        }
        self.start_urls = list(self.url_dict.keys())
        self.root = os.path.join(MOVES_DIR, f"gen_{self.gen}")

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

        """
        gen = self.gen
        # Moves learnt by level up
        by_level = pd.DataFrame(columns=["Move", "Lv."])
        # Moves learnt by HM
        by_hm = pd.DataFrame(columns=["Move", "HM"])
        # Moves learnt by TM
        by_tm = pd.DataFrame(columns=["Move", "TM"])
        # Egg moves
        by_egg = pd.DataFrame(columns=["Move", "Egg"])
        # Move Tutor moves
        by_tutor = pd.DataFrame(columns=["Move", "Tutor"])
        try:
            by_level = to_df_if(tables, 0, by_level)[["Move", "Lv."]]
            if gen == 1:
                # Ignore Pre-Evo moves in gen 1, they always come after level move if present
                if "Pre-evolution moves" in titles:
                    del tables[1]
                by_hm = to_df_if(tables, 1, by_hm)[["Move", "HM"]]
                by_tm = to_df_if(tables, 2, by_tm)[["Move", "TM"]]
            if gen == 2 or gen == 3 or gen == 4:
                by_egg = to_df_if(HTMLTable(tables[1]), by_egg)[["Move"]]
                by_hm = to_df_if(HTMLTable(tables[2]), by_hm)[["Move", "HM"]]
                by_tm = to_df_if(HTMLTable(tables[3]), by_tm)[["Move", "TM"]]
            if gen == 5 or gen == 6:
                by_egg = to_df_if(HTMLTable(tables[1]), by_egg)[["Move"]]
                by_tutor = to_df_if(HTMLTable(tables[2]), by_tutor)[["Move"]]
                by_hm = to_df_if(HTMLTable(tables[3]), by_hm)[["Move", "HM"]]
                by_tm = to_df_if(HTMLTable(tables[4]), by_tm)[["Move", "TM"]]
            if gen == 7 or gen == 8:
                by_egg = to_df_if(HTMLTable(tables[1]), by_egg)[["Move"]]
                by_tutor = to_df_if(HTMLTable(tables[2]), by_tutor)[["Move"]]
                by_tm = to_df_if(HTMLTable(tables[3]), by_tm)[["Move", "TM"]]
            """


    # Called for each urls in self.start_urls
    def parse(self, response):
        def to_df_if(selectors, index, df:pd.DataFrame):
            try:
                # In case selector is not a table or selectors is smaller than expected
                table = HTMLTable(selectors[index])
                converted = MovesByPokemon.as_dataframe(table)
                if len(converted) == 0:
                    return df
                return converted
            except:
                return df
        

        # Get Pokemon name from url
        pokemon = self.url_dict[response.url]
        # Get tables
        tables = response.xpath('//*[@class="data-table"]')

        title_tables = {}
        for title in response.xpath('//div[@class="grid-row"]/*/h3'):
            # We have the following hierarchy:
            # <div class="grid-col span-lg-6">
            #     <h3>Moves learnt by level up</h3> 
            # <p class="text-small"><em>Butterfree</em> learns the following moves in Pokémon Red &amp; Blue at the levels specified.</p> 
            # <div class="resp-scroll">
            #     <table class="data-table"> ...
            # 
            # So we are looking for the table at <title>/../div/table=data-table
            #
            # We could also have
            # <div class="grid-col span-lg-6">
            #   <h3>Moves learnt by HM</h3> 
            #   <p><em>Butterfree</em> does not learn any HMs in Pokémon Red &amp; Blue.</p> 
            # <h3>Moves learnt by TM</h3> 
            # <p class="text-small"><em>Butterfree</em> is compatible with these Technical Machines in Pokémon Red &amp; Blue:</p> 
            #     <div class="resp-scroll">
            #         <table class="data-table">
            #
            # This means we should <Moves learnt by HM>/../div/table=data-table will point to the TM table !!
            
            # For some reasons table are repeated twice, we only take the first one
            h3 = title.xpath("text()").get()
            next_table_selector = title.xpath('..//div/table[@class="data-table"]')
            # Check the h3 before the table is indeed the expected one by looking at the most close h3
            related_h3 = next_table_selector.xpath('../../h3')
            print("Related", h3, related_h3)

            
            title_tables[h3] = next_table_selector
            
        #for k,v in title_tables.items():
        #    print("AF", k, len(v))
        try:
            # Move learned by leveling up
            if "Moves learnt by level up" in title_tables:
                by_level = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Moves learnt by level up"]))[["Move", "Lv."]]
            else:
                by_level = pd.DataFrame(columns=["Move", "Lv."])
            # Move learned from pre-evolutions of the pokemon
            if "Pre-evolution moves" in title_tables:
                by_preevol = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Pre-evolution moves"]))["Move"]
            else:
                by_preevol = pd.DataFrame(columns=["Move", "PreEvol"])
            # Move learned by HM
            if "Moves learnt by HM" in title_tables:
                by_hm = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Moves learnt by HM"]))[["Move", "HM"]]
            else:
                by_hm = pd.DataFrame(columns=["Move", "HM"])
            # Move learned by HM
            if "Moves learnt by TM" in title_tables:
                by_tm = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Moves learnt by TM"]))[["Move", "TM"]]
            else:
                by_tm = pd.DataFrame(columns=["Move", "TM"])
            # Move learned from reproduction
            if "Egg moves" in title_tables:
                by_egg = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Egg moves"]))["Move"]
            else:
                by_egg = pd.DataFrame(columns=["Move", "Egg"])
            # Move learned by the tutor
            if "Move Tutor moves" in title_tables:
                by_tutor = MovesByPokemon.as_dataframe(HTMLTable(title_tables["Move Tutor moves"]))["Move"]
            else:
                by_tutor = pd.DataFrame(columns=["Move", "Tutor"])

            # Merge all dataframes to have all columns
            joined = by_level
            joined = pd.merge(joined, by_preevol, on="Move", how="outer")
            joined = pd.merge(joined, by_hm, on="Move", how="outer")
            joined = pd.merge(joined, by_tm, on="Move", how="outer")
            joined = pd.merge(joined, by_egg, on="Move", how="outer")
            joined = pd.merge(joined, by_tutor, on="Move", how="outer")

            # Add current pokemon name as a column
            joined["Name"] = [pokemon for i in range(len(joined))]

            # Concat global df
            self.df = pd.concat([self.df, joined], ignore_index=True)
            print(self.df)
        except Exception as e:
            print(pokemon, e)

@wait_for(3600)
def run_spider():
    crawler = CrawlerRunner()
    #d = crawler.crawl(CompletePokedexWithStats)
    #for i in ["all"] + list(range(1,9+1)):
    #    d = crawler.crawl(Moves, gen = i)

    d = crawler.crawl(MovesByPokemon, gen = "1")
    return d

if __name__ == "__main__":
    run_spider()
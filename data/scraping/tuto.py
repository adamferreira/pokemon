# scrape webpage
import scrapy
from scrapy.crawler import CrawlerRunner
# text cleaning
import re
# Reactor restart
from crochet import setup, wait_for
setup()

class InvalidSelector(Exception):
    ''' Exception raised when the table selector is invalid
    '''

def validate_selector(selector):
    ''' Validates if a selector has a match and can be used
    '''
    if not hasattr(selector, 'css'):
        raise InvalidSelector(f'Given selector [{type(selector)}] has no \
css function, is it a valid scrapy selector?')
    if len(selector) > 1:
        raise InvalidSelector("Selector matching more than one element")
    if len(selector) == 0:
        raise InvalidSelector("Selector not matching any elements")

def get_cells_from_row(row_selector):
    ''' Takes a tr selector and gets all cell values as strings
    '''
    cells = row_selector.css('td, th')
    return [ ''.join(cell.css('*::text').getall()) for cell in cells]

def get_all_rows_and_cells(table_selector):
    ''' Extracts all texts from all cells in all rows under selector
    '''
    rows = table_selector.css('tr')
    return list(map(get_cells_from_row, rows))

class Table:
    ''' Utility class to parse an html table into an array of arrays
    Usage:
    table = scraper.table.Table(response.css('#table_id'))
    table.get_header_row()
    table.get_rows()
    '''
    def __init__(self, table_selector):
        validate_selector(table_selector)
        self.rows = get_all_rows_and_cells(table_selector)

    def get_header_row(self):
        ''' Get values from first row
        '''
        return self.rows[0]

    def get_header_column(self):
        ''' Get values from first column
        '''
        cells = [row[0] for row in self.rows]
        return cells[1:]

    def get_rows(self):
        ''' Get all rows and their values
        '''
        return self.rows

    def as_dicts(self):
        ''' Using first row as headers get values as dictionary
        '''
        headers = self.rows[0]
        return [ dict(zip(headers, row)) for row in self.rows[1:] ]

class QuotesToCsv(scrapy.Spider):
    """scrape first line of  quotes from `wikiquote` by 
    Maynard James Keenan and save to json file"""
    name = "MJKQuotesToCsv"
    start_urls = [
        'https://pokemondb.net/pokedex/all',
    ]

    def parse(self, response):
        table = Table(response.xpath('//*[@id="pokedex"]'))
        yield from table.as_dicts()
        """
        for title in response.css('.oxy-post-title'):
            yield {'title': title.css('::text').get()}

        for next_page in response.css('a.next'):
            yield response.follow(next_page, self.parse)
        """

@wait_for(10)
def run_spider():
    """run spider with MJKQuotesToCsv"""
    crawler = CrawlerRunner()
    d = crawler.crawl(QuotesToCsv)
    print(dir(d))
    return d
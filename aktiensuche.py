from yahooquery import Ticker
import yahooquery
from pprint import pprint

def searchbyname(name: str, count=20) -> list:
    found = list()
    x = yahooquery.search(name, country="germany", quotes_count=count)
    quotes = x.get('quotes')
    pprint(x)
    if quotes:
        for quote in quotes:
            exchange = quote.get('exchDisp')
            longname = quote.get('longname', quote.get('shortname'))   # try / exception ???
            symbol = quote.get('symbol')
            quoteType = quote.get('quoteType')
            if quoteType in ['ETF', 'EQUITY']: 
                found.append({
                    'exchange' : exchange,
                    'longname' : longname, 
                    'symbol' : symbol,
                    'quoteType' : quoteType,
                    })
    return found

if __name__ == '__main__':
    f = searchbyname('Allianz')
    pprint(f)
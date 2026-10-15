from yahooquery import Ticker
from pprint import pprint

def toEUR(currency, price, rate):
    # Wenn price None ist, direkt None zurückgeben
    if price is None:
        return 0.0, currency
    if currency == "USD" and rate:
        price = price * rate
        currency = 'EUR'
    return price, currency
    
def get_prices_in_eur(ticker_symbols):
    myprices = dict()
    all_tickers = ticker_symbols + ["USDEUR=X"]
    t = Ticker(all_tickers)
    
    prices = t.price
    summary = t.summary_detail
    statistic = t.key_stats
    pprint(statistic)
    # Den aktuellen USD/EUR Wechselkurs holen
    usd_eur_rate = None
    rate_data = prices.get("USDEUR=X")
    if isinstance(rate_data, dict):
        usd_eur_rate = rate_data.get("regularMarketPrice")
        print(f"USDEUR=X Wechselkurs: {usd_eur_rate}") 

    # Prüfen, ob Daten für alle Ticker da sind
    for symbol in ticker_symbols:
        if symbol == 'USDEUR=X': 
            continue
        
        data = prices.get(symbol, {})
        summary_data = summary.get(symbol, {})
        statistic_data = statistic.get(symbol, {})
        
        price = data.get("regularMarketPrice")
        currency = data.get("currency", "EUR") # Fallback auf EUR, falls nicht vorhanden

        if price is None:
            print(f"{symbol}: Keine Daten gefunden")
            continue

        # Umrechnungen durchführen
        price_eur, curr_out = toEUR(currency=currency, price=price, rate=usd_eur_rate)
        price_open_eur, _ = toEUR(currency=currency, price=data.get('regularMarketOpen', 0.0), rate=usd_eur_rate)
        price_close_eur, _ = toEUR(currency=currency, price=data.get('regularMarketPreviousClose'), rate=usd_eur_rate)
        
        oneyearlow, _ = toEUR(currency=currency, price=summary_data.get('fiftyTwoWeekLow', 0.0), rate=usd_eur_rate)
        oneyearhigh, _ = toEUR(currency=currency, price=summary_data.get('fiftyTwoWeekHigh', 0.0), rate=usd_eur_rate)
        lastDividendValue, _ = toEUR(currency=currency, price=statistic_data.get('lastDividendValue', 0.0), rate=usd_eur_rate)
        
        enterprise_val, _ = toEUR(currency=currency, price=statistic_data.get('enterpriseValue', 0.0), rate=usd_eur_rate)

        print(f"{symbol}: {price_eur:.2f} {curr_out}")
        
        myprices[symbol] = {
            'name': data.get('longName', symbol),
            'currency': curr_out,
            'price': price_eur,
            'price_open': price_open_eur,
            'price_close': price_close_eur,
            'oneyearlow' : oneyearlow,
            'oneyearhigh': oneyearhigh,
            'dividende' : lastDividendValue,
            'kgv' : statistic_data.get('forwardPE', 0),
            'eps' : statistic_data.get('trailingEps', 0),
            'enterpriseValue': enterprise_val, 
            'priceToBook' : statistic_data.get('priceToBook', 0),
            'pegRatio': statistic_data.get('pegRatio', 0.0),
            'beta' : statistic_data.get('beta', 0.0), 
            'profitMargins' : summary_data.get('profitMargins', 0.0).   #  Die Nettomarge. Von jedem Euro Umsatz bleiben der Allianz knapp 10 Cent als Reingewinn. 
        }
        
    pprint(myprices)

if __name__ == "__main__":
    test_tickers = ["ALV.DE"] #, "AAPL"]  # Testweise mal eine US-Aktie (AAPL) dazugenommen
    get_prices_in_eur(test_tickers)
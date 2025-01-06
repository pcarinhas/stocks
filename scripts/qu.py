#! /usr/bin/env python3
"""Get Quotes from Yahoo

   Install these four
   ------------------
   * pytz>=2023.3.post1
   * yfinance>=0.2.28
   * tabulate>=0.9.0
   * termcolor>=2.3.0
"""
import csv
import datetime
import sys
import warnings
from io import StringIO
import re


import pytz
from tabulate import tabulate
from termcolor import colored
import yfinance as yf

# from yfin import YFinance as yf

warnings.simplefilter("ignore")
# ticker_re = re.compile(r"^\w+(?:[\w-]*\w)?$")
ticker_re = re.compile(r"^\^?\w+(?:[\-]\w)?$")


def currency_symbol(currency):
    table = dict(
        AUD="$",
        CAD="$",
        CNY="¥",
        EUR="€",
        GBP="£",
        HKD="元",
        INR="R",
        JPY="¥",
        PHP="₱",
        USD="$",
        ZAR="R",
    )
    return table.get(currency)


def int_to_human(n):
    if n == "N/A":
        return "N/A"
    if n == 0:
        return 0

    if n >= 1e9:
        return f"{n / 1e9:.1f}B"
    elif n >= 1e6:
        return f"{n / 1e6:.1f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.1f}K"
    else:
        return str(n)


def color_bias(num, poscolor="green", negcolor="red"):
    """Colorize red, using sign of trigger"""
    numerical = str(num).replace("%", "")
    if float(numerical) < 0.0:
        return colored(num, negcolor, attrs=["bold"])
        return colored(num, negcolor, attrs=["bold"])
    return colored(num, poscolor)


def color_trigger(num, trigger, poscolor="green"):
    """Colorize, using sign of trigger"""
    if float(trigger) < 0.0:
        return colored(num, "red", attrs=["bold"])
    return colored(num, poscolor)


def tricolor_bias_low(num, cutoff=4.0, poscolor="green"):
    """Colorize, using sign of trigger, negative numbers are bad"""
    if float(num) <= 0:
        return colored(num, "red", attrs=["bold"])
    if float(num) >= cutoff:
        return colored(num, "yellow", attrs=["bold"])
    return colored(num, poscolor)


def tricolor_bias_high(num, cutoff=4.0, poscolor="green"):
    """Colorize, using sign of trigger, negative numbers are bad"""
    if float(num) <= 0:
        return colored(num, "red", attrs=["bold"])
    if float(num) <= cutoff:
        return colored(num, "yellow", attrs=["bold"])
    return colored(num, poscolor)


def quadcolor_trigger(num, trigger=None, neg_value=1.0, warn_value=1.5, good_value=2.5):
    """For Quick and Current Ratios, colorize results"""
    # If the number doesn't exist, we return a dash to indicate non-existance
    if not num:
        return "-"

    negcolor = "red"
    warncolor = "yellow"
    goodcolor = "green"
    greatcolor = "cyan"
    """Colorize, using sign of trigger"""
    if not trigger:
        trigger = num

    num = round(num, 2)
    if float(trigger) < neg_value:
        return colored(num, negcolor, attrs=["bold"])
    if float(trigger) > neg_value and float(trigger) <= warn_value:
        return colored(num, warncolor, attrs=["bold"])
    if float(trigger) > warn_value and float(trigger) <= good_value:
        return colored(num, goodcolor, attrs=["bold"])
    if float(trigger) > good_value:
        return colored(num, greatcolor, attrs=["bold"])
    return colored(num, negcolor)


def quadcolor_bias_low(num, warn_value=2.0, good_value=1.5, great_value=1):
    """For Ratios, colorize results, negative value is bad,"""
    # If the number doesn't exist, we return a dash to indicate non-existance
    if not num:
        return "-"

    negcolor = "red"
    warncolor = "yellow"
    goodcolor = "green"
    greatcolor = "cyan"
    """Colorize, using sign of trigger"""

    num = round(num, 2)
    if float(num) < 0:
        return colored(num, negcolor, attrs=["bold"])
    if float(num) > 0 and float(num) <= great_value:
        return colored(num, greatcolor, attrs=["bold"])
    if float(num) > great_value and float(num) <= good_value:
        return colored(num, goodcolor, attrs=["bold"])
    if float(num) > good_value and float(num) <= warn_value:
        return colored(num, warncolor, attrs=["bold"])
    if float(num) > warn_value:
        return colored(num, negcolor, attrs=["bold"])
    return colored(num, negcolor)


def color_pct_trigger(num, trigger, poscolor="orange", negcolor="yellow"):
    """Return %dif, Colorize, using sign of trigger"""
    pct_vol = round(((num / trigger) * 100.0), 2)
    output = f"{pct_vol}%"

    if float(num) < trigger:
        output = colored(output, negcolor, attrs=["bold"])
    else:
        output = f"+{colored(output, poscolor, attrs=['bold'])}"

    return output


def side_by_side_tables(*tables):
    # Remove None in tables, though this should not happen.
    _tables = [x for x in tables if x is not None]
    if not _tables:
        return ""

    max_lines = max([len(tab.splitlines()) for tab in _tables])
    line_ranges = [len(tab.splitlines()) for tab in _tables]
    line_sizes = [len(tab.splitlines()[0]) for tab in _tables]

    # iterate each line naively and add to formatted
    formatted = ""
    for line in range(max_lines):
        # iterate through _tables
        for idx in range(len(_tables)):
            # Skip (continue) if line is greater than its line capacity
            if line > line_ranges[idx] - 1:
                formatted += " " * line_sizes[idx]
                continue
            # Write data from table to line
            formatted += _tables[idx].splitlines()[line]
        # Don't print the extra newline at end of group
        if line < max_lines - 1:
            formatted += "\n"

    return formatted


for symbol in sys.argv[1:]:

    if not ticker_re.match(symbol):
        warning = format(f"Ticker {symbol} is not a valid ticker symbol... Shamefull!")
        warning = colored(warning, "yellow", attrs=["bold"])
        print(warning)
        continue

    ticker = yf.Ticker(symbol)
    # If the length of ticker_info is small, its probably a dud.
    if len(ticker.info) <= 2:
        message = format(f"NOTE: {ticker.ticker} missing data! Possibly delisted!!")
        message = colored(message, "red", attrs=["bold"])
        print(message)
        continue

    try:
        ticker_info = ticker.info
    except Exception as e:
        print(e)
        message = format(f"NOTE: Ticker {ticker} does not exist!")
        message = colored(message, "red", attrs=["bold"])
        print(message)
        continue

    # This is the only dependable way to get price. Some issues don't have
    current = ticker_info.get("currentPrice")
    if not current:
        try:
            ticker.history(period="max")
            current = ticker.history_metadata.get("regularMarketPrice")
        except Exception as ex:
            print(type(ex))
            data = ticker.history()
            if data.get("Close").size == 0:
                sys.exit(1)
            current = data.get("Close").iloc[-1]

    # If no current price, just skip
    if not current:
        continue

    current = round(current, 5)
    previous = ticker_info.get("regularMarketPreviousClose")
    change = round(
        current - previous,
        4,
    )
    change_pct = round(
        100 * (current - previous) / previous,
        2,
    )
    if change >= 0:
        change = "+" + str(change)
        change_pct = "+" + str(change_pct) + "%"
    else:
        change = str(change)
        change_pct = str(change_pct) + "%"

    if len(sys.argv) > 2:
        print("=" * 80)

    change_num = color_bias(change)
    change_pct_num = color_bias(change_pct)
    current_val = color_trigger(current, change, "green")
    short_name = ticker.info.get("shortName")
    country = ticker.info.get("country", "None")
    exchange = ticker.info.get("exchange")
    value = (
        f"{symbol.upper()}: {short_name} "
        f"({country}:"
        f"{exchange}) "
        f"|| {current_val}: {change_num} "
        f": {change_pct_num}"
    )
    print(value)
    timezone = pytz.timezone("US/Eastern")
    now = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"Time: {now}")
    print(f"Sector/Industry: {ticker_info.get('sector')}/{ticker_info.get('industry')}")

    table = []
    _vol = ticker_info.get("volume")
    if not _vol:
        continue
    volume = f"Volume: {_vol:>8}"
    _ave_vol = ticker_info.get("averageVolume")
    if not _ave_vol:
        print("Zero Average Volume: skipping: ", symbol.upper())
        continue
    ave_vol = f"AveVol: {_ave_vol}"
    pct_diff = color_pct_trigger(_vol, _ave_vol, poscolor="cyan", negcolor="yellow")
    vol_diff = f"VolPct: {pct_diff}"
    shares_outstanding = ticker_info.get("sharesOutstanding", "N/A")
    shares_outstanding = int_to_human(shares_outstanding)
    shares_outstanding = f"Outstanding: {shares_outstanding:>5}"
    table.append([ave_vol, volume, vol_diff, shares_outstanding])

    shares_float = ticker_info.get("floatShares", "N/A")
    shares_float = int_to_human(shares_float)
    shares_float = f"Float Share: {shares_float:>5}"

    shares_inst = ticker_info.get("heldPercentInstitutions")
    if shares_inst is None:
        shares_inst = "Institu Pct:   N/A"
    else:
        shares_inst_pct = round(shares_inst * 100.0, 1)
        shares_inst = f"Institu Pct: {shares_inst_pct:4}%"

    options = ticker.options
    options_count = None
    if options:
        opts = len(options)
        opts = color_bias(opts)
        options_count = f"Options: {opts:>16}"

    # Sometimes the open values are not correct in info. Its ugly.
    _open = round(ticker_info.get("open"), 5)
    if not _open:
        _open = round(ticker.get_fast_info.get("open"), 5)
    Open = f"Open: {_open:>10.2f}"
    _close = ticker_info.get("regularMarketPreviousClose")
    Close = f"PrevClose: {_close:>5}"
    delta = color_bias(round(_open - _close, 4))
    delta = f"OpenDif: {delta:>14}"
    table.append([Open, Close, delta, shares_float])

    _high = ticker_info.get("dayHigh")
    high = f"High: {_high:>10.2f}"
    _low = round(ticker_info.get("dayLow"), 2)
    low = f"Low: {_low:>11.2f}"
    _diff = round(_high - _low, 4)
    diff = f"Diff: {_diff:>8.2f}"
    shares_inside_pct = ticker_info.get("heldPercentInsiders")
    if shares_inside_pct is None:
        shares_inside_pct = "Insider Pct:   N/A"
    else:
        shares_inside_pct = round(shares_inside_pct * 100.0, 1)
        shares_inside_pct = f"Insider Pct: {shares_inside_pct:4}%"
    table.append([high, low, diff, shares_inside_pct])

    _bid = ticker_info.get("bid")
    _ask = ticker_info.get("ask")
    if not _bid or not _ask:
        bid = "-"
        ask = "-"
        _diff = "-"
        spread = "-"
    else:
        bid = f"Bid: {_bid:>11.2f}"
        ask = f"Ask: {_ask:11}"
        _diff = round(_ask - _bid, 4)
        spread = f"Spread: {_diff:>6.2f}"

    table.append([bid, ask, spread, shares_inst])

    _bid_size = ticker_info.get("bidSize")
    _ask_size = ticker_info.get("askSize")
    if not _bid_size or not _ask_size:
        bid_size = "-"
        ask_size = "-"
    else:
        bid_size = f"BidSize: {_bid_size:>7}"
        ask_size = f"AskSize: {_ask_size:>7}"

    _beta = ticker_info.get("beta")
    if _beta:
        _beta = round(ticker_info.get("beta"), 4)
        _beta = f"Beta:  {_beta:>7.2f}"
    else:
        _beta = "Beta:     N/A"

    # short_timestamp = ticker_info.get("dateShortInterest")

    table.append([bid_size, ask_size, _beta, options_count])
    table1 = tabulate(table, tablefmt="outline")
    print(table1)

    # -------------------------------------------------------------------------
    # Analysts
    # -------------------------------------------------------------------------
    table = []
    num_of_analysts = ticker_info.get("numberOfAnalystOpinions", "0")
    num_of_analysts = tricolor_bias_high(num_of_analysts)
    table.append(["Num Analysts: ", num_of_analysts])

    recommendation = ticker_info.get("recommendationKey", "-").lower().strip()
    if "buy" in recommendation:
        recommendation = colored(recommendation.upper(), "green", attrs=["bold"])
    elif "hold" in recommendation:
        recommendation = colored(recommendation.upper(), "yellow", attrs=["bold"])
    elif "sell" in recommendation or "underperform" in recommendation:
        recommendation = colored(recommendation.upper(), "red", attrs=["bold"])
    else:
        recommendation = recommendation.upper()

    table.append(["Recommendation:", recommendation])
    table.append(["TargetLow:", ticker_info.get("targetLowPrice", "-")])
    table.append(["TargetHigh:", ticker_info.get("targetHighPrice", "-")])
    target_mean = ticker_info.get("targetMeanPrice")
    if target_mean:
        target_mean_ratio = target_mean / current
        target_mean_colored = quadcolor_trigger(
            target_mean,
            trigger=target_mean_ratio,
            neg_value=1.5,
            warn_value=3.0,
            good_value=4.0,
        )
        table.append(["TargetMean:", target_mean_colored])

    target_median = ticker_info.get("targetMedianPrice")
    if target_median:
        target_median_ratio = target_median / current
        target_median_colored = quadcolor_trigger(
            target_median,
            trigger=target_median_ratio,
            neg_value=1.5,
            warn_value=3.0,
            good_value=4.0,
        )
        table.append(["TargetMedian:", target_median_colored])

    analyst_table = tabulate(table, tablefmt="outline")

    # -------------------------------------------------------------------------
    # Ratios
    # -------------------------------------------------------------------------
    ratio_table = []
    quick_ratio = ticker_info.get("quickRatio")
    ratio_table.append(["QuickRatio:", quadcolor_trigger(quick_ratio)])
    current_ratio = ticker_info.get("currentRatio")
    ratio_table.append(["CurrentRatio:", quadcolor_trigger(current_ratio)])
    # We use inverse of PEG as trigger here because PEG_good \in (0,1)
    # ratio_table.append(["PEG Ratio:", ticker_info.get("pegRatio", "-")])
    trailing_peg_ratio = ticker_info.get("trailingPegRatio")
    if trailing_peg_ratio:
        ratio_table.append(
            [
                "TrailingPEG:",
                quadcolor_trigger(
                    trailing_peg_ratio,
                    trigger=(1 / trailing_peg_ratio),
                    neg_value=0.5,
                    warn_value=1.05,
                    good_value=1.11,
                ),
            ]
        )
    else:
        ratio_table.append(["TrailingPEG", "-"])

    peg_ratio = ticker_info.get("pegRatio")
    if peg_ratio:
        ratio_table.append(
            [
                "PEG Ratio:",
                quadcolor_trigger(
                    peg_ratio,
                    trigger=(1 / peg_ratio),
                    neg_value=0.5,
                    warn_value=1.05,
                    good_value=1.11,
                ),
            ]
        )
    short_ratio = ticker_info.get("shortRatio")
    if short_ratio:
        short_ratio = tricolor_bias_low(short_ratio)
        ratio_table.append(["Short Ratio:", short_ratio])
    # If either book value or NAV exists, show them. Usually mutually exlusive
    book_value = ticker_info.get("bookValue")
    if book_value:
        price_book_ratio = round(current / book_value, 2)
        price_book_ratio = tricolor_bias_low(price_book_ratio)
        ratio_table.append(["Price/Book:", price_book_ratio])
    else:
        ratio_table.append(["Price/Book:", "-"])

    nav_price = ticker_info.get("navPrice")
    if nav_price:
        ratio_table.append(["NAV:", nav_price])
    ratio_table = tabulate(ratio_table, tablefmt="outline")

    trailing_eps = ticker_info.get("trailingEps")
    forward_eps = ticker_info.get("forwardEps")

    # -------------------------------------------------------------------------
    # Earnings
    # -------------------------------------------------------------------------
    table = []
    earnings_table = None
    if trailing_eps:
        trailing_eps_formatted = color_bias(trailing_eps)
        table.append(["TrailingEps:", trailing_eps_formatted])
    else:
        table.append(["TrailingEps:", "-"])

    if forward_eps:
        forward_eps_formatted = color_bias(forward_eps)
        table.append(["ForwardEps:", forward_eps_formatted])
    else:
        table.append(["ForwardEps:", "-"])

    div_rate = ticker_info.get("dividendRate")
    if div_rate:
        table.append(["DivRate:", div_rate])

    # sometimes trailingAnnualDividendYield is not available.
    div_yield = ticker_info.get("trailingAnnualDividendYield")
    if div_yield is None and div_rate:
        div_yield = div_rate / current

    if div_yield:
        div_yield = round(div_yield * 100.0, 2)
        div_yield = f"{str(div_yield)}%"
        table.append(["Yield:", div_yield])

    debt_equity_ratio = ticker_info.get("debtToEquity")
    if debt_equity_ratio:
        debt_equity_ratio = quadcolor_bias_low(debt_equity_ratio, warn_value=5)
        table.append(["DbtEqRatio:", debt_equity_ratio])

    currency = ticker_info.get("financialCurrency")
    cur_symbol = currency_symbol(currency)

    cash = ticker_info.get("totalCash")
    if cash:
        cash = int_to_human(cash)
        cash = f"{cash}"
        title = f"Cash: {cur_symbol}"
        table.append([title, cash])

    debt = ticker_info.get("totalDebt")
    if debt:
        debt = int_to_human(debt)
        debt = f"{debt}"
        title = f"Debt: {cur_symbol}"
        table.append([title, debt])

    # If table non empty, create it.
    if table:
        earnings_table = tabulate(table, tablefmt="outline")

    sst = side_by_side_tables(analyst_table, ratio_table, earnings_table)
    if sst:
        print(sst)

    # -------------------------------------------------------------------------
    # Dividend History
    # -------------------------------------------------------------------------
    # if there are no dividends, continue
    if not ticker.history(period="max").any().Dividends:
        continue

    # limit dividend horizon to 1 year:
    history = ticker.history(period="2y")

    dividends = ticker.get_dividends()
    dividend_table = None
    if not dividends.empty:
        data = dividends.tail(12).to_csv()
        table = csv.reader(StringIO(data))
        dividend_table = tabulate(table, headers="firstrow", tablefmt="outline")

    if not div_yield:
        div_rate = round(dividends.sum(), 2)
        div_yield = div_rate / current
        div_pct = round(div_yield * 100.0, 2)
        if div_rate:
            print(f"Calculated Dividend Rate: {div_rate}")
            print(f"Calculated Dividend Yield: {div_pct}%")

    if dividend_table:
        print(dividend_table)

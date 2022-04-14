import argparse
from ai_article_handler import process_article_request
from datetime import datetime
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', required=True, help="Required: customer name")
    parser.add_argument('-f', '--fetch', required=True, help="Required: fetch games, valid inputs are \'True\' and \'False\'")
    parser.add_argument('-r', '--range', required=False, help="Default: 0 otherwise specifiy (int) "
                                                              "number of days to fetch from", default=0)
    parser.add_argument('-d', '--date', required=False, help="The game day date in MM-DD-YYYY")

    args = parser.parse_args()

    name = args.name

    fetch_games = args.fetch
    if fetch_games == "True" or fetch_games == "False":
        fetch_games = eval(fetch_games)
    else:
        print("-f input must be True or False, exiting...")
        exit(1)

    range = int(args.range)

    if args.date:
        game_date = datetime.strptime(args.date, "%m-%d-%Y")
    else:
        game_date = None

    process_article_request(customer_name=name, fetch_games=fetch_games, game_range_days=range,
                            fixed_date_time=game_date)


if __name__ == '__main__':
    try:
        main()
    except ValueError as e:
        print(repr(e))

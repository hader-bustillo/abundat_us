from db import dynamo
from datetime import datetime, timedelta

old_table = "RS_AI_SS_GAMES"

new_table = "LEDE_AI_NEW_GAMES_TABLE"

alt_table = "LEDE_AI_NEW_GAMES_TABLE_ALT"


start_date = "2021-09-15 00:00:00"

current_end_date = "2021-09-23 00:00:00"

end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# while item_date.strftime("%Y %m %d") < end_date:
    # posted_items = dynamo.dynamo_scan_table(table_name=old_table, keys=['logtime', 'logtime'],
    #                          vals=[item_date.strftime("%Y %m %d"),(item_date + timedelta(days=1)).strftime("%Y %m %d") ],
    #                          operators=['>=','<' ],
    #                          is_and=True)

# posted_items = dynamo.dynamo_db_scan(table_name=old_table)

game_items = dynamo.dynamo_scan_table(table_name=old_table, keys=['startDateTime', 'startDateTime', 'confidenceGrade'],
                                      vals=[start_date, current_end_date, 99], operators=['>=', '<=', '>='], is_and=True)

print("the total number of items found is %d" % (len(game_items)))






import ai_article_handler as tnp
from datetime import datetime
from logging import getLogger


logger = getLogger(__name__)


test_date = datetime(2018, 10, 4, 00, 00)


tnp.write_customer_articles(customer_name="Richland Source", fetch_games=True,
                            fixed_date_time=test_date, game_range_days=0)

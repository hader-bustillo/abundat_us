from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)


class Dates:

    @staticmethod
    def get_day_of_week(year:int,month:int,day:int):
        return datetime(year,month,day).strftime("%A")

    @staticmethod
    def utc_date_range(local_date_time=datetime.now(), game_range_days=0, timezone="US/Eastern"):
        logging.info("The datetime received is %s", local_date_time.strftime("%Y-%m-%d %H:%M"))

        local_date_time = datetime(local_date_time.year, local_date_time.month, local_date_time.day, 1, 30)
        eastern_time_object = pytz.timezone('US/Eastern').normalize(
            pytz.timezone('US/Eastern').localize(local_date_time))

        customer_timezone = pytz.timezone(timezone)

        customer_local_normalized_time = eastern_time_object.astimezone(customer_timezone)

        date_range = [customer_timezone.localize(datetime(customer_local_normalized_time.year, customer_local_normalized_time.month,
                               customer_local_normalized_time.day, 0, 0) - timedelta(
                    days=game_range_days)),
                     customer_timezone.localize(datetime(customer_local_normalized_time.year, customer_local_normalized_time.month,
                              customer_local_normalized_time.day, 23, 59))]

        utc_range = [dt.astimezone(pytz.utc) for dt in date_range]

        utc_formatted_date_range = [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in utc_range]

        logging.info(" the UTC date range is %s and %s", utc_formatted_date_range[0], utc_formatted_date_range[1])
        return utc_formatted_date_range

    @staticmethod
    def utc_to_local(utc_date_time_str:str, time_zone:str):
        logging.info("The UTC datetime string is %s with timezone %s", utc_date_time_str, time_zone)
        utc_date_time = datetime.strptime(utc_date_time_str, '%Y-%m-%d %H:%M:%S')
        to_zone = pytz.timezone(time_zone)
        from_zone = pytz.utc

        utc_date_time = utc_date_time.replace(tzinfo=from_zone)

        # Convert time zone
        game_localized_time = utc_date_time.astimezone(to_zone)

        return game_localized_time


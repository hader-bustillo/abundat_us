"""
This module provides the necessary methods to check if publish stats are available and sends
an email with those details .
"""
import logging
import json
from utils import utils


logger = logging.getLogger(__name__)


def general_stats_info(articles, stats):
    logging.info("Priting out general stats information")
    stats_str = "<p></p>"
    for name, system in stats.items():
        stats_str += "<p><b>" + name + "</b>:</p>" + "\n"
        for rc,count in system.items():
            if rc == 201:
                stats_str += "<p>Number of articles published successfully - " + str(count) + "</p>\n" 
            elif rc == 409:
                stats_str += "<p>Number of articles already successfully published, hence ignoring this run- " + str(count) + "</p>\n"
            else:
                stats_str += "<p>Number of articles we were unsuccessful in publishing - " + str(count) + "</p>\n"
    return stats_str



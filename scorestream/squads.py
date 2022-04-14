"""
Constructs a Squads object from the scorestream data and uploads it to the dynamo db.
"""
import logging

logger = logging.getLogger(__name__)


class Squads:
    def __init__(self, complete_result):
        self.complete_result = complete_result['collections']
        
    def get_squad_list(self):
        return self.complete_result['squadCollection']['list']

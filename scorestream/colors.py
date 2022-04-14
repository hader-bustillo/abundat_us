"""
Constructs a Colors object from the data provided by scorestream and is uploaded to the dynamoDB.

"""
import logging

logger = logging.getLogger(__name__)



class Colors:
    def __init__(self,complete_result):
        self.complete_result = complete_result['collections']
        
    def get_colors_list_from_ss(self):
        return self.complete_result['colorCollection']['list']

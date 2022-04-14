"""
Constructs a url that should be used in retrieving data from scorestream.

"""
import requests
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class ss_url_requests():
    
    url = 'http://scorestream.com/api?request='
    post_url = 'https://scorestream.com/api'

    def __init__(self, method, params, method_key='method'):
        self.method_key = method_key
        self.method = method
        self.params = params
        
        
    def get_base_url(self, url=None):
        if url is not None:
            logging.debug("The Url is %s", url)
            return url
        else:
            logging.debug("The self Url is %s", self.url)
            return self.url
    
    
    def get_method(self):
        return self.string_to_url_val(self.method_key)+':'+self.string_to_url_val(self.method)

    
    def get_params(self, key='params'):
        return self.string_to_url_val(key)+':'+self.convert_params(par=self.params)
    

    def convert_params(self,par):
        param_keys = list(par)
        param_vals = list(par.values())
        
        #self.handle_dict_params(self.params)
        
        param_keys = self.convert_string_params(param_keys)
        param_vals = self.convert_string_params(param_vals)
        
        return self.ret_params(param_keys,param_vals)
    
    def string_to_url_val(self, val):
        if type(val) is str:
            return '%22'+val+'%22'
        elif self.check_for_dict(val) is True:
            return self.convert_params(val)
        else:
            return val
        
    def convert_string_params(self, par):
        for i in range(len(par)):
            par[i] = self.string_to_url_val(par[i])
        return par
    
    def ret_params(self, keys, vals):
        ret_str = '{'
        key_length = len(keys)
        for i in range(key_length):
            
            val = vals[i]
            key = str(keys[i])
            ret_str = ret_str+'%s:%s,'%(key, val)
            
        ret_str = ret_str[:-1]
        ret_str = ret_str+'}'
        return ret_str

    def check_for_dict(self, val):
        if type(val) is dict:
            return True
        else:
            return False
    
    def get_request(self):
        return self.url+'{'+self.get_method()+','+self.get_params()+'}'
    
    def make_request(self):
        request = requests.get(url=self.get_request())
        logging.debug("The request is %s", request)
        return request
    
    def post_request(self):
        data = { self.method_key : self.method,
                 'params': self.params}

        request = requests.post(url=self.post_url, json=data)

        logging.debug("The request is %s", request)
        return request


from typing import Dict
from data_processor.data_modifier import DataModifier
from data_processor.model_params_generator import ModelParams
from util.header import *


class DataPreprocessor:
    def __init__(self, data_dict, start_week: str, T=26):

        self._T = T

        _data_modifier = DataModifier(data_dict, start_week, T)
        self._data_dict = _data_modifier.get_modified_data_dict()

        self._generate_processed_data_cls()


    def get_modified_data_dict(self):
        return self._data_dict
    

    def get_processed_data_cls(self) -> Dict:
        return self._processed_data_cls


    def _generate_processed_data_cls(self):
        self._processed_data_cls = ModelParams(self._data_dict, self._T)
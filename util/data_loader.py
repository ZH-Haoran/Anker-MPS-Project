from data.data_reader import DataReader
from data_processor.data_preprocessor import DataPreprocessor
from util.header import *
import warnings

warnings.filterwarnings('ignore')


def load_model_params(start_week, T):
    """加载数据"""
    data_reader = DataReader()
    data_dict = data_reader.get_data_dict()
    data_preprocessor = DataPreprocessor(data_dict, start_week, T)
    modified_data_dict = data_preprocessor.get_modified_data_dict()
    model_params_cls = data_preprocessor.get_processed_data_cls()

    return model_params_cls, modified_data_dict

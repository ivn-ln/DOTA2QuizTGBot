import json
import logging
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class JsonTools:
    @staticmethod
    def add_dict_to_json(json_file, data_dict, ignore_existing=True):
        try:
            with open(json_file, 'r') as file:
                json_data = json.load(file)
        except json.JSONDecodeError:
            json_data = {}

        for key, value in data_dict.items():
            if key in json_data and ignore_existing:
                logging.log(logging.INFO ,f"Key '{key}' already exists in the JSON file. Ignoring the addition.")
            else:
                json_data[key] = value

        with open(json_file, 'w') as file:
            json.dump(json_data, file, indent=4, cls=NumpyEncoder)

    @staticmethod
    def load_dict_from_json(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data



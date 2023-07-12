import json

class JsonTools:
    @staticmethod
    def add_dict_to_json(json_file, data_dict):
        try:
            with open(json_file, 'r') as file:
                json_data = json.load(file)
        except json.JSONDecodeError:
            json_data = {}

        for key, value in data_dict.items():
            if key in json_data:
                print(f"Key '{key}' already exists in the JSON file. Ignoring the addition.")
            else:
                json_data[key] = value

        with open(json_file, 'w') as file:
            json.dump(json_data, file, indent=4)
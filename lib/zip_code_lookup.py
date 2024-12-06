import csv
from typing import Optional, Dict, List


class ZipCodeLookup:
    def __init__(self, csv_file: str):
        self.zip_data: Dict[str, Dict[str, str]] = {}
        self._load_csv(csv_file)

    def _load_csv(self, csv_file: str):
        """Load data from a CSV file into a dictionary."""
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.zip_data[row['zip']] = row

    def get_primary_city(self, zip_code: str) -> Optional[str]:
        """Retrieve the primary city for a given zip code."""
        return self.zip_data.get(zip_code, {}).get('primary_city')

    def get_state(self, zip_code: str) -> Optional[str]:
        """Retrieve the state for a given zip code."""
        return self.zip_data.get(zip_code, {}).get('state')

    def get_county(self, zip_code: str) -> Optional[str]:
        """Retrieve the county for a given zip code."""
        return self.zip_data.get(zip_code, {}).get('county')

    def get_acceptable_cities(self, zip_code: str) -> List[str]:
        """Retrieve the list of acceptable cities for a given zip code."""
        acceptable_cities = self.zip_data.get(zip_code, {}).get('acceptable_cities', "")
        return [city.strip() for city in acceptable_cities.split(',')] if acceptable_cities else []

    def get_unacceptable_cities(self, zip_code: str) -> List[str]:
        """Retrieve the list of unacceptable cities for a given zip code."""
        unacceptable_cities = self.zip_data.get(zip_code, {}).get('unacceptable_cities', "")
        return [city.strip() for city in unacceptable_cities.split(',')] if unacceptable_cities else []

    def get_fallback_city(self, zip_code: str) -> Optional[str]:
        """
        Retrieve the primary city for a given zip code.
        If the primary city is null or empty, return the first acceptable city.
        If that is also null or empty, return None.
        """
        if not zip_code:
            return None
        
        data = self.zip_data.get(zip_code, {})
        primary_city = data.get('primary_city')
        if primary_city:  # If primary city exists and is not empty
            return primary_city

        # Retrieve acceptable cities and pick the first one if available
        acceptable_cities = data.get('acceptable_cities', "")
        acceptable_list = [city.strip() for city in acceptable_cities.split(',') if city.strip()]
        return acceptable_list[0] if acceptable_list else None

    def lookup(self, zip_code: str) -> Optional[Dict[str, str]]:
        """Retrieve all information for a given zip code."""
        return self.zip_data.get(zip_code)

import requests

class BankAPI:
    BASE_URL = 'https://nubapi.com/api/verify'

    def __init__(self, bearer_token):
        self.headers = {
            'Authorization': f'Bearer {bearer_token}',
        }

    def get_account_details(self, account_number, bank_code):
        params = {
            'account_number': account_number,
            'bank_code': bank_code,
        }
        response = requests.get(self.BASE_URL, headers=self.headers, params=params)
        return response.json()

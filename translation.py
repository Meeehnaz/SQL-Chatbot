import requests, uuid, json
from config import config as config 

key = config["AZURE-TRANSLATOR-SERVICE"]["API_KEY"]
endpoint = config["AZURE-TRANSLATOR-SERVICE"]["ENDPOINT"]
location = config["AZURE-TRANSLATOR-SERVICE"]["LOCATION"]
path = '/translate'
constructed_url = endpoint + path

params = {
    'api-version': '3.0',
    'to': ['en']
}

headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Ocp-Apim-Subscription-Region': location,
    'Content-type': 'application/json',
    'X-ClientTraceId': str(uuid.uuid4())
}

def translate_text(text, to_lang):
    """
    Translates text to the specified language using Microsoft Translator API.

    Args:
    - text (str): Text to be translated.
    - to_lang (str): Target language code (e.g., 'en' for English).

    Returns:
    - dict: JSON response containing translated text.

    Raises:
    - Exception: If there is an error during the translation request.
    """
    try:
        body = [{'text': text}]
        response = requests.post(constructed_url, params={'api-version': '3.0', 'to': [to_lang]}, headers=headers, json=body)
        return response.json()
    except Exception as e:
        raise Exception(f"Translation error: {e}")
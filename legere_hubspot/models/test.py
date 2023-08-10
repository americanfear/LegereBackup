import requests

url = "https://045e76557773-747780121491364008.ngrok-free.app/webhook/hubspot"
data = {'status': 'okay'}

response = requests.post(url, json=data, timeout=60)
print ("=========response", response)
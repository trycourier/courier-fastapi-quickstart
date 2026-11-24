import os

from courier import Courier

client = Courier(api_key=os.environ["COURIER_API_KEY"])

response = client.send.message(
    message={
        "to": {"email": os.environ["DEMO_EMAIL"]},
        "content": {"title": "Your agent run finished", "body": "Sent from FastAPI with Courier."},
        "routing": {"method": "single", "channels": ["email"]},
    },
)
print(response.request_id)

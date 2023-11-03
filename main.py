from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import httpx
from typing import Optional
import os

# Initialize FastAPI app
app = FastAPI()

class WhatsAppMessageRequest(BaseModel):
    to: str
    body: str
    preview_url: Optional[bool] = False

class WhatsAppMessageResponse(BaseModel):
    recipient_id: str
    message_id: str

class WebhookPayload(BaseModel):
    object: str
    entry: list

# Environment Variables
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
FROM_PHONE_NUMBER_ID = os.getenv("FROM_PHONE_NUMBER_ID")

@app.post("/send-whatsapp-message/", response_model=WhatsAppMessageResponse)
async def send_whatsapp_message(message: WhatsAppMessageRequest):
    url = f"https://graph.facebook.com/v18.0/{FROM_PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.to,
        "type": "text",
        "text": {
            "preview_url": message.preview_url,
            "body": message.body
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()

@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload):
    print(payload.json(indent=2))

    if payload.object:
        for entry in payload.entry:
            for change in entry.get("changes", []):
                if 'value' in change and 'messages' in change['value']:
                    messages = change['value']['messages']
                    if messages:
                        phone_number_id = change['value']['metadata']['phone_number_id']
                        for message in messages:
                            from_ = message['from']
                            msg_body = message['text']['body']
                            
                            # Echo the received message back to the sender
                            async with httpx.AsyncClient() as client:
                                await client.post(
                                    f"https://graph.facebook.com/v12.0/{phone_number_id}/messages",
                                    params={"access_token": ACCESS_TOKEN},
                                    json={
                                        "messaging_product": "whatsapp",
                                        "to": from_,
                                        "text": {"body": f"Ack: {msg_body}"}
                                    },
                                    headers={"Content-Type": "application/json"}
                                )
   
    return status.HTTP_200_OK

@app.get("/webhook")
async def confirm_webhook(mode: str, token: str, challenge: str):
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app', host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

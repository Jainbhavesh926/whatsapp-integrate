from fastapi import FastAPI, Request, status, HTTPException
from pydantic import BaseModel
import httpx
import os
 
app = FastAPI()
 
# The token to authenticate your app with WhatsApp API
# Make sure to set this in your environment variables
token = os.getenv("WHATSAPP_TOKEN")
verify_token = os.getenv("VERIFY_TOKEN")
 
class WebhookPayload(BaseModel):
    object: str
    entry: list
 
@app.post("/webhook")
async def receive_webhook(payload: WebhookPayload):
    # Check the Incoming webhook message
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
                                    params={"access_token": token},
                                    json={
                                        "messaging_product": "whatsapp",
                                        "to": from_,
                                        "text": {"body": f"Ack: {msg_body}"}
                                    },
                                    headers={"Content-Type": "application/json"}
                                )
        return status.HTTP_200_OK
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
 
@app.get("/webhook")
async def confirm_webhook(mode: str, token: str, challenge: str):
    # Verification endpoint for the webhook
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            return challenge
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run('app', host="0.0.0.0", port=int(os.getenv("PORT", 1337)))
import os

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger as log

app = FastAPI(title="Integrations API")

security = HTTPBearer()

WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")


# todo create on start run all scenarios


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Bearer token from Authorization header."""
    if not WEBHOOK_TOKEN:
        log.warning("WEBHOOK_TOKEN not configured, skipping authentication")
        return credentials

    if credentials.credentials != WEBHOOK_TOKEN:
        log.warning(f"Invalid token received")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return credentials


class AlertLabel(BaseModel):
    alertname: str
    device: Optional[str] = None
    severity: Optional[str] = None
    alertstate: Optional[str] = None
    instance: Optional[str] = None
    job: Optional[str] = None


class AlertAnnotation(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None


class Alert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: str
    endsAt: str
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None


class AlertmanagerWebhook(BaseModel):
    receiver: str
    status: str
    alerts: list[Alert]
    groupLabels: dict
    commonLabels: dict
    commonAnnotations: dict
    externalURL: str
    version: str
    groupKey: str
    truncatedAlerts: Optional[int] = 0


@app.post("/api/alerts")
async def receive_alerts(
        webhook: AlertmanagerWebhook,
        credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """
    Endpoint for receiving Alertmanager webhook notifications.
    """
    log.info(f"Received alert webhook: status={webhook.status}, receiver={webhook.receiver}")

    for alert in webhook.alerts:
        alertname = alert.labels.get("alertname", "unknown")
        device = alert.labels.get("device", "unknown")
        severity = alert.labels.get("severity", "unknown")
        status = alert.status

        log.info(
            f"Alert triggered: name={alertname}, device={device}, "
            f"severity={severity}, status={status}"
        )

    return {
        "status": "received",
        "alerts_count": len(webhook.alerts),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

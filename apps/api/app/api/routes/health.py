"""Health endpoints."""


def health_payload():
    return {"status": "ok", "service": "event-surge-api"}


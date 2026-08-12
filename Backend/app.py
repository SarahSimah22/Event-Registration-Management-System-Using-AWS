import json
import os
from datetime import datetime
from urllib.parse import unquote

TABLE_NAME = os.environ.get("TABLE_NAME")
DYNAMO_ENABLED = bool(TABLE_NAME)

events = [
    {"eventId": "aws-cloud-meetup", "name": "AWS Cloud Meetup", "date": "2026-09-20", "capacity": 30, "registeredCount": 0},
    {"eventId": "devops-summit", "name": "DevOps Summit", "date": "2026-10-15", "capacity": 20, "registeredCount": 0},
    {"eventId": "ai-workshop", "name": "AI Workshop", "date": "2026-11-05", "capacity": 15, "registeredCount": 0},
]

registrations = {}

table = None
if DYNAMO_ENABLED:
    import boto3
    from boto3.dynamodb.conditions import Attr, Key

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)


def _json_response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(payload),
    }


def _get_event(event_id):
    for event in events:
        if event["eventId"] == event_id:
            return event
    return None


def _scan_registrations(filter_expression=None):
    if not DYNAMO_ENABLED:
        return list(registrations.values())

    scan_kwargs = {}
    if filter_expression is not None:
        scan_kwargs["FilterExpression"] = filter_expression

    items = []
    response = table.scan(**scan_kwargs)
    items.extend(response.get("Items", []))
    while response.get("LastEvaluatedKey"):
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"], **scan_kwargs)
        items.extend(response.get("Items", []))
    return items


def _sync_event_counts():
    if DYNAMO_ENABLED:
        counts = {}
        items = _scan_registrations()
        for item in items:
            counts[item.get("eventId")] = counts.get(item.get("eventId"), 0) + 1
        for event in events:
            event["registeredCount"] = counts.get(event["eventId"], 0)
    else:
        for event in events:
            event["registeredCount"] = sum(
                1 for registration in registrations.values() if registration["eventId"] == event["eventId"]
            )


def _list_events():
    _sync_event_counts()
    return _json_response(200, {"events": events})


def _register(event_id, email):
    email = email.strip()
    event = _get_event(event_id)
    if not event:
        return _json_response(404, {"error": "Event not found"})

    email_lower = email.lower()
    if DYNAMO_ENABLED:
        duplicates = table.query(
            IndexName="EmailEventIndex",
            KeyConditionExpression=Key("email").eq(email_lower) & Key("eventId").eq(event_id),
        ).get("Items", [])
        if duplicates:
            return _json_response(409, {"error": "You are already registered for this event."})

        _sync_event_counts()
        if event["registeredCount"] >= event["capacity"]:
            return _json_response(409, {"error": "This event is full."})

        registration_id = f"reg-{int(datetime.utcnow().timestamp() * 1000)}"
        item = {
            "registrationId": registration_id,
            "eventId": event_id,
            "eventName": event["name"],
            "email": email_lower,
            "status": "Confirmed",
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }
        table.put_item(Item=item)
        _sync_event_counts()
        return _json_response(201, {"message": "Registration successful", "registration": item})

    if any(reg["email"].lower() == email_lower and reg["eventId"] == event_id for reg in registrations.values()):
        return _json_response(409, {"error": "You are already registered for this event."})

    _sync_event_counts()
    if event["registeredCount"] >= event["capacity"]:
        return _json_response(409, {"error": "This event is full."})

    registration_id = f"reg-{len(registrations) + 1}"
    registration = {
        "registrationId": registration_id,
        "eventId": event_id,
        "eventName": event["name"],
        "email": email_lower,
        "status": "Confirmed",
    }
    registrations[registration_id] = registration
    _sync_event_counts()
    return _json_response(201, {"message": "Registration successful", "registration": registration})


def _get_registrations(email):
    email_lower = email.strip().lower()
    if DYNAMO_ENABLED:
        matches = table.query(
            IndexName="EmailEventIndex",
            KeyConditionExpression=Key("email").eq(email_lower),
        ).get("Items", [])
        return _json_response(200, {"registrations": matches})

    matches = [
        registration
        for registration in registrations.values()
        if registration["email"].lower() == email_lower
    ]
    return _json_response(200, {"registrations": matches})


def _cancel_registration(registration_id):
    if DYNAMO_ENABLED:
        response = table.delete_item(
            Key={"registrationId": registration_id},
            ReturnValues="ALL_OLD",
        )
        if not response.get("Attributes"):
            return _json_response(404, {"error": "Registration not found"})
        _sync_event_counts()
        return _json_response(200, {"message": "Registration cancelled"})

    if registration_id not in registrations:
        return _json_response(404, {"error": "Registration not found"})
    del registrations[registration_id]
    _sync_event_counts()
    return _json_response(200, {"message": "Registration cancelled"})


def lambda_handler(event, context):
    method = None
    path = None

    if isinstance(event, dict):
        method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
        path = event.get("rawPath") or event.get("path") or "/"

    if not method or not path:
        return _json_response(400, {"error": "Invalid request"})

    if method == "OPTIONS":
        return _json_response(200, {})

    if method == "GET" and path == "/events":
        return _list_events()

    if method == "POST" and path == "/register":
        try:
            body = json.loads(event.get("body", "{}") or "{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "Invalid JSON body"})

        event_id = body.get("eventId")
        email = body.get("email")
        if not event_id or not email:
            return _json_response(400, {"error": "eventId and email are required"})
        return _register(event_id, email)

    if method == "GET" and path.startswith("/registrations/"):
        email = unquote(path.split("/registrations/", 1)[1])
        return _get_registrations(email)

    if method == "DELETE" and path.startswith("/registration/"):
        registration_id = unquote(path.split("/registration/", 1)[1])
        return _cancel_registration(registration_id)

    return _json_response(404, {"error": "Route not found"})

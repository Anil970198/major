import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
import re

from core.email_service import get_credentials, load_settings

logger = logging.getLogger(__name__)


def list_availability(date_strs: List[str]) -> Dict[str, Any]:
    """Returns a list of events per date in structured format."""
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        availability = {}

        for date_str in date_strs:
            try:
                day = datetime.strptime(date_str, "%d-%m-%Y").date()
                start_of_day = datetime.combine(day, datetime.min.time()).isoformat() + "Z"
                end_of_day = datetime.combine(day, datetime.max.time()).isoformat() + "Z"

                events_result = service.events().list(
                    calendarId="primary",
                    timeMin=start_of_day,
                    timeMax=end_of_day,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()
                events = events_result.get("items", [])
                availability[date_str] = [
                    {
                        "summary": e.get("summary", "No Title"),
                        "start": convert_to_local(e["start"].get("dateTime", e["start"].get("date"))),
                        "end": convert_to_local(e["end"].get("dateTime", e["end"].get("date"))),
                    }
                    for e in events
                ] or "No events found"
            except Exception as e:
                logger.error(f"Error fetching events for {date_str}: {e}")
                availability[date_str] = "Error fetching events"

        return availability
    except HttpError as e:
        logger.error(f"Google API error: {e}")
        return {"error": str(e)}


def schedule_meeting(emails: List[str], title: str, start_time: str, end_time: str) -> Dict[str, Any]:
    """Schedules a meeting and returns the result including Meet link."""
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        settings = load_settings()
        timezone = settings.get("timezone", "Asia/Kolkata")
        creator_email = settings.get("monitored_email", "me")

        # Ensure creator is invited
        emails = list(set(emails + [creator_email]))

        event = {
            "summary": title,
            "start": {"dateTime": start_time, "timeZone": timezone},
            "end": {"dateTime": end_time, "timeZone": timezone},
            "attendees": [{"email": e} for e in emails],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": generate_request_id(title, start_time),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        result = service.events().insert(
            calendarId="primary",
            body=event,
            sendUpdates="all",
            conferenceDataVersion=1,
        ).execute()

        meet_link = result.get("hangoutLink")
        return {"success": True, "meet_link": meet_link, "event_id": result.get("id")}

    except Exception as e:
        logger.error(f"Error sending calendar invite: {e}")
        return {"success": False, "error": str(e)}


def convert_to_local(iso_str: str) -> str:
    settings = load_settings()
    tz = settings.get("timezone", "Asia/Kolkata")
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local_dt = dt.astimezone(pytz.timezone(tz))
        return local_dt.strftime("%Y-%m-%d %I:%M %p %Z")
    except Exception:
        return iso_str


def generate_request_id(title: str, dt_str: str) -> str:
    base = re.sub(r"\W+", "", title.lower())[:20]
    timestamp = dt_str.replace(":", "").replace("-", "").replace("T", "")[:12]
    return f"{base}-{timestamp}"

def add_calendar_reminder(title: str, start_time: str) -> Dict[str, Any]:
    """
    Creates a 30-minute Google Calendar event at the given time with popup/email reminder.
    Args:
        title: The title of the reminder event.
        start_time: ISO format (e.g. "2024-06-06T15:00:00") in local time zone.
    """
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)

        settings = load_settings()
        timezone = settings.get("timezone", "Asia/Kolkata")

        # Calculate 30-minute end time
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=30)

        event = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},   # 1 hour before
                    {"method": "popup", "minutes": 10}    # 10 minutes before
                ],
            },
        }

        event_result = service.events().insert(
            calendarId="primary",
            body=event,
            sendUpdates="none"
        ).execute()

        return {
            "success": True,
            "event_id": event_result.get("id"),
            "link": event_result.get("htmlLink")
        }

    except Exception as e:
        logger.error(f"Failed to create reminder event: {e}")
        return {"success": False, "error": str(e)}

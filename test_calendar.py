# test_calendar.py

from core.calendar_manager import get_events_for_days, send_calendar_invite
from datetime import datetime, timedelta

# 🔍 Test 1: Check Calendar Availability
print("📅 Checking availability...")
result = get_events_for_days({"date_strs": ["17-05-2025", "18-05-2025"]})
print(result)

# 📤 Test 2: Try Sending a Calendar Invite
print("\n📨 Sending test invite...")
start_time = (datetime.utcnow() + timedelta(hours=1)).replace(microsecond=0).isoformat()
end_time = (datetime.utcnow() + timedelta(hours=2)).replace(microsecond=0).isoformat()

success = send_calendar_invite(
    emails=["mondruanilkumar596@gmail.com"],  # Replace with your own test Gmail
    title="Test Meeting with AI Agent",
    start_time=start_time,
    end_time=end_time,
)

print("✅ Invite sent successfully!" if success else "❌ Failed to send invite.")

from typing import Dict, Any
from server.features.google_suite.gmail.gmail_tool import gmail_tool, EmailDraft, EmailAttachment, EmailFilterCriteria
from server.features.google_suite.calendar.calendar_tool import calendar_tool, CalendarEventDetail, CalendarAttendee
from server.features.google_suite.contacts.contacts_tool import contacts_tool, ContactFullRecord, ContactEmail, ContactPhoneNumber
from server.features.google_suite.classroom.classroom_tool import classroom_tool, ClassroomCourseFull, ClassroomAssignment
from server.features.google_suite.drive.drive_tool import drive_tool, DriveFileItem, DrivePermission

class GoogleSuiteSubagentMesh:
    def __init__(self) -> None:
        self.subagents = {
            "google_gmail": gmail_tool,
            "google_calendar": calendar_tool,
            "google_contacts": contacts_tool,
            "google_classroom": classroom_tool,
            "google_drive": drive_tool,
        }

    def dispatch_task(self, subagent_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if subagent_id == "google_gmail":
            if action == "send":
                draft = EmailDraft(**payload)
                return gmail_tool.send_email(draft)
            elif action == "draft":
                draft = EmailDraft(**payload)
                return gmail_tool.create_draft(draft)
            elif action == "search":
                criteria = EmailFilterCriteria(**payload)
                return gmail_tool.search_emails(criteria)
            elif action == "delete":
                return gmail_tool.delete_email(payload.get("message_id", ""))

        elif subagent_id == "google_calendar":
            if action == "schedule":
                evt = CalendarEventDetail(**payload)
                return calendar_tool.schedule_event(evt)
            elif action == "check_availability":
                return calendar_tool.check_availability(payload.get("start_time", ""), payload.get("end_time", ""))
            elif action == "cancel":
                return calendar_tool.cancel_event(payload.get("event_id", ""))
            return calendar_tool.list_upcoming_events(payload.get("limit", 10))

        elif subagent_id == "google_contacts":
            if action == "create":
                cnt = ContactFullRecord(**payload)
                return contacts_tool.create_contact(cnt)
            elif action == "find":
                return contacts_tool.find_contact(payload.get("query", ""))
            elif action == "delete":
                return contacts_tool.delete_contact(payload.get("contact_id", ""))
            return contacts_tool.list_all_contacts(payload.get("limit", 50))

        elif subagent_id == "google_classroom":
            if action == "create_course":
                crs = ClassroomCourseFull(**payload)
                return classroom_tool.create_course(crs)
            elif action == "assign":
                asg = ClassroomAssignment(**payload.get("assignment", {}))
                return classroom_tool.assign_homework(payload.get("course_id", ""), asg)
            elif action == "roster":
                return classroom_tool.get_course_roster(payload.get("course_id", ""))
            return classroom_tool.list_courses()

        elif subagent_id == "google_drive":
            if action == "upload":
                item = DriveFileItem(**payload.get("file", {}))
                return drive_tool.upload_file(item, payload.get("content_bytes", b""))
            elif action == "create_folder":
                return drive_tool.create_folder(payload.get("name", "Nuova Cartella"), payload.get("parent_id", "root"))
            elif action == "share":
                perm = DrivePermission(**payload.get("permission", {}))
                return drive_tool.share_file(payload.get("file_id", ""), perm)
            elif action == "delete":
                return drive_tool.delete_file(payload.get("file_id", ""))
            return drive_tool.list_files(payload.get("folder_id", "root"), payload.get("query", ""))

        return {"status": "error", "message": f"Subagente non riconosciuto: {subagent_id}"}

google_suite_mesh = GoogleSuiteSubagentMesh()

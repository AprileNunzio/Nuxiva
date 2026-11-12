import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ClassroomAssignment(BaseModel):
    assignment_id: str = ""
    title: str
    description: str = ""
    max_points: int = 100
    due_date: Optional[str] = None
    materials: List[str] = Field(default_factory=list)

class ClassroomCourseFull(BaseModel):
    course_id: str = ""
    name: str
    section: str = "A"
    description: str = ""
    room: str = ""
    enrollment_code: str = ""
    teacher_email: str = "teacher@google.edu"
    students_count: int = 0
    assignments: List[ClassroomAssignment] = Field(default_factory=list)

class ClassroomTool:
    def __init__(self) -> None:
        self.tool_id = "google_classroom_tool"
        self.name = "Google Classroom Expert"
        self._courses: Dict[str, ClassroomCourseFull] = {}

    def create_course(self, course: ClassroomCourseFull) -> Dict[str, Any]:
        cid = course.course_id or f"crs_{hashlib.sha256(course.name.encode()).hexdigest()[:12]}"
        course.course_id = cid
        if not course.enrollment_code:
            course.enrollment_code = cid[:6].upper()
        self._courses[cid] = course
        return {"status": "success", "course": course.model_dump()}

    def assign_homework(self, course_id: str, assignment: ClassroomAssignment) -> Dict[str, Any]:
        if course_id not in self._courses:
            return {"status": "error", "message": "Corso non trovato"}
        asg_id = assignment.assignment_id or f"asg_{hashlib.sha256((assignment.title + course_id).encode()).hexdigest()[:12]}"
        assignment.assignment_id = asg_id
        self._courses[course_id].assignments.append(assignment)
        return {"status": "success", "course_id": course_id, "assignment": assignment.model_dump()}

    def list_courses(self) -> Dict[str, Any]:
        items = list(self._courses.values())
        return {"status": "success", "count": len(items), "courses": [c.model_dump() for c in items]}

    def get_course_roster(self, course_id: str) -> Dict[str, Any]:
        if course_id not in self._courses:
            return {"status": "error", "message": "Corso non trovato"}
        c = self._courses[course_id]
        return {
            "status": "success",
            "course_id": course_id,
            "name": c.name,
            "students_count": c.students_count,
            "enrollment_code": c.enrollment_code,
            "assignments_count": len(c.assignments),
        }

classroom_tool = ClassroomTool()

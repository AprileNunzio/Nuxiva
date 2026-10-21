from server.shared.errors.domain_errors import NuxivaBaseException


class InvalidFrameException(NuxivaBaseException):
    def __init__(self, reason: str):
        super().__init__(
            message="Invalid camera frame",
            code="INVALID_FRAME",
            details={"reason": reason},
        )


class VisionUnavailableException(NuxivaBaseException):
    def __init__(self, reason: str):
        super().__init__(
            message="Vision analysis unavailable",
            code="VISION_UNAVAILABLE",
            details={"reason": reason},
        )


class SessionAccessException(NuxivaBaseException):
    def __init__(self, session_id: str):
        super().__init__(
            message="Workbench session not accessible",
            code="UNAUTHORIZED",
            details={"session_id": session_id},
        )

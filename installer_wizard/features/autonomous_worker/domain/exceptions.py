class AutonomousWorkerError(Exception):
    pass


class MissionNotFoundError(AutonomousWorkerError):
    pass


class MissionValidationError(AutonomousWorkerError):
    pass


class MissionStateError(AutonomousWorkerError):
    pass


class SpecialistExecutionError(AutonomousWorkerError):
    pass

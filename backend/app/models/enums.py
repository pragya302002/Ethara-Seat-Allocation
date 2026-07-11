import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    HR = "hr"
    PROJECT_MANAGER = "project_manager"
    EMPLOYEE = "employee"


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"
    NOTICE_PERIOD = "notice_period"


class SeatType(str, enum.Enum):
    STANDARD = "standard"
    STANDING_DESK = "standing_desk"
    CABIN = "cabin"
    MEETING_POD = "meeting_pod"
    ACCESSIBLE = "accessible"


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AllocationEventType(str, enum.Enum):
    ALLOCATE = "allocate"
    RELEASE = "release"
    TRANSFER = "transfer"
    RESERVE = "reserve"

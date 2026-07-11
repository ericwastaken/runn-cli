from dataclasses import dataclass
from typing import Optional

@dataclass
class Assignment:
    assignmentId: int
    personId: int
    projectId: int
    roleId: int
    minutesPerDay: int
    startDate: str
    endDate: str
    isBillable: bool
    isNonWorkingDay: bool
    note: Optional[str] = None
    phaseId: Optional[int] = None
    isPlaceholder: Optional[bool] = None
    workstreamId: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

@dataclass
class AssignmentCreate:
    personId: int
    projectId: int
    roleId: int
    startDate: str
    endDate: str
    minutesPerDay: int
    note: Optional[str] = None
    isBillable: Optional[bool] = None
    phaseId: Optional[int] = None
    workstreamId: Optional[int] = None
    isNonWorkingDay: bool = False

@dataclass
class Actual:
    actualId: Optional[int]
    personId: int
    projectId: int
    roleId: int
    date: str
    billableMinutes: int
    nonbillableMinutes: int
    billableNote: Optional[str] = None
    nonbillableNote: Optional[str] = None

@dataclass
class Project:
    projectId: int
    name: str

@dataclass
class Person:
    personId: int
    firstName: str
    lastName: str
    email: Optional[str]

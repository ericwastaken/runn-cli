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

@dataclass
class Actual:
    actualId: Optional[int]
    personId: int
    projectId: int
    roleId: int
    date: str
    billableMinutes: int
    nonbillableMinutes: int

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

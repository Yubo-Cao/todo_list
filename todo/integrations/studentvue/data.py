from datetime import datetime
from typing import NamedTuple
from decimal import Decimal

"""
This file contains the data models for the StudentVue API.
"""


class MeasureType(NamedTuple):
    """
    Measure type in the grade book for assignment.
    """

    id: int
    name: str
    weight: Decimal
    drop_scores: Decimal


class Assignment(NamedTuple):
    """
    Assignment in grade book
    """

    title: str
    points: Decimal
    points_possible: Decimal
    due_date: datetime
    unit: str
    measure_type: MeasureType
    excused: bool = False
    is_for_grading: bool = True
    is_done: bool = False


class Teacher(NamedTuple):
    """
    Teacher in the grade book.
    """

    name: str
    email: str


class Class(NamedTuple):
    """
    Class in grade book
    """

    name: str
    teacher: Teacher
    score: Decimal
    measure_types: list[MeasureType]
    assignments: list[Assignment]


class Student(NamedTuple):
    """
    Student in grade book
    """

    name: str
    gpa: Decimal
    classes: list[Class]

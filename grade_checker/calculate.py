from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as dates

from dateutil import tz
from itertools import chain
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from grade_checker.db import Course, Grade, connection
from grade_checker.logger import logger

today = datetime.utcnow()
start_of_day_timestamp = datetime(
    today.year, today.month, today.day, tzinfo=tz.tzutc()
).timestamp()


def calculate_unweighted_avg(na=100, semester=None, ts=start_of_day_timestamp):
    cursor = connection.cursor()
    res = cursor.execute(
        f"""
                   SELECT AVG(IIF(grade <> -1, grade, ?))
                   FROM grade
                   WHERE {'''(
                       SELECT semester
                       FROM course
                       WHERE course.id=grade.course_id
                   ) = ? AND ''' if semester else ''}ts = ?
                   """,
        (na, semester, ts) if semester else (na, ts),
    ).fetchone()[0]
    cursor.close()
    return res


def calculate_weighted_avg(na=100, semester=None, ts=start_of_day_timestamp):
    cursor = connection.cursor()
    res = cursor.execute(
        f"""SELECT
                    AVG(
                        IIF (
                            g.grade <> - 1,
                            IIF ( c.name LIKE '%ap%', g.grade + 10, g.grade ),
                            IIF ( c.name LIKE '%ap%', ? + 10, ? )
                        ) 
                    ) 
                FROM
                    grade AS "g"
                    JOIN course AS "c" ON c.id = g.course_id 
                WHERE
                    {"c.semester = ? AND" if semester else ""} ts = ?;""",
        (na, na, semester, ts) if semester else (na, na, ts),
    ).fetchone()[0]
    cursor.close()
    return res


def calculate_weighted_avg_html(na=100, semester=None, ts=start_of_day_timestamp):
    cursor = connection.cursor()
    res = cursor.execute(
        f"""SELECT
                    AVG(
                        IIF (
                            g.grade <> - 1,
                            IIF ( g.course_id LIKE '%ap%', g.grade + 10, g.grade ),
                            IIF ( g.course_id LIKE '%ap%', ? + 10, ? )
                        ) 
                    ) 
                FROM
                    grade AS "g"
                WHERE
                    ts = ?;""",
        (na, na, semester, ts) if semester else (na, na, ts),
    ).fetchone()[0]
    cursor.close()
    return res


def find_grade_with_semester(semester):
    cursor = connection.cursor()
    res = (
        [
            Grade(*data)
            for data in cursor.execute(
                """SELECT * FROM grade WHERE (SELECT semester FROM course WHERE
                   course.id = grade.course_id) = ?""",
                (semester,),
            ).fetchall()
        ]
        if semester
        else Grade.find()
    )
    cursor.close()
    return res


def stack_plot(master, na=100, semester=2):
    cursor = connection.cursor()
    courses = Course.find(semester=semester)
    result = {}
    # find most common length/amount of grades get from Sqlite Query
    node_count = {}

    for course in courses:
        exists = result.setdefault(course.name, [])
        results = list(
            chain(
                *cursor.execute(
                    """SELECT IIF(g.grade <> -1, g.grade, ?) 
                            FROM grade AS "g"
                            WHERE g.course_id=?
                            ORDER BY g.ts ASC""",
                    (
                        na,
                        course.id,
                    ),
                ).fetchall()
            )
        )
        node_count[len(results)] = node_count.get(len(results), 0) + 1
        if not exists:
            exists.extend(results)
        else:
            # Handle the case where the course has too much grade, i.e., quarter
            # In that case, the grade that are shorter is assumed to be second quarter
            # However, if they equal, then just take average directly
            if results:
                logger.info("Too much grade for {}".format(course.name))
                first_quarter, second_quarter = (
                    (exists, results)
                    if len(results) < len(exists)
                    else (results, exists)
                )
                result[course.name] = list(
                    map(
                        lambda a, b: (a + b) / 2,
                        first_quarter,
                        first_quarter[: len(first_quarter) - len(second_quarter)]
                        + second_quarter,
                    )
                )

    result = {
        k: v
        for k, v in result.items()
        if v
        and len(v) == max(node_count, key=node_count.get)
        or logger.info(f"Dropped grade {k}")  # only take the most common length
    }

    timestamps = [
        dates.date2num(datetime.fromtimestamp(ts))
        for ts in chain(
            *cursor.execute(
                """SELECT DISTINCT ts
                     FROM grade
                     ORDER BY ts"""
            ).fetchall()
        )
    ]
    cursor.close()

    fig, ax = plt.subplots(1, 1)
    ax.stackplot(
        timestamps,
        *result.values(),
        labels=result.keys(),
        colors=plt.cm.get_cmap("Blues")(np.linspace(0, 1, len(result))),
    )

    ax.get_xaxis().set_major_formatter(dates.DateFormatter("%Y-%m-%d"))
    ax.get_xaxis().set_major_locator(dates.AutoDateLocator())

    ax.set_ylabel("Time", fontsize=10)
    ax.set_xlabel("Grade", fontsize=10)

    fig.legend(loc="upper right")
    fig.autofmt_xdate()

    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()

    return canvas.get_tk_widget()


def get_latest_grade_change():
    cursor = connection.cursor()
    res = cursor.execute(
        "SELECT * FROM grade_change ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    cursor.close()
    return res

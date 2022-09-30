import atexit
import functools
import json
import re
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from itertools import chain
from operator import itemgetter
from typing import Any, Callable, Dict, Iterable, List, Match, Tuple, cast
from urllib import error
from urllib.parse import parse_qs

import requests
from dateutil import tz
from lxml import etree
from pyquery import PyQuery as pq
from requests.models import Response

from grade_checker.config import cfg
from grade_checker.db import Course, Grade, Navigation, Teacher
from grade_checker.logger import logger

session = requests.session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Referer": "https://publish.gwinnett.k12.ga.us/",
    }
)
cookies = MozillaCookieJar(str(cfg.grade_checker.cookies_path))
session.cookies = cookies
session.hooks = {"response": lambda r, *args, **kwargs: r.raise_for_status()}
atexit.register(session.close)


def try_again(*on_fail: Callable) -> Any:
    """
    The try_again function is a decorator that wraps the decorated function with
    a try-except block. If an exception is raised, it will be caught and logged.


    :param on_fail:Callable|Sequence[Callable]: Specify the action to take when an error occurs
    :return: The result of the function
    """

    def _deco(func):
        @functools.wraps(func)
        def _impl(*args, **kwargs):
            first_time = True
            while True:
                try:
                    return func(*args, **kwargs)
                except (error.HTTPError, requests.HTTPError) as e:
                    logger.error(
                        f"""Failed to execute methods {func.__name__}. 
HTTPError: return code {e.code} because {e.reason}. 
HTTPHeader: {e.headers}""",
                        exc_info=True,
                    )
                except error.URLError as e:
                    logger.error(
                        f"""Failed to execute method {func.__name__}.
URLError is raised because {e.reason}""",
                        exc_info=True,
                    )
                except (OSError, AttributeError) as e:
                    logger.error(
                        f"""Unknown IO error while executing {func.__name__}.
{e!r}""",
                        exc_info=True,
                    )
                except Exception as e:
                    logger.error(f"{e!r}", exc_info=True)
                if first_time:
                    for f in on_fail:
                        logger.debug(
                            f"Trying to execute on_fail function {f.__name__}."
                        )
                        try:
                            f(*args, **kwargs)
                        except Exception as e:
                            logger.error(
                                f"Failed to execute on_fail function {f.__name__}.",
                                exc_info=True,
                            )
                        else:
                            logger.debug(f"on_fail function {f.__name__} succeeds.")
                    first_time = False
                else:
                    logger.error(
                        f"Failed to execute method {func.__name__}, on_fail operation failed."
                    )
                    raise Exception()

        return _impl

    return _deco


def login_to_sso(
    session: requests.Session,
    username=cfg.grade_checker.get("username", ""),
    password=cfg.grade_checker.get("password", ""),
    *args,
    **kwargs,
) -> None:
    """
    It logs into the SSO (Single Sign On/Eclass) system and save cookies.

    :param session: requests.Session()
    :type session: requests.Session
    :param _first: This is a boolean that is used to determine if the function is being called for the
    first time, defaults to True (optional)
    """
    logger.debug("Try to login to eclass. Cookies has expired.")
    try:
        response = session.post(
            "https://apps.gwinnett.k12.ga.us/pkmslogin.form",
            data={
                "forgotpass": "p0/IZ7_3AM0I440J8GF30AIL6LB453082=CZ6_3AM0I440J8GF30AIL6LB4530G6=LA0=OC=Eaction!ResetPasswd==/#Z7_3AM0I440J8GF30AIL6LB453082",
                # TODO: Understand what is that. Bug may arise due to that.
                "login-form-type": "pwd",
                "username": username,
                "password": password,
            },
        )
        cast(MozillaCookieJar, session.cookies).save(
            ignore_discard=True, ignore_expires=True
        )
        return response
    except error.HTTPError as e:
        logger.error(f"Error while try to login to eclass.")
    except error.URLError as e:
        print(e.reason)


@try_again(login_to_sso)
def login_to_saml(session, *args, **kwargs) -> None:
    """
    It goes to the student VUE page, then it goes to the SAML page, then it SAML xml
    data to VUE as to obtain cookies for login later.

    :param session: the session object that you created earlier
    """

    logger.debug("Try to obtain SAML cookies. Cookies has expired.")

    # go to student VUE -- SP
    student_vue_url = (
        pq(session.get("https://apps.gwinnett.k12.ga.us/dca/student/dashboard").text)
        .find("li:first-child .app-button")
        .attr("href")
    )

    # 402 jump to SAML -- ISP
    session.headers["Referer"] = "https://apps.gwinnett.k12.ga.us/dca/student/dashboard"
    response = session.get(student_vue_url)

    # prepare data by extracting html page
    saml_xml = etree.HTML(response.text.encode("utf-8"))

    # before we go, change referer
    session.headers["Referer"] = response.url

    # send the data to ISP to obtain cookies
    session.post(
        "https://apps.gwinnett.k12.ga.us/spvue/SamlAssertionConsumer.aspx",
        data={
            "RelayState": (d := saml_xml.xpath("//input/@value"))[0],
            "SAMLResponse": d[1],
        },
    )

    session.get(
        "https://apps.gwinnett.k12.ga.us/spvue/PXP2_ClassSchedule.aspx"
    )  # with cookies, go back to SP -- Course Schedule

    cast(MozillaCookieJar, session.cookies).save(
        ignore_discard=True, ignore_expires=True
    )


def parse_navigation(schedule_html: str) -> List[Navigation]:
    """
    It finds the first occurrence of the string `PXP.NavigationData =` in the response
    text, then it parse javascript object declared after it to dict.

    :param schedule_response: The response from the schedule page
    :type schedule_response: requests.Response
    :return: A dictionary of the navigation items.
    """

    try:
        index = (
            cast(
                Match,
                re.search(
                    r"PXP\.NavigationData\s*=\s*(?=\{)", schedule_html, re.MULTILINE
                ),
            ).end()
            + 1
        )
    except AttributeError as e:
        raise ValueError("Invalid html is given") from e
    start = index - 1
    stack = ["{"]
    while len(stack):
        match (schedule_html[index]):
            case ("{" | "[") as l:
                stack.append(l)
            case ("]" | "}") as r:
                match (r):
                    case "}":
                        assert stack.pop() == "{"
                    case "]":
                        assert stack.pop() == "["
        index += 1

    return [
        Navigation(item["description"], item["url"])
        for item in json.loads(schedule_html[start:index])["items"]
    ]


def parse_schedule(
    semester_responses: List[Tuple[int, List[Dict[str, Dict[str, str] | str]]]]
) -> Tuple[Iterable[Course], Iterable[Teacher]]:
    return cast(
        Tuple[Iterable[Course], Iterable[Teacher]],
        tuple(
            map(
                set,
                map(
                    chain,
                    *(
                        parse_one_schedule(one_semester_response)
                        for one_semester_response in semester_responses
                    ),
                ),
            )
        ),
    )


def parse_one_schedule(
    semester_courses: Tuple[int, List[Dict[str, Dict[str, str] | str]]]
) -> Tuple[Iterable[Course], Iterable[Teacher]]:
    """
    It takes a tuple of a semester number and a list of courses, and returns a tuple of a set of courses
    and a set of teachers

    :param semester_courses: Tuple[int, List[Dict[str, Dict[str, str] | str]]]
    :type semester_courses: Tuple[int, List[Dict[str, Dict[str, str] | str]]]
    :return: A tuple of two iterables, one of Course objects and one of Teacher objects.
    """

    semester, courses = semester_courses

    course_table = set(
        [
            Course(
                id=course["ID"],
                semester=semester,
                year=datetime.now().year,
                period=course["Period"],
                name=cast(str, course["CourseTitle"]).title(),
                room=course["RoomName"],
                teacher_id=cast(Dict[str, str], course["Teacher"])["sgu"],
            )
            for course in courses
        ]
    )
    teacher_table = set(
        [
            Teacher(
                id=teacher["sgu"],
                name=teacher["teacherName"],
                email=teacher["email"],
            )
            for teacher in map(itemgetter("Teacher"), courses)
        ]
    )
    return course_table, teacher_table


def get_schedule_data(
    session, one=False
) -> Tuple[Iterable[Response], Iterable[Tuple[int, Iterable[Response]]]]:
    one_schedule_html_response, one_schedule_data_response = _get_one_schedule_data(
        session
    )
    dom = pq(one_schedule_html_response.text)
    result_html: List[Response] = [one_schedule_html_response]
    result_data: List[Tuple[int, List[Response]]] = [
        (
            _parse_semester(
                dom.find(
                    '.heading_breadcrumb ul li.selected:contains("Semester")'
                ).text()
            ),
            one_schedule_data_response,
        )
    ]
    if not one:
        for a in dom.find(
            '.heading_breadcrumb ul li:contains("Semester"):not(.selected) a'
        ).items():
            (
                one_schedule_html_response,
                one_schedule_data_response,
            ) = _get_one_schedule_data(
                session, "https://apps.gwinnett.k12.ga.us/spvue/" + a.attr("href")
            )
            result_html.append(one_schedule_html_response)
            result_data.append((_parse_semester(a.text()), one_schedule_data_response))
    return result_html, result_data


@try_again(login_to_sso, login_to_saml)
def _get_one_schedule_data(
    session, url="https://apps.gwinnett.k12.ga.us/spvue/PXP2_ClassSchedule.aspx"
):
    """
    It goes to the schedule page, gets the data store parameters, and then uses those parameters to make
    a request to the server for the schedule data (fake ajax)

    :param session: the session object that contains the cookies
    :return: A JSON object with the schedule data.
    """

    schedule_html_response = session.get(
        url
    )  # with cookies, go back to SP -- Course Schedule

    # change referer
    session.headers["Referer"] = schedule_html_response.url

    # prepare payload
    data_store_params = re.search(
        r"new DevExpress.PXPRemoteDataStore\((.*?),\s*(.*?)\)",
        schedule_html_response.text,
        re.MULTILINE,
    )

    # prepare payload to get schedule data
    payload = {
        "request": {
            "agu": re.search(
                r"PXP\.AGU\s*=\s*(.*?);?$", schedule_html_response.text, re.MULTILINE
            )
            .group(1)
            .strip("'\""),
            "dataRequestType": "Load",
            "gridParameters": data_store_params.group(2).strip("'\""),
            "dataSourceTypeName": data_store_params.group(1).strip("'\""),
            "loadOptions": {
                "requireTotalCount": True,
                "searchOperation": "contains",
                "searchValue": None,
                "skip": 0,
                "take": 15,
                "sort": None,
                "group": None,
            },
        }
    }

    schedule_data_response = session.post(
        "https://apps.gwinnett.k12.ga.us/spvue/service/PXP2Communication.asmx/DXDataGridRequest",
        json=payload,
        headers={"X-Requested-With": "XMLHttpRequest"},  # ajax headers
    )

    return schedule_html_response, schedule_data_response


@try_again(login_to_sso, login_to_saml)
def get_grade_book(session: requests.Session, relative_path: str) -> Iterable[Response]:
    """
    The get_grade_book function retrieves the grade book for each semester. It does
    this by first navigating to the Grade Book page, and then parsing out all of the
    available semesters from a dropdown menu on that page. For each available semester,
    a response which requests its own inner html is returned.

    :param session: Maintain the session
    :return: A list of responses
    """
    grade_book_url = "https://apps.gwinnett.k12.ga.us/spvue/" + (
        grade_book_query := relative_path
    )

    # send requests
    response = session.get(grade_book_url)

    # change referer
    session.headers["Referer"] = grade_book_url

    # by default, current semester's grade is displayed
    # we want all school year

    # parse document to prepare ajax parameters
    dom = pq(response.text)

    result: List[Response] = []
    for panel in dom.find(".pxp-panel .update-panel").items():
        for available_semester in panel("ul.dropdown-menu>li").items():
            # semester_number = int(re.search(r"\d+", available_semester.text()).group(0))

            payload = {
                "request": {
                    "control": "Gradebook_SchoolClasses",
                    "parameters": {
                        "gradePeriodGU": available_semester("a").attr("data-period-id"),
                        "GradingPeriodGroup": available_semester("a").attr(
                            "data-period-group"
                        ),
                        "schoolID": panel.attr("data-school-id"),
                        "OrgYearGU": panel.attr("data-orgyear-id"),
                        "AGU": parse_qs(grade_book_query.split("?", 1)[1])["AGU"][0],
                    },
                }
            }

            response = session.post(
                "https://apps.gwinnett.k12.ga.us/spvue/service/PXP2Communication.asmx/LoadControl",
                json=payload,
            )

            result.append(response)
    if len(result) == 0:
        raise OSError("Failed to obtain any useful info.")
    return result


def parse_grade_book(
    responses: Iterable[str],
    rendered: bool = False,
) -> Iterable[Grade]:
    """
    The parse_grade_book function takes a list of requests.Response objects and returns
    a dictionary mapping the semester number to a dictionary mapping course names to grades.


    :param responses:Iterable[Response]: Get the html of the gradebook
    :param rendered:bool=False: Specify if the responses are manually downloaded html
    :return: A dictionary of dictionaries
    """

    result: List[Grade] = []
    courses = Course.len()
    today = datetime.utcnow()
    start_of_day_timestamp = datetime(
        today.year, today.month, today.day, tzinfo=tz.tzutc()
    ).timestamp()
    year = datetime.now().year

    for dom in map(pq, responses):

        try:
            semester = _parse_semester(
                dom.find(
                    '.term-selector button[data-toggle="dropdown"] .current'
                ).text()
            )
        except AttributeError as e:
            raise ValueError("Invalid html is given.") from e

        # assert semester_number == expected_semester_number
        # Uncomment pass expected_semester_number if one want to make sure semester_number
        # is as expected.

        table = dom.find(".pres-table>div:nth-child(2)")
        divs = list(table.children("div").items())

        classes = list(
            # div:nth-child(2n) would work. but it make parsing more difficult
            zip(divs[::3], divs[1::3])
            if rendered
            else zip(
                divs[::2],
                divs[1::2],
            )
        )

        result += [
            Grade(
                ts=start_of_day_timestamp,
                grade=float(mark) if (mark := body(".mark").text()) != "N/A" else -1,
                course_id=Course.find_one(
                    name=header(".course-title")
                    .text()
                    .split(": ", 1)[1]
                    .strip()
                    .title(),
                    semester=semester,
                    year=year,
                ).id
                if courses
                else header(".course-title").text().split(": ", 1)[1].strip().title(),
            )
            for header, body in classes
        ]

    return set(result)


def _parse_semester(text: str) -> int:
    # get identifier of semester. 1 = first semester, 2 = second semester, and
    # so on. being old and lazy, nobody can make me write enum (hahaha)
    # notice, quarter exists for Geo-Precal students. Hence, we normalize them to 1
    # or 2

    try:
        ordinal_numbers = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
            "sixth": 6,
            "seventh": 7,
            "eigth": 8,
            "ninth": 9,
            "tenth": 10,
        }
        text = text.casefold()
        for k, v in ordinal_numbers.items():
            text = text.replace(k, str(v))
        semester_match = cast(
            Match,
            re.search(
                r"(quarter|smester)?\s*(\d+)\s*(quarter|semester)?",
                text,
            ),
        )
        semester_number = int(semester_match.group(2))
        if semester_match.group(1) == "quarter":
            # 1 -> 1, 2 -> 1, 3 -> 2, 4 -> 2
            semester_number = (semester_number + 1) // 2
        return semester_number
    except AttributeError as e:
        raise ValueError(f"Invalid string {text}.") from e


@try_again(
    lambda *args: fetch_teacher_course_data(checked=False),
    lambda *args: fetch_navigation_data(checked=False),
)
def refresh_db():
    """
    The refresh_db function refreshes the grade_checker data.

    It does this by logging into e-class, and then parsing the schedule and grade book pages for their respective data.
    The function also parses the navigation bar to go to grade book.

    :return: The schedule data
    """
    try:
        fetch_teacher_course_data(session)
        fetch_navigation_data(session)
        fetch_grade_book_data(session)
    finally:
        session.close()


def fetch_navigation_data(session=session, checked=True):
    # DATA: navigation
    logger.debug("Scrape navigation data.")
    if not checked or not Navigation.len():
        schedule_html_responses, _ = get_schedule_data(session, one=True)
        navigation_data = parse_navigation(
            schedule_html_responses[0].text
        )  # Since navigations are same across semesters
        return navigation_data
    return Navigation.find()


def fetch_teacher_course_data(session=session, checked=True):
    # DATA: schedule & teacher
    logger.debug("Scrape schedule and teacher data.")
    if not checked or not Teacher.len() or not Course.len():
        _, schedule_data_responses = get_schedule_data(session)

        semesters_responses = [
            (semester, schedule_data_response.json()["d"]["Data"]["data"])
            for semester, schedule_data_response in schedule_data_responses
        ]
        for course in chain(*map(itemgetter(1), semesters_responses)):
            course["Teacher"] = json.loads(course["Teacher"])

        course_table, teacher_table = parse_schedule(
            semesters_responses
        )  # automatically stored
        return course_table, teacher_table
    return Course.find(), Teacher.find()


def validate_username_password(username, password, session=session) -> None:
    response = login_to_sso(session, username, password)
    return response.text.find("error") == -1


@try_again(
    lambda *args: fetch_teacher_course_data(checked=False),
    lambda *args: fetch_navigation_data(checked=False),
)
def fetch_grade_book_data(session=session):
    # DATA: grade_book
    logger.debug("Scrape grade book data.")
    grade_book_data_response = get_grade_book(
        session, Navigation.find_one(name="Grade Book").url
    )

    htmls = [
        # ajax return json
        response.json()["d"]["Data"]["html"]
        for response in grade_book_data_response
    ]

    grade_book_table = parse_grade_book(htmls)
    logger.debug(f"Parsed {len(grade_book_table)} grades.")
    return grade_book_table


def parse_grade_from_html(html):
    panels = pq(html).find(".update-panel")
    data = parse_grade_book([node.outer_html() for node in panels.items()], True)
    return data


if __name__ == "__main__":
    fetch_grade_book_data()

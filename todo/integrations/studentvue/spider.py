import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

import aiohttp
import pyparsing as pp
from async_property import async_cached_property
from lxml import etree
from yarl import URL

from todo.error import SpiderError
from todo.integrations.spider import *
from todo.integrations.studentvue.data import (
    MeasureType,
    Assignment,
    Teacher,
    Class as ClassData,
)
from todo.utils import find_kv

logger = logging.getLogger(__name__)


class EClass(Retry, instance_name="e_class"):
    def __init__(
        self,
        manager: SessionManager,
        navigator: Navigator,
        username: str,
        password: str,
    ):
        """
        E-class student integrations.

        :param manager: Session manager.
        :param navigator: Navigator.
        """

        super().__init__(manager, navigator)
        self.username = username
        self.password = password

    @SessionManager.supply
    async def login(self, session) -> None:
        """
        Login to StudentVue.
        """

        logger.debug("Logging in to E-Class")
        async with session.post(
            "https://apps.gwinnett.k12.ga.us/pkmslogin.form",
            data={
                "username": self.username,
                "password": self.password,
                "forgotpass": "p0/IZ7_3AM0I440J8GF30AIL6LB453082=CZ6_3AM0I440J8GF30AIL6LB4530G6=LA0=OC=Eaction!ResetPasswd==/#Z7_3AM0I440J8GF30AIL6LB453082",
                "login-form-type": "pwd",
            },
        ) as resp:
            SpiderError.check_response(resp, "Failed to login.")
            error = etree.HTML(await resp.text()).xpath(
                "//meta[contains(@content, 'error')]/@content"
            )
            if error:
                raise SpiderError(
                    f"Login failed. Error code = {URL(error[0].split('URL=')[1]).query.get('error', None)}",
                    resp.url,
                )

    @SessionManager.supply
    async def load_nav(self, session):
        """
        Load the navigation page, jump tables, etc.
        """

        logger.debug("Loading navigation page")

        # implicit conversion from str to Navigator during assignment
        self.nav.dashboard: Navigator = "https://apps.gwinnett.k12.ga.us/dca/student/dashboard"  # type: ignore
        async with session.get(self.nav.dashboard.url) as resp:
            SpiderError.check_response(resp, "Failed to load dashboard.")
            tree = etree.HTML(await resp.text())
            buttons = tree.xpath('//*[@id="apps"]//li//a')
            self.nav.add_all(
                {
                    "".join(button.itertext()).lower(): button.xpath("@href")[0]
                    for button in buttons
                }
            )


class StudentVue(Retry, instance_name="student_vue"):
    def __init__(self, manager: SessionManager, navigator: Navigator, e_class: EClass):
        super().__init__(manager, navigator)
        self.e_class = e_class

    @EClass.retry
    @SessionManager.supply
    async def login(self, session):
        """
        Login to StudentVue.
        """

        logger.debug("Logging in to StudentVue")
        async with session.get(self.nav.my_studentvue.url) as resp:
            assert resp.ok
            text = await resp.text()

        tree = etree.HTML(text.encode("utf-8"))
        params = dict(zip(*[tree.xpath("//input/@%s" % i) for i in ["name", "value"]]))
        url = tree.xpath("//form/@action")[0]

        async with session.post(url, data=params) as resp:
            SpiderError.check_response(resp, "Failed to login to studentVUE.")
            self.nav.my_studentvue.start = resp.url

    @EClass.retry
    @SessionManager.supply
    async def load_nav(self, session):
        logger.debug("Loading StudentVue navigation")
        self.nav.my_studentvue.load_control = (
            "service/PXP2Communication.asmx/LoadControl"
        )
        async with session.get(self.nav.my_studentvue.start.url) as resp:
            SpiderError.check_response(resp, "Failed to load studentVUE.")
            text = await resp.text()

            tree = etree.HTML(text.encode("utf-8"))
            js = tree.xpath("//script/text()")[0]
            items = JSParser(js)["PXP.NavigationData"]["items"]

            self.nav.my_studentvue.add_all(
                {item["description"]: item["url"] for item in items}
            )

    @EClass.retry
    @SessionManager.supply
    async def post(self, path, data, *, xhr=True, session=None):
        headers = {"CURRENT_WEB_PORTAL": "StudentVUE"}
        if xhr:
            headers["X-Requested-With"] = "XMLHttpRequest"

        async def impl():
            async with session.post(
                self.nav.my_studentvue.start.url.join(URL(path)),
                json=data,
                headers=headers,
            ) as resp:
                SpiderError.check_response(resp, "Failed to post to studentVUE.")
                return await resp.json()

        task = asyncio.create_task(impl())
        return await task

    @EClass.retry
    async def load_control(self, name, params):
        data = await self.post(
            self.nav.my_studentvue.load_control.url,
            {"request": {"control": name, "parameters": params}},
        )
        if error := data["d"]["Error"]:
            raise SpiderError(error, self.nav.my_studentvue.load_control.url)
        return data["d"]["Data"]


class GradeBook(Spider):
    def __init__(
        self,
        manager: SessionManager,
        navigator: Navigator,
        student_vue: StudentVue,
    ):
        """
        Grade book integrations.

        :param manager: the session manager.
        :param navigator: the navigator.
        :param student_vue: the studentvue integrations.
        """
        super().__init__(manager, navigator)
        self.student_vue = student_vue

    @StudentVue.retry
    @SessionManager.supply
    async def visit(self, session: aiohttp.ClientSession):
        """
        Visit the grade book.
        """
        logger.debug("Visiting grade book")
        async with session.get(self.nav.my_studentvue.grade_book.url) as resp:
            SpiderError.check_response(resp, "Failed to load grade book.")
            text = await resp.text()

            tree = etree.HTML(text.encode("utf-8"))
            js = tree.xpath("//script/text()")[0]
            parser = JSParser(js)

            self.school = parser["PXP.GBFocusData"]["Schools"][0]
            self.agu = parser["PXP.AGU"]
            self.periods = self.school["GradingPeriods"]
            self.default_period = [
                period for period in self.periods if period["defaultFocus"]
            ][0]

    @StudentVue.retry
    async def get_classes_per_semester(
        self, period: dict[str, str] = None
    ) -> list[dict]:
        """
        Get all classes for a semester.

        :param period: A period from self.periods
        :return: A list of parameters to load a class.
        """

        if period is None:
            period = self.default_period
        logger.debug(f"Getting classes for {period.get('Name', 'NA')}")

        grading_period_group = period["GroupName"]
        grade_period_gu = period["GU"]
        org_year_gu = period["OrgYearGU"]
        params = {
            "gradePeriodGU": grade_period_gu,
            "GradingPeriodGroup": grading_period_group,
            "schoolID": self.school["SchoolID"],
            "OrgYearGU": org_year_gu,
            "AGU": self.agu,
        }
        data = await self.student_vue.load_control("Gradebook_SchoolClasses", params)
        html = data["html"]

        tree = etree.HTML(html.encode("utf-8"))
        table = tree.xpath('//div[contains(@class, "table")]')[0]
        table.remove(table.xpath('//div[contains(@class, "table-header")]')[0])
        rows = [
            json.loads(row)
            for row in table.xpath(
                './div/div[contains(@class, "row") and contains(@class, "header")]//button/@data-focus'
            )
        ]
        return rows

    @StudentVue.retry
    async def get_classes(self) -> dict[str, list[dict]]:
        """
        Get all classes for all semesters.

        :return: a dictionary of semester names to a list of parameters to
            load a class.
        """

        logger.debug("Getting all classes")
        return dict(
            zip(
                [period["Name"] for period in self.periods],
                await asyncio.gather(
                    *[self.get_classes_per_semester(period) for period in self.periods]
                ),
            )
        )

    @StudentVue.retry
    async def get_default_classes(self) -> list[dict]:
        """
        Get all classes for the default semester.

        :return: A list of parameters to load a class.
        """

        return await self.get_classes_per_semester()

    classes = async_cached_property(get_classes)
    default_classes = async_cached_property(get_default_classes)


class Class(Spider):
    """
    Represents a class in the grade book. Notice this class
    only take care about 1 semester/quarter/grading period.
    """

    current_class_id: int = None

    def __init__(
        self,
        manager: SessionManager,
        navigator: Navigator,
        studentvue: StudentVue,
        load_params: dict,
    ):
        """
        Class integrations.

        :param manager: the session manager.
        :param navigator: the navigator.
        :param studentvue: the studentvue integrations.
        :param load_params: the parameters to load this class, obtained from GradeBook class.
        """

        super().__init__(manager, navigator)
        self.studentvue = studentvue
        self.load_params = load_params

    @property
    def class_id(self):
        return self.load_params["FocusArgs"]["classID"]

    @property
    def mark_period_gu(self):
        return self.load_params["FocusArgs"]["markPeriodGU"]

    @property
    def grade_period_gu(self):
        return self.load_params["FocusArgs"]["gradePeriodGU"]

    @async_cached_property
    async def measure_types(self) -> list[MeasureType]:
        """
        Measure types in the class.
        """

        await self._ensure_meta()
        return [
            MeasureType(
                id=data["id"],
                name=data["name"],
                weight=Decimal(data["weight"]),
                drop_scores=Decimal(data["dropScores"]),
            )
            for data in self._meta["measureTypes"]
        ]

    @async_cached_property
    async def assignment_count(self) -> int:
        """
        Number of assignments in the class.
        """
        await self._ensure_meta()
        return self._meta["classGrades"][0]["assignmentCount"]

    @async_cached_property
    async def upcoming_assignment_count(self) -> int:
        """
        Number of upcoming assignments in the class.
        """

        await self._ensure_assignments_counts()
        return int(
            next(
                filter(
                    lambda dct: dct["type"] == "upcoming",
                    self._assignments_counts["cards"],
                )
            )["count"]
        )

    @async_cached_property
    async def missing_assignment_count(self) -> int:
        """
        Number of missing assignments in the class.
        """

        await self._ensure_assignments_counts()
        return int(
            next(
                filter(
                    lambda dct: dct["type"] == "missing",
                    self._assignments_counts["cards"],
                )
            )["count"]
        )

    @async_cached_property
    async def score(self) -> Decimal:
        """
        Not exact score. Same as reported in the website.
        """
        await self._ensure_meta()
        return Decimal(self._meta["classGrades"][0]["totalWeightedPercentage"])

    @async_cached_property
    async def assignments(self) -> list[Assignment]:
        """
        Get all assignments in the class.
        """
        await self._ensure_assignments()
        results = []

        for assign in self._assignments["responseData"]["data"]:
            if not (assign["showAssignmentGrade"] and assign["points"]):
                continue
            meta = (
                find_kv(
                    await self.assignment_metas,
                    "gradeBookId",
                    assign["itemID"],
                    "Meta data not found for assignment %s" % assign["itemID"],
                )
                or {}
            )
            measure_type = (
                find_kv(
                    await self.measure_types,
                    "id",
                    meta.get("measureTypeId"),
                    "MeasureType for assignment %s not found" % assign["itemID"],
                )
                or {}
            )
            results.append(
                Assignment(
                    title=assign.get("title"),
                    points=Decimal(assign.get("points", "-1")),
                    points_possible=Decimal(assign.get("pointsPossible", "-1")),
                    due_date=datetime.fromisoformat(
                        assign.get("due_date", datetime.now().isoformat())
                    ),
                    unit=meta.get("unit") or assign.get("unit"),
                    measure_type=measure_type,
                    excused=meta.get(
                        "excused", False
                    ),  # if assignment can't be scraped, treat it as excused
                    is_for_grading=meta.get("isForGrading", False),
                    is_done=bool(assign.get("isDone", False)),
                )
            )

        return results

    @async_cached_property
    async def exact_score(self) -> Decimal:
        """
        Exact score. Not same as reported in the website.
        """
        assignments: list[Assignment] = await self.assignments
        assignments = [
            assign
            for assign in assignments
            if assign.is_for_grading and not assign.excused
        ]
        grouper: dict[MeasureType, list[Assignment]] = {}
        for assign in assignments:
            grouper.setdefault(assign.measure_type, []).append(assign)
        score = sum(
            sum(
                (assign.points - assign.measure_type.drop_scores)
                / assign.points_possible
                for assign in assigns
            )
            / len(assigns)
            * mt.weight
            for mt, assigns in grouper.items()
        ) * (100 / sum(mt.weight for mt in grouper.keys()))
        return score

    @async_cached_property
    async def assignment_metas(self) -> list[dict[str, Any]]:
        await self._ensure_meta()
        return self._meta["assignments"]

    @async_cached_property
    async def name(self) -> str:
        await self._ensure_class_meta()
        return self._class_meta["className"]

    @async_cached_property
    async def teacher(self) -> Teacher:
        await self._ensure_class_meta()

        mailto = pp.Combine(
            pp.Literal("mailto:").suppress() + pp.dbl_quoted_string
        ) + pp.QuotedString(quote_char="<", end_quote_char=">")("email")
        email = mailto.parseString(self._class_meta["emailLink"]).email

        return Teacher(name=self._class_meta["teacherName"], email=email)

    async def _ensure_class_meta(self):
        await self._choose()
        if hasattr(self, "_class_meta"):
            return

        self._class_meta = await self.studentvue.post(
            "./api/GB/ClientSideData/Transfer?action=pxp.course.grade.card-get",
            {
                "FriendlyName": "pxp.course.grade.card",
                "Method": "get",
                "Parameters": "{}",
            },
        )

    async def _ensure_meta(self):
        await self._choose()
        if hasattr(self, "_meta"):
            return

        self._meta = await self.studentvue.post(
            "./api/GB/ClientSideData/Transfer?action=genericdata.classdata-GetClassData",
            {
                "FriendlyName": "genericdata.classdata",
                "Method": "GetClassData",
                "Parameters": "{}",
            },
        )

    async def _choose(self):
        if Class.current_class_id != self.class_id:
            await self.studentvue.load_control(
                self.load_params["LoadParams"]["ControlName"],
                self.load_params["FocusArgs"],
            )
            Class.current_class_id = self.class_id

    async def _ensure_assignments_counts(self):
        await self._choose()
        if hasattr(self, "_assignments_counts"):
            return

        self._assignments_counts = await self.studentvue.post(
            "./api/GB/ClientSideData/Transfer?action=pxp.course.cards-get",
            {"FriendlyName": "pxp.course.cards", "Method": "get", "Parameters": "{}"},
        )

    async def _ensure_assignments(self):
        await self._choose()
        if hasattr(self, "_assignments"):
            return

        self._assignments = await self.studentvue.post(
            "./api/GB/ClientSideData/Transfer?action=pxp.course.content.items-LoadWithOptions",
            {
                "FriendlyName": "pxp.course.content.items",
                "Method": "LoadWithOptions",
                "Parameters": '{"loadOptions":{"sort":[{"selector":"due_date","desc":false}],"requireTotalCount":true,"userData":{}},"clientState":{}}',
            },
        )

    async def to_class(self) -> ClassData:
        """
        Convert self into pure data.
        """

        logger.debug("Converting class %s to data", await self.name)
        try:
            done, pending = await asyncio.wait(
                (
                    self._ensure_meta(),
                    self._ensure_class_meta(),
                    self._ensure_assignments_counts(),
                    self._ensure_assignments(),
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.error("Timeout while loading data.")
            raise SpiderError(
                "Timeout while load data for assignments",
                self.nav.my_studentvue.grade_book.url,
            )
        return ClassData(
            *(
                await asyncio.gather(
                    self.name,
                    self.teacher,
                    self.exact_score,
                    self.measure_types,
                    self.assignments,
                )
            )
        )

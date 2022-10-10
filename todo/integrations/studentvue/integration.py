from pprint import pprint
from todo.error import NeedConfigError
from todo.integrations import Integration
from todo.integrations.studentvue.spider import *
import todo.integrations.studentvue.spider as spider


class GradeBookIntegration(Integration):
    def __init__(self):
        spider.logger = self.logger
        try:
            self.username = self.config.username
        except AttributeError:
            raise NeedConfigError(f"{self.config_path}.username", "username of the e-class account") from None
        try:
            self.password = self.config.password
        except AttributeError:
            raise NeedConfigError(f"{self.config_path}.password", "password of the e-class account") from None
        self.manager = SessionManager("e_class")
        self.navigator = Navigator("e_class", "e_class")

    async def update(self):
        manager, navigator = self.manager, self.navigator
        username, password = self.username, self.password

        if not hasattr(self, "e_class"):
            try:
                self.e_class = EClass(manager, navigator, username, password)
            except SpiderError as e:
                self.error(f"Failed to login to e-class: {e}")
                raise NeedConfigError(f"{self.config_path}", "check the password and username")

        if not hasattr(self, "student_vue"):
            try:
                self.student_vue = StudentVue(manager, navigator, self.e_class)
            except SpiderError as e:
                self.error(f"Failed to login to studentvue: {e}")
                raise e

        if not hasattr(self, "classes"):
            try:
                self.grade_book = await GradeBook.create(manager, navigator, self.student_vue)
                # hopefully nobody will run this program for more than a semester continuously
                self.classes = await self.grade_book.default_classes
            except SpiderError as e:
                self.error(f"Failed to get class datas: {e}")
                raise e

        results = []
        try:
            for cls in self.classes:
                cl = await Class.create(manager, navigator, self.student_vue, cls)
                results.append(await cl.to_class())
        except SpiderError as e:
            self.error(f"Failed to get data for individual classes: {e}")
            raise e


asyncio.run(GradeBookIntegration().update())

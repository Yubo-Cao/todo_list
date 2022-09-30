import functools
from tkinter import filedialog
from urllib.parse import quote, urlunparse
import webbrowser
import gender_guesser.detector as gender

from datetime import datetime

from grade_checker.components import *
from concurrent.futures import ThreadPoolExecutor
from grade_checker.db import Course, Teacher, Grade_Change
from grade_checker.logger import logger
from grade_checker.spider import (
    fetch_grade_book_data,
    fetch_navigation_data,
    fetch_teacher_course_data,
    validate_username_password,
    refresh_db,
    parse_grade_from_html,
)
from grade_checker.config import cfg

from grade_checker.calculate import (
    calculate_unweighted_avg,
    calculate_weighted_avg_html,
    get_latest_grade_change,
    stack_plot,
    calculate_weighted_avg,
    find_grade_with_semester,
)

import sys

ASSETS_PATH = Path(__file__).resolve().parent / "assets"
ICON = str(ASSETS_PATH / "icon.ico")


def create_first_time_frame(win, root):
    notebook = ttk.Notebook(root)
    notebook.grid(row=0, column=0, sticky="NSEW")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    # Welcome
    welcome_tab = ttk.Frame(notebook)
    welcome_tab["padding"] = 16
    notebook.add(welcome_tab, text="Welcome")

    Icon(welcome_tab, icon_path="icon.png", sz=128).grid(
        row=0, column=0, sticky="ew", pady=4
    )
    ttk.Label(welcome_tab, text="Welcome to", font=TITLE_FONT, anchor="center").grid(
        row=1, column=0, sticky="ew"
    )
    ttk.Label(
        welcome_tab, text="Grade Checker", font=SUBTITLE_FONT, anchor="center"
    ).grid(row=2, column=0, sticky="ew", pady=(0, 4))
    ttk.Button(
        welcome_tab,
        text="Next",
        style="Accent.TButton",
        command=lambda: notebook.tab(license_tab, state="normal")
        or notebook.select(license_tab),
    ).grid(row=5, column=0, sticky="s")

    welcome_tab.columnconfigure(0, weight=1)
    welcome_tab.rowconfigure(0, weight=2)
    welcome_tab.rowconfigure(5, weight=1)

    # Acknowledgement And License
    license_tab = ttk.Frame(notebook, padding=(80, 16, 80, 16))
    notebook.add(license_tab, text="License", state="hidden")

    message = Text(
        license_tab,
        font=(default_font.actual("family"), 12),
    )
    with open(Path(__file__).parent / "assets" / "license") as f:
        message.insert(
            "1.0",
            f.read()
            .strip()
            .replace("\n", " ")
            .replace("   ", "\n\n")
            .replace("  ", "\n\n")
            .format(path=cfg.path),
        )
    message["state"] = "disabled"
    message.grid(row=0, column=0, sticky="news", pady=(0, 16))
    license_tab.columnconfigure(0, weight=1)
    license_tab.rowconfigure(0, weight=1)

    ttk.Button(
        license_tab,
        text="Next",
        style="Accent.TButton",
        command=lambda: notebook.tab(ask_info_tab, state="normal")
        or notebook.select(ask_info_tab),
    ).grid(row=5, column=0, sticky="s")

    # Ask for informations
    ask_info_tab = ttk.Frame(notebook)
    ask_info_tab["padding"] = 16
    notebook.add(ask_info_tab, text="Informations", state="hidden")
    warning = ttk.Label(
        ask_info_tab,
        text="""
- No password and username
- Less Functionality
- Parse HTML""".strip(),
    )
    warning.bind(
        "<Configure>",
        lambda e: warning.configure(wraplength=e.width)
        or file_path_status.configure(wraplength=e.width),
    )
    warning.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
    file_path_variable = StringVar()

    def choose_file():
        path = filedialog.askopenfilename(
            filetypes=[("HTML File", "*.html")],
            title="Choose HTML File",
        )
        file_path_variable.set(path)
        file_path_status["text"] = "File path: " + path

    style = ttk.Style()
    style.configure("Default.TButton")

    def update_btn_state(*args):
        if not (
            file_path_variable.get() or (username.validate() and password.validate())
        ):
            next_btn.state(["disabled"])
            next_btn.config(style="Default.TButton")
        else:
            if username.validate() and password.validate():
                cfg.grade_checker["username"] = username.value
                cfg.grade_checker["password"] = password.value
                if "file_path" in cfg.grade_checker:
                    cfg.grade_checker.pop("file_path")
                cfg.grade_checker["update_method"] = "login"
            elif file_path_variable.get():
                if "username" in cfg.grade_checker:
                    cfg.grade_checker.pop("username")
                if "password" in cfg.grade_checker:
                    cfg.grade_checker.pop("password")
                cfg.grade_checker["html_path"] = file_path_variable.get()
                cfg.grade_checker["update_method"] = "html"

            next_btn.state(["!disabled"])
            next_btn.config(style="Accent.TButton")
            next_btn.config(text="Next")

    file_path_variable.trace_add("write", update_btn_state)

    file_path_status = ttk.Label(ask_info_tab, text="File path: ")

    choose_file_btn = ttk.Button(ask_info_tab, text="Choose File", command=choose_file)

    Icon(ask_info_tab, icon_path="html.png", sz=128, resizable=False).grid(
        row=0, column=0, sticky="news"
    )
    warning.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
    choose_file_btn.grid(row=2, column=0, sticky="sew", padx=4, pady=4)
    file_path_status.grid(row=3, column=0, sticky="new", padx=4, pady=4)

    sep = ttk.Separator(ask_info_tab, orient="vertical")
    sep.grid(row=0, column=1, sticky="ns", rowspan=4)

    info = ttk.Label(
        ask_info_tab,
        text="""
- Require eclass password and username
- Automatically retrieve grade, course, teacher
    """.strip(),
    )
    info.bind("<Configure>", lambda e: info.configure(wraplength=e.width))

    username = DefaultEntry(
        ask_info_tab,
        prompt="Enter your username:",
        key_re="[-0-9]*",
        total_re="[-0-9]{9,}",
    )
    password = PasswordEntry(ask_info_tab, prompt="Enter your password:", total_re=".+")

    Icon(ask_info_tab, icon_path="user.png", sz=128, resizable=False).grid(
        row=0, column=2, sticky="news"
    )
    info.grid(row=1, column=2, sticky="ew", padx=8, pady=8)
    username.grid(row=2, column=2, sticky="sew", padx=4, pady=4)
    password.grid(row=3, column=2, sticky="new", padx=4, pady=4)

    username.variable.trace_add("write", update_btn_state)
    password.variable.trace_add("write", update_btn_state)

    def next():

        if (
            cfg.grade_checker.update_method == "login"
            and not validate_username_password(
                cfg.grade_checker.username, cfg.grade_checker.password
            )
        ):
            next_btn.state(["disabled"])
            next_btn.config(style="Default.TButton")
            next_btn.config(text="Invalid username or password")
        else:
            notebook.tab(done_tab, state="normal")
            notebook.select(done_tab)

    next_btn = ttk.Button(ask_info_tab, text="Next", command=next)
    next_btn.state(["disabled"])
    next_btn.grid(row=4, column=0, sticky="s", columnspan=3, pady=(8, 0))

    ask_info_tab.rowconfigure(0, weight=1)
    ask_info_tab.rowconfigure(1, weight=1)
    ask_info_tab.rowconfigure(2, weight=1)
    ask_info_tab.columnconfigure(0, weight=1, uniform="card")
    ask_info_tab.columnconfigure(1, weight=0, minsize=16)
    ask_info_tab.columnconfigure(2, weight=1, uniform="card")

    # Done
    done_tab = ttk.Frame(notebook)
    done_tab["padding"] = 16
    notebook.add(done_tab, text="Done", state="hidden")
    Icon(done_tab, icon_path="done.png", sz=128, resizable=False).grid(
        row=0, column=0, sticky="news"
    )
    ttk.Label(done_tab, text="Congratulations!", font=TITLE_FONT, anchor="center").grid(
        row=1, column=0, sticky="ew"
    )
    ttk.Label(
        done_tab,
        text="You are ready to use this APP",
        font=SUBTITLE_FONT,
        anchor="center",
    ).grid(row=2, column=0, sticky="ew", pady=(4, 0))

    def done():
        cfg.grade_checker.__setitem__("first_time", False)
        [slave.grid_forget() for slave in root.grid_slaves()]
        win.withdraw()
        if cfg.grade_checker.update_method == "login":
            daemon_loop(root)
            create_normal_login_main(root)
        else:
            create_normal_html_main(root)
        win.deiconify()

    ttk.Button(
        done_tab,
        text="Next",
        style="Accent.TButton",
        command=done,
    ).grid(row=3, column=0, sticky="s", pady=(8, 0))
    done_tab.columnconfigure(0, weight=1)
    done_tab.rowconfigure(0, weight=2)
    done_tab.rowconfigure(3, weight=1)


def create_normal_login_main(root):
    notebook = ttk.Notebook(root)
    notebook.grid(row=0, column=0, sticky="NSEW")

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Fetcher
    fetcher_tab = ttk.Frame(notebook, padding=16)
    notebook.add(fetcher_tab, text="Fetcher")

    Icon(fetcher_tab, icon_path="teacher.png", width=64).grid(
        row=0, column=0, sticky="news", padx=(0, 4), pady=(0, 8)
    )
    future_progressbar(
        fetcher_tab,
        "Force Re-Fetch Teachers and Courses",
        lambda: fetch_teacher_course_data(checked=False),
    ).grid(row=0, column=1, sticky="news", pady=(0, 8))

    Icon(fetcher_tab, icon_path="navigation.png", width=64).grid(
        row=1, column=0, sticky="news", padx=(0, 4), pady=(8, 0)
    )
    future_progressbar(
        fetcher_tab,
        "Force Re-Fetch Navigation Data",
        lambda: fetch_navigation_data(checked=False),
    ).grid(row=1, column=1, sticky="news")

    Icon(fetcher_tab, icon_path="grade.png", width=64).grid(
        row=0, column=2, sticky="news", padx=(16, 4), pady=(0, 8)
    )
    future_progressbar(
        fetcher_tab,
        "Fetch Grades Now",
        fetch_grade_book_data,
    ).grid(row=0, column=3, sticky="news", pady=(0, 8))

    Icon(fetcher_tab, icon_path="all.png", width=64).grid(
        row=1, column=2, sticky="news", padx=(0, 4), pady=(8, 0)
    )
    future_progressbar(
        fetcher_tab,
        "Refresh All Databases",
        refresh_db,
    ).grid(row=1, column=3, sticky="news", padx=4, pady=(16, 0))

    for slave in fetcher_tab.grid_slaves():
        slave.grid_configure(padx=8, pady=8)
        fetcher_tab.rowconfigure(slave.grid_info()["row"], weight=1, uniform="row")

    for i in range(4):
        if i % 2 == 0:
            fetcher_tab.columnconfigure(i, weight=1, uniform="btn")
        else:
            fetcher_tab.columnconfigure(i, weight=0, minsize=32, uniform="icon")

    # Overview
    overview_tab = ttk.Frame(notebook, padding=16)
    notebook.add(overview_tab, text="Overview")

    status = ttk.Frame(overview_tab, padding=[0, 0, 0, 8])

    # Display Unweighted Average Grade on LEFT
    ttk.Label(status, text="Unweighted Average", font=TITLE_FONT, anchor="center").grid(
        row=0, column=0, sticky="sew", pady=(0, 4)
    )
    unweighted_avg = StringVar()
    ttk.Label(
        status, textvariable=unweighted_avg, font=SUBTITLE_FONT, anchor="center"
    ).grid(row=1, column=0, sticky="new", pady=(0, 8))

    items = {}

    def update_overview():
        s = semester_values[semester_var.get()]
        weighted_avg.set(calculate_weighted_avg(na=na_var.get(), semester=s))
        unweighted_avg.set(calculate_unweighted_avg(na=na_var.get(), semester=s))

        _update_tree()

    # Display Weighted Average Grade on LEFT
    weighted_avg = StringVar()
    ttk.Label(status, text="Weighted Average", font=TITLE_FONT, anchor="center").grid(
        row=2, column=0, sticky="sew", pady=(0, 4)
    )
    ttk.Label(
        status, textvariable=weighted_avg, font=SUBTITLE_FONT, anchor="center"
    ).grid(row=3, column=0, sticky="new")

    for row in range(4):
        if row % 2 == 0:
            status.rowconfigure(row, weight=2)
        else:
            status.rowconfigure(row, weight=1)
    status.columnconfigure(0, weight=1)

    # Display Some Control For Filter
    control = ttk.Frame(overview_tab, padding=[0, 8, 0, 0])

    semester_values = {"Semester 1": 1, "Semester 2": 2, "Semester 1 & 2": None}
    semester_var = StringVar(value="Semester 1")
    semester = ttk.Combobox(
        control, values=list(semester_values.keys()), textvariable=semester_var
    )
    semester.state(["readonly"])
    semester.grid(row=1, column=0, sticky="ew")
    semester.current(0)
    semester.bind("<<ComboboxSelected>>", lambda event: update_overview())

    na_var = IntVar(value=100)
    na = ttk.Spinbox(control, from_=0, to=100, textvariable=na_var)
    na_var.trace_add("write", lambda *args: update_overview())
    na.grid(row=2, column=0, sticky="ew")

    for slave in control.grid_slaves():
        slave.grid_configure(pady=4)
        control.rowconfigure(slave.grid_info()["row"], weight=1, uniform="row")
    control.columnconfigure(0, weight=1)

    status.grid(row=0, column=0, sticky="news", padx=(0, 8))
    control.grid(row=1, column=0, sticky="news", padx=(0, 8))

    # Display Grade Breakdown on RIGHT

    tree = ttk.Treeview(
        overview_tab, columns=["grade", "teacher", "weighted"], show="headings"
    )
    tree["columns"] = ("name", "grade", "weighted", "teacher-email")

    tree.column("name", width=150, anchor="center")
    tree.heading("name", text="Course Name")
    tree.column("grade", width=50, anchor="center")
    tree.heading("grade", text="Grade")
    tree.column("weighted", width=50, anchor="center")
    tree.heading("weighted", text="Weighted")
    tree.column("teacher-email", width=150, anchor="center")
    tree.heading("teacher-email", text="Teacher's Email")

    tree.grid(row=0, column=1, rowspan=2, sticky="news", padx=(8, 0))

    overview_tab.rowconfigure(0, weight=2)
    overview_tab.rowconfigure(1, weight=1)
    overview_tab.columnconfigure(0, weight=1, uniform="overview_column")
    overview_tab.columnconfigure(1, weight=1, uniform="overview_column")

    def _update_tree():
        s = semester_values[semester_var.get()]
        new_grades = set(find_grade_with_semester(s))

        for grade in items.keys() - new_grades:
            tree.detach(items[grade])
            del items[grade]

        for grade in new_grades - items.keys():
            course = Course.find_one(id=grade.course_id)
            teacher = Teacher.find_one(id=course.teacher_id)

            if grade not in items:
                id = tree.insert(
                    "",
                    "end",
                    values=[
                        course.name,
                        grade.grade,
                        course.name.find("Ap") != -1,
                        teacher.email,
                    ],
                )
                items[grade] = id
            else:
                tree.move(items[grade], "", "end")

    update_overview()
    notebook.bind("<<NotebookTabChanged>>", lambda event: update_overview())

    # Plotter
    plotter_tab = ttk.Frame(notebook, padding=16)
    notebook.add(plotter_tab, text="Graph")

    def update_plot():
        for slave in plotter_tab.grid_slaves():
            slave.grid_remove()
        try:
            canvas = stack_plot(plotter_tab, semester=2)
            canvas.grid(row=0, column=0, sticky="news")
        except Exception:
            Icon(plotter_tab, icon_path="cancel.png", sz=256, resizable=False).grid(
                row=0, column=0, sticky="news"
            )

            ttk.Label(
                plotter_tab,
                text="Nor enough grades to plot",
                font=TITLE_FONT,
                anchor="center",
            ).grid(row=1, column=0, sticky="ew")

    plotter_tab.bind("<Configure>", lambda event: update_plot())

    plotter_tab.rowconfigure(0, weight=1)
    plotter_tab.rowconfigure(1, weight=1)
    plotter_tab.columnconfigure(0, weight=1)


executor = ThreadPoolExecutor(max_workers=2)

count = 0


def future_progressbar(
    root,
    text,
    func,
    btn_kwargs={},
    pbar_kwargs={},
    cancelable=True,
    cancel_text="Cancel",
    *args,
    **kwargs,
) -> ttk.Frame:
    pbar_size = pbar_kwargs.get("size", 10)
    f = ttk.Frame(root)

    def update_status(cur_run):
        nonlocal running
        running = cur_run
        pbar.running = running
        if running:
            style.configure(style_name, anchor="w")
            btn.config(style=style_name)
            if cancelable:
                btn["text"] = cancel_text
                btn["command"] = cancel_func
            else:
                btn.state(["disabled"])

            pbar.place(
                in_=btn,
                anchor="center",
                rely=0.5,
                relx=1,
                x=-pbar_size / 2 - (btn.winfo_height() - pbar_size) / 2,
            )
        else:
            pbar.place_forget()
            style.configure(style_name, anchor="center")
            btn.config(style=style_name)
            btn["command"] = run
            btn["text"] = text
            btn.state(["!disabled"])
            btn.grid(row=0, column=0, sticky="news")

    def cancel_func():
        future.cancel()
        update_status(False)

    def run():
        nonlocal running, future
        update_status(True)

        def _done_hook(future):
            nonlocal running
            update_status(False)

        future = executor.submit(func, *args, **kwargs)
        future.add_done_callback(_done_hook)

    future = None
    running = False
    btn = ttk.Button(f, text=text, command=run, **btn_kwargs)
    pbar = CircularProgressBar(f, size=pbar_size, **pbar_kwargs)

    global count
    style_name = str(count) + ".TButton"
    style = ttk.Style()
    count += 1

    btn.bind(
        "<Configure>",
        lambda e: pbar.event_generate(
            "<Configure>", width=e.width, height=e.height, x=e.x, y=e.y
        )
        or style.configure(style_name, wraplength=e.width),
    )

    update_status(False)

    f.rowconfigure(0, weight=1)
    f.columnconfigure(0, weight=1)

    return f


def create_normal_html_main(root):
    r = ttk.Frame(root, padding=16)
    r.grid(row=0, column=0, sticky="news")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    def _auto_update():
        if Path(cfg.grade_checker.html_path).exists():
            try:
                with open(cfg.grade_checker.html_path, encoding="utf-8") as f:
                    data = parse_grade_from_html(f.read())
                    assert len(data) != 0, "No grades found"
                    update_overview()
                    remove_exception()
                    grid_status()
            except Exception as e:
                logger.error(f"Error while parsing html: {e!r}")
                remove_status()
                grid_exception(f"HTML at {cfg.grade_checker.html_path} is invalid")
                
        else:
            remove_status()
            grid_exception(
                f"You haven't put StudentVUE html at {cfg.grade_checker.html_path} yet"
            )

        r.after(5000, _auto_update)

    def remove_status():
        status.grid_remove()
        na.grid_remove()
    
    def grid_status():
        status.grid(row=0, column=0, sticky="news")
        na.grid(row=1, column=0, sticky="news")

    def grid_exception(msg):
        warning.grid(row=0, column=0, sticky="news")
        message.grid(row=1, column=0, sticky="news")
        message["text"] = msg
        
    def remove_exception():
        warning.grid_remove()
        message.grid_remove()

    def update_overview():
        weighted_avg.set(calculate_weighted_avg_html(na=na_var.get()))
        unweighted_avg.set(calculate_unweighted_avg(na=na_var.get()))

    warning = Icon(r, icon_path="cancel.png", sz=128, resizable=False)
    message = ttk.Label(
        r,
        text=f"You haven't put StudentVUE HTML at {cfg.grade_checker.html_path} yet",
        font=TITLE_FONT,
        anchor="center",
    )

    status = ttk.Frame(r, padding=[0, 0, 0, 8])

    # Display Unweighted Average Grade on LEFT
    ttk.Label(status, text="Unweighted Average", font=TITLE_FONT, anchor="center").grid(
        row=0, column=0, sticky="sew", pady=(0, 4)
    )
    unweighted_avg = StringVar()
    ttk.Label(
        status, textvariable=unweighted_avg, font=SUBTITLE_FONT, anchor="center"
    ).grid(row=1, column=0, sticky="new", pady=(0, 8))

    # Display Weighted Average Grade on LEFT
    weighted_avg = StringVar()
    ttk.Label(status, text="Weighted Average", font=TITLE_FONT, anchor="center").grid(
        row=2, column=0, sticky="sew", pady=(0, 4)
    )
    ttk.Label(
        status, textvariable=weighted_avg, font=SUBTITLE_FONT, anchor="center"
    ).grid(row=3, column=0, sticky="new")

    for row in range(4):
        if row % 2 == 0:
            status.rowconfigure(row, weight=2)
        else:
            status.rowconfigure(row, weight=1)
    status.columnconfigure(0, weight=1)

    na_var = IntVar(value=100)
    na = ttk.Spinbox(r, from_=0, to=100, textvariable=na_var)
    na_var.trace_add("write", lambda *args: update_overview())
    na.grid(row=4, column=0, sticky="sew")

    r.columnconfigure(0, weight=1)
    for i in range(5):
        r.rowconfigure(i, weight=1)
    r.after(1000, _auto_update)


def send_email_generator(grade_change, course, teacher) -> Callable:
    fmt_dict = get_format_dict(grade_change, course, teacher)

    body = cfg.grade_checker.body_template.format(**fmt_dict)
    subject = cfg.grade_checker.subject_template.format(**fmt_dict)
    url = urlunparse(
        (
            "mailto",
            "",
            teacher.email,
            "",
            f"body={quote(body)}&subject={quote(subject)}",
            "",
        )
    )

    def _impl():
        try:
            webbrowser.open(url)
        except Exception:
            logger.error("Failed to open " + url)

    return _impl


@functools.cache
def get_format_dict(grade_change, course, teacher):
    hour = datetime.now().hour
    seen = set()
    gender = [
        gender
        for gender in filter(
            lambda r: r != "unknown",
            (detector.get_gender(name) for name in teacher.name.split(" ")),
        )
        if (gender not in seen or seen.add(gender))
    ]
    gender = (
        gender[0] if len(gender) == 1 else (gender[-1] if len(gender) == 2 else "male")
    )  # If two result, use last name. If no result, assume male
    title = "Mr." if gender == "male" else "Ms."

    fmt_dict = dict(
        time="morning" if hour < 12 else ("afternoon" if hour < 18 else "evening"),
        title=title,
        teacher_name=teacher.name,
        teacher_last_name=teacher.name.split(" ")[-1],
        teacher_first_name=teacher.name.split(" ")[0],
        your_name=cfg.grade_checker.get("your_name", " "),
        your_last_name=cfg.grade_checker.get("your_name", " ").split(" ")[-1],
        your_first_name=cfg.grade_checker.get("your_name", " ").split(" ")[0],
        period=course.period,
        **{"class": course.name},
        teacher_email=teacher.email,
        old_grade=grade_change.old_grade,
        new_grade=grade_change.new_grade,
    )

    return fmt_dict


detector = gender.Detector()


def daemon_loop():
    if grade_change := get_latest_grade_change():
        grade_change = Grade_Change(*grade_change)
        grade_change.delete()

        logger.debug("Daemon loop: Detected grade change")
        course = Course.find_one(id=grade_change.course_id)
        teacher = Teacher.find_one(id=course.teacher_id)
        if grade_change.old_grade > grade_change.new_grade:
            Notification(
                title="Grade Checker",
                subtitle=cfg.grade_checker.grade_decrease_notification_template.format(
                    **get_format_dict(grade_change, course, teacher)
                ),
                icon=ASSETS_PATH / "decrease.ico",
                callback=send_email_generator(grade_change, course, teacher),
            )
        else:
            Notification(
                title="Grade Checker",
                subtitle=cfg.grade_checker.grade_increase_notification_template.format(
                    **get_format_dict(grade_change, course, teacher)
                ),
                icon=ASSETS_PATH / "increase.ico",
            )
        # A shorter interval to check update again
        win.after(5000, daemon_loop)

    if (
        datetime.utcnow().timestamp()
        - cfg.grade_checker.get("last_update", datetime.utcnow().timestamp())
        > cfg.grade_checker.daemon_interval
    ):
        executor.submit(refresh_db)
        cfg.grade_checker.last_update = datetime.utcnow().timestamp()
    win.after(cfg.grade_checker.daemon_interval, daemon_loop)


tray_menu = None


def on_closing():
    win.withdraw()
    global tray_menu
    if not tray_menu:
        win.tk.call("package", "require", "Winico")
        icon = win.tk.call("winico", "createfrom", ICON)
        win.tk.call(
            "winico",
            "taskbar",
            "add",
            icon,  # set the icon
            "-callback",
            (
                win.register(menu_func),
                "%m",
                "%x",
                "%y",
            ),  # refer to winico documentation.
            "-pos",
            0,
            "-text",
            "Grade Checker",
        )

        tray_menu = Menu(win)
        tray_menu.add_command(label="Show", command=win.deiconify)
        tray_menu.add_command(label="Quit", command=shutdown)
        tray_menu.add_command(label="Config", command=lambda: webbrowser.open(cfg.path))


def shutdown():
    try:
        executor.shutdown(wait=False)
        win.destroy()
    except Exception as e:
        logger.error(f"Failed to shutdown because of {e!r}", exc_info=True)
    finally:
        sys.exit(0)


def menu_func(event, x, y):
    if event == "WM_RBUTTONDOWN":
        tray_menu.tk_popup(x, y)
    if event == "WM_LBUTTONDOWN":
        win.deiconify()


def main():
    root = ttk.Frame(win)
    root.grid(row=0, column=0, sticky="nsew")
    win.title("Grade Checker")
    win.rowconfigure(0, weight=1)
    win.columnconfigure(0, weight=1)
    win.iconbitmap(ICON)

    if cfg.grade_checker.first_time:
        create_first_time_frame(win, root)
    else:
        if cfg.grade_checker.update_method == "login":
            create_normal_login_main(root)
        elif cfg.grade_checker.update_method == "html":
            create_normal_html_main(root)

    win.protocol("WM_DELETE_WINDOW", on_closing)
    if cfg.grade_checker.get("update_method", None) == "login":
        win.after(1000, daemon_loop)
    win.mainloop()


if __name__ == "__main__":
    main()

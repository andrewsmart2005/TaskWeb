#!/usr/bin/env python3
import argparse
import json
import os
import shlex
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


STORE_FILE = ".today_tasks.json"


def load_tasks() -> List[Dict[str, Any]]:
    if not os.path.exists(STORE_FILE):
        return []
    with open(STORE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, sort_keys=False)


def next_id(tasks: List[Dict[str, Any]]) -> int:
    return (max((t["id"] for t in tasks), default=0) + 1)


def parse_due_key(due: Optional[str]) -> Tuple[int, str]:
    if not due:
        return (999999, "")
    due = due.strip()
    for fmt in ("%H:%M", "%I:%M%p", "%I%p"):
        try:
            dt = datetime.strptime(due.upper(), fmt)
            return (dt.hour * 60 + dt.minute, due)
        except ValueError:
            continue
    return (999998, due)


def cmd_add(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    task = {
        "id": next_id(tasks),
        "text": args.text.strip(),
        "due": args.due.strip() if args.due else None,
        "done": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f'Added #{task["id"]}: {task["text"]}')


def cmd_list(_: argparse.Namespace) -> None:
    tasks = load_tasks()
    if not tasks:
        print("No tasks yet.")
        return
    tasks_sorted = sorted(
        tasks, key=lambda t: (t["done"],) + parse_due_key(t.get("due"))
    )
    for t in tasks_sorted:
        status = "x" if t["done"] else " "
        due = f' (due {t["due"]})' if t.get("due") else ""
        print(f'[{status}] #{t["id"]} {t["text"]}{due}')


def cmd_done(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            t["done"] = True
            save_tasks(tasks)
            print(f'Marked done: #{t["id"]} {t["text"]}')
            return
    print(f"Task #{args.id} not found.")


def cmd_undone(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            t["done"] = False
            save_tasks(tasks)
            print(f'Marked not done: #{t["id"]} {t["text"]}')
            return
    print(f"Task #{args.id} not found.")


def cmd_remove(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    filtered = [t for t in tasks if t["id"] != args.id]
    if len(filtered) == len(tasks):
        print(f"Task #{args.id} not found.")
        return
    save_tasks(filtered)
    print(f"Removed task #{args.id}.")


def build_shell_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="")
    sub = parser.add_subparsers(required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("text")
    p_add.add_argument("--due")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list")
    p_list.set_defaults(func=cmd_list)

    p_done = sub.add_parser("done")
    p_done.add_argument("id", type=int)
    p_done.set_defaults(func=cmd_done)

    p_undone = sub.add_parser("undone")
    p_undone.add_argument("id", type=int)
    p_undone.set_defaults(func=cmd_undone)

    p_remove = sub.add_parser("remove")
    p_remove.add_argument("id", type=int)
    p_remove.set_defaults(func=cmd_remove)

    return parser


def cmd_shell(_: argparse.Namespace) -> None:
    shell_parser = build_shell_parser()
    print('Interactive mode. Type "help" for commands, "quit" to exit.')
    while True:
        try:
            line = input("tasks> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line in ("quit", "exit"):
            break
        if line == "help":
            print("Commands:")
            print('  add "task text" [--due 14:30|2:30PM]')
            print("  list")
            print("  done ID")
            print("  undone ID")
            print("  remove ID")
            print("  quit")
            continue
        try:
            argv = shlex.split(line)
        except ValueError as e:
            print(f"Parse error: {e}")
            continue
        try:
            args = shell_parser.parse_args(argv)
        except SystemExit:
            continue
        args.func(args)


def format_task_line(task: Dict[str, Any]) -> str:
    status = "x" if task["done"] else " "
    due = f' (due {task["due"]})' if task.get("due") else ""
    return f'[{status}] #{task["id"]} {task["text"]}{due}'


def sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(tasks, key=lambda t: (t["done"],) + parse_due_key(t.get("due")))


def cmd_ui(_: argparse.Namespace) -> None:
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Horizontal, Vertical
        from textual.screen import ModalScreen
        from textual.widgets import Button, Input, Label, ListItem, ListView, Static
    except ImportError:
        print("Textual is not installed. Run: pip install textual")
        return

    class TaskEditScreen(ModalScreen[Optional[Tuple[str, Optional[str]]]]):
        def __init__(self, title: str, text: str = "", due: str = "") -> None:
            super().__init__()
            self.title = title
            self.text = text
            self.due = due

        def compose(self) -> ComposeResult:
            yield Static(self.title, id="title")
            yield Input(value=self.text, placeholder="Task text", id="text")
            yield Input(value=self.due, placeholder="Due time (optional)", id="due")
            with Horizontal():
                yield Button("Save", id="save", variant="primary")
                yield Button("Cancel", id="cancel")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if event.button.id == "save":
                text = self.query_one("#text", Input).value.strip()
                due = self.query_one("#due", Input).value.strip()
                if not text:
                    return
                self.dismiss((text, due or None))
            else:
                self.dismiss(None)

    class TasksApp(App):
        CSS = """
        Screen { padding: 1; }
        #title { content-align: center middle; height: 3; }
        ListView { height: 1fr; border: round #5c5c5c; }
        Input { margin-bottom: 1; }
        """
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("a", "add_task", "Add"),
            ("d", "delete_task", "Delete"),
            ("e", "edit_task", "Edit"),
            ("enter", "toggle_task", "Toggle"),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.tasks: List[Dict[str, Any]] = []
            self.list_view: Optional[ListView] = None

        def compose(self) -> ComposeResult:
            yield Static("Today Tasks", id="title")
            self.list_view = ListView()
            yield self.list_view
            yield Label("a add | d delete | e edit | enter toggle | q quit")

        def on_mount(self) -> None:
            self.tasks = load_tasks()
            self.refresh_list()

        def refresh_list(self, selected_id: Optional[int] = None) -> None:
            assert self.list_view is not None
            self.list_view.clear()
            for task in sort_tasks(self.tasks):
                item = ListItem(Label(format_task_line(task)))
                item.task_id = task["id"]  # type: ignore[attr-defined]
                self.list_view.append(item)
            if selected_id is not None:
                for idx, item in enumerate(self.list_view.children):
                    if getattr(item, "task_id", None) == selected_id:
                        self.list_view.index = idx
                        break

        def get_selected_task(self) -> Optional[Dict[str, Any]]:
            assert self.list_view is not None
            item = self.list_view.highlighted_child
            if item is None:
                return None
            task_id = getattr(item, "task_id", None)
            if task_id is None:
                return None
            for task in self.tasks:
                if task["id"] == task_id:
                    return task
            return None

        def action_toggle_task(self) -> None:
            task = self.get_selected_task()
            if not task:
                return
            task["done"] = not task["done"]
            save_tasks(self.tasks)
            self.refresh_list(selected_id=task["id"])

        def action_delete_task(self) -> None:
            task = self.get_selected_task()
            if not task:
                return
            self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
            save_tasks(self.tasks)
            self.refresh_list()

        def action_add_task(self) -> None:
            def after(result: Optional[Tuple[str, Optional[str]]]) -> None:
                if not result:
                    return
                text, due = result
                task = {
                    "id": next_id(self.tasks),
                    "text": text,
                    "due": due,
                    "done": False,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
                self.tasks.append(task)
                save_tasks(self.tasks)
                self.refresh_list(selected_id=task["id"])

            self.push_screen(TaskEditScreen("Add Task"), after)

        def action_edit_task(self) -> None:
            task = self.get_selected_task()
            if not task:
                return

            def after(result: Optional[Tuple[str, Optional[str]]]) -> None:
                if not result:
                    return
                text, due = result
                task["text"] = text
                task["due"] = due
                save_tasks(self.tasks)
                self.refresh_list(selected_id=task["id"])

            self.push_screen(
                TaskEditScreen("Edit Task", text=task["text"], due=task.get("due") or ""),
                after,
            )

    TasksApp().run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple today-task tracker (add, list, check off)."
    )
    sub = parser.add_subparsers(required=True)

    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("text", help="Task description")
    p_add.add_argument("--due", help="Due time, e.g. 14:30 or 2:30PM")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List tasks")
    p_list.set_defaults(func=cmd_list)

    p_done = sub.add_parser("done", help="Mark task as done")
    p_done.add_argument("id", type=int, help="Task id")
    p_done.set_defaults(func=cmd_done)

    p_undone = sub.add_parser("undone", help="Mark task as not done")
    p_undone.add_argument("id", type=int, help="Task id")
    p_undone.set_defaults(func=cmd_undone)

    p_remove = sub.add_parser("remove", help="Remove a task")
    p_remove.add_argument("id", type=int, help="Task id")
    p_remove.set_defaults(func=cmd_remove)

    p_shell = sub.add_parser("shell", help="Start interactive prompt")
    p_shell.set_defaults(func=cmd_shell)

    p_ui = sub.add_parser("ui", help="Start interactive UI")
    p_ui.set_defaults(func=cmd_ui)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

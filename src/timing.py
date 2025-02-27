#    This file is part of Eichhörnchen 1.0.
#    Copyright (C) 2019  Carine Dengler
#
#    Eichhörnchen is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
:synopsis: Timing.
"""


# standard library imports
import datetime

# third party imports
# library specific imports
import src.sqlite


class Timer(object):
    """Timer.

    :ivar SQLite sqlite: Eichhörnchen SQLite database interface
    :ivar Task current_task: current task
    """

    def __init__(self, database):
        """Initialize timer.

        :param str database: Eichhörnchen SQLite3 database
        """
        self.sqlite = src.sqlite.SQLite(database)
        self.sqlite.create_table()
        self._reset_current_task()

    def _reset_current_task(self):
        """Reset current task."""
        name = ""
        start = end = due = datetime.datetime.now()
        due = datetime.datetime(9999, 12, 31)
        total = (end - start).seconds
        self.current_task = src.sqlite.Task(name, start, end, total, due)

    def _replace(self, **kwargs):
        """Replace current task."""
        self.current_task = self.current_task._replace(**kwargs)

    def start(self, args):
        """Start task.

        :param str args: arguments
        """
        if self.current_task.name:
            raise RuntimeError
        try:
            name = " ".join(args.split(" ")[:-1])
            due = datetime.datetime.strptime(args.split(" ")[-1], "%Y-%m-%d")
        except ValueError:
            name = args
            due = None
        now = datetime.datetime.now()
        result_set = self.sqlite.select_one("name", (name,))
        if result_set:
            task = src.sqlite.Task(*result_set)
            if due:
                self._replace(
                    name=name, start=now, total=task.total, due=due
                )
                self.sqlite.update_one(
                    "due",
                    "name",
                    (self.current_task.due, self.current_task.name)
                )
            else:
                self._replace(name=name, start=now, total=task.total)
            self.sqlite.update_one(
                "start",
                "name",
                (self.current_task.start, self.current_task.name)
            )
        else:
            if due:
                self._replace(name=name, start=now, due=due)
            else:
                self._replace(name=name, start=now)
            self.sqlite.insert([[*self.current_task]])

    def stop(self):
        """Stop task."""
        now = datetime.datetime.now()
        total = (
            self.current_task.total
            + (now - self.current_task.start).seconds
        )
        self._replace(end=now, total=total)
        row = self.sqlite.select_one("name", (self.current_task.name,))
        if not row:
            self.sqlite.insert([[*self.current_task]])
        row = self.sqlite.update_one(
            "end",
            "name",
            (self.current_task.end, self.current_task.name)
        )
        self.sqlite.update_one(
            "total",
            "name",
            (self.current_task.total, self.current_task.name)
        )
        self._reset_current_task()

    def list(self):
        """List tasks.

        :returns: list of tasks
        :rtype: list
        """
        now = datetime.datetime.now()
        start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0)
        tasks = [
            src.sqlite.Task(*task)
            for task in self.sqlite.select_many(
                column="start", parameters=(start_of_day,), operator=">="
            )
        ]
        return tasks

    def sum(self, name0, name1):
        """Sum up two tasks.

        :param str name0: name
        :param str name1: name

        :returns: sum of total attributes
        :rtype: int
        """
        task0 = self.sqlite.select_one(column="name", parameters=(name0,))
        if not task0:
            raise ValueError(f"'{name0}' does not exist")
        task0 = src.sqlite.Task(*task0)
        task1 = self.sqlite.select_one(column="name", parameters=(name1,))
        if not task1:
            raise ValueError(f"'{name1}' does not exist")
        task1 = src.sqlite.Task(*task1)
        return task0.total + task1.total

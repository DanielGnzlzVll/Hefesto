import datetime
from types import SimpleNamespace

from apscheduler.schedulers.background import BackgroundScheduler
from django.test import SimpleTestCase

from .management.commands.hefesto_processor import (
    TaskReconciler,
    function_wrap,
)

LOGGER = "hefesto_core.management.commands.hefesto_processor"
T0 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
T1 = T0 + datetime.timedelta(minutes=1)


class FakeTask(SimpleNamespace):
    def __str__(self):
        return f"{self.name} [{self.id}]"


def make_task(id=1, command="true", cron_expression="*/5 * * * *", updated=T0):
    return FakeTask(
        id=id,
        name=f"task-{id}",
        command=command,
        cron_expression=cron_expression,
        updated=updated,
    )


class TaskReconcilerTests(SimpleTestCase):
    def setUp(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start(paused=True)
        self.reconciler = TaskReconciler(self.scheduler)

    def tearDown(self):
        self.scheduler.shutdown(wait=False)

    def jobs(self):
        return {job.id: job for job in self.scheduler.get_jobs()}

    def test_adds_a_job_per_task(self):
        self.reconciler.reconcile([make_task(1), make_task(2)])

        self.assertEqual(set(self.jobs()), {"1", "2"})
        self.assertEqual(self.jobs()["1"].func.command, "true")

    def test_removes_jobs_for_tasks_no_longer_listed(self):
        self.reconciler.reconcile([make_task(1), make_task(2)])

        self.reconciler.reconcile([make_task(2)])

        self.assertEqual(set(self.jobs()), {"2"})

    def test_replaces_job_when_command_changes(self):
        self.reconciler.reconcile([make_task(1)])

        self.reconciler.reconcile(
            [make_task(1, command="echo hi", updated=T1)]
        )

        self.assertEqual(self.jobs()["1"].func.command, "echo hi")

    def test_replaces_job_when_cron_expression_changes(self):
        self.reconciler.reconcile([make_task(1)])

        self.reconciler.reconcile(
            [make_task(1, cron_expression="0 3 * * *", updated=T1)]
        )

        fields = {f.name: str(f) for f in self.jobs()["1"].trigger.fields}
        self.assertEqual(fields["hour"], "3")

    def test_leaves_unchanged_job_alone(self):
        self.reconciler.reconcile([make_task(1)])
        self.jobs()["1"].modify(next_run_time=T1)

        self.reconciler.reconcile([make_task(1)])

        self.assertEqual(self.jobs()["1"].next_run_time, T1)

    def test_resave_without_changes_does_not_reschedule(self):
        self.reconciler.reconcile([make_task(1)])
        self.jobs()["1"].modify(next_run_time=T1)

        self.reconciler.reconcile([make_task(1, updated=T1)])

        self.assertEqual(self.jobs()["1"].next_run_time, T1)

    def test_invalid_cron_expression_is_logged_and_skipped(self):
        self.reconciler.reconcile([make_task(1)])

        with self.assertLogs(LOGGER, "ERROR"):
            self.reconciler.reconcile(
                [
                    make_task(1, cron_expression="nope", updated=T1),
                    make_task(2),
                ]
            )

        self.assertEqual(set(self.jobs()), {"2"})


class FunctionWrapTests(SimpleTestCase):
    def test_logs_error_with_stderr_on_non_zero_exit(self):
        with self.assertLogs(LOGGER, "ERROR") as logs:
            function_wrap("echo boom >&2; exit 3")()

        self.assertIn("3", logs.output[0])
        self.assertIn("boom", logs.output[0])

    def test_logs_exit_code_on_success(self):
        with self.assertLogs(LOGGER, "INFO") as logs:
            function_wrap("true")()

        self.assertEqual([r.levelname for r in logs.records], ["INFO"])
        self.assertIn("0", logs.output[0])

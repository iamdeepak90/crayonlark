"""Task modules are imported here so the worker registers them."""

from crayonlark.worker.tasks import (  # noqa: F401
    ai_tasks,
    marketing_tasks,
    notify_tasks,
    print_tasks,
    publish_tasks,
    report_tasks,
    site_tasks,
    system,
)

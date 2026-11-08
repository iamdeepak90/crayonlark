"""Task modules are imported here so the worker registers them."""

from crayonlark.worker.tasks import (  # noqa: F401
    marketing_tasks,
    notify_tasks,
    print_tasks,
    publish_tasks,
    system,
)

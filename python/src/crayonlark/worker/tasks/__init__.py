"""Task modules are imported here so the worker registers them."""

from crayonlark.worker.tasks import notify_tasks, print_tasks, system  # noqa: F401

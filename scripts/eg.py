#!/usr/bin/env python3
"""Unified engineering-gates entry point.

Subcommands register on ``COMMANDS``. ``trace`` is EG-S2; ``checkpoint``
and ``identity`` are EG-S1. Adding a subcommand must not change ``trace``.
"""

import sys

sys.dont_write_bytecode = True

from egtrace.engine import run_trace, usage_error
from egcheckpoint.checkpoint import run_checkpoint
from egcheckpoint.identity import run_identity


COMMANDS = {
    "trace": run_trace,
    "checkpoint": run_checkpoint,
    "identity": run_identity,
}


def main(argv):
    if not argv or argv[0].startswith("-"):
        return usage_error("缺少子命令 trace")
    command = argv[0]
    handler = COMMANDS.get(command)
    if handler is None:
        return usage_error("未知子命令 %s" % command)
    return handler(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Unified engineering-gates entry point.

Only the ``trace`` subcommand is implemented here. Later specs register
further subcommands on ``COMMANDS`` without changing this dispatch shape.
"""

import sys

sys.dont_write_bytecode = True

from egtrace.engine import run_trace, usage_error


COMMANDS = {
    "trace": run_trace,
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

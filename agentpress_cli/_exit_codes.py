"""Centralized exit codes. Mirrors bin/lib/exit_codes.js so Node + Python
CLIs have identical contracts."""

OK = 0
ERRORS_FOUND = 1          # validation errors, unknown command, user abort
STRICT_OR_INTERNAL = 2    # strict-mode warning escalation OR internal error
FILE_NOT_FOUND = 3        # agents.txt missing where expected

'use strict';

// Centralised exit codes. Used by every verb module so the CLI's
// contract with shell users / CI is consistent.

module.exports = Object.freeze({
  OK: 0,
  ERRORS_FOUND: 1,          // generic non-success: validation errors, unknown command, user abort
  STRICT_OR_INTERNAL: 2,    // strict-mode warning escalation OR internal/unexpected error
  FILE_NOT_FOUND: 3,        // agents.txt missing where one was expected
});

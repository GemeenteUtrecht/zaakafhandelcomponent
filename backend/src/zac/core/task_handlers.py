"""
Define which form keys map to which handlers (urls/views).
"""

HANDLERS = {
    "zac:doRedirect": "core:redirect-task",
}

REVERSE_HANDLERS = {handler: form_key for form_key, handler in HANDLERS.items()}

import inspect


def process_docstring(app, what, name, obj, options, lines):
    from zac.accounts.permissions import Permission

    if inspect.isclass(obj) and issubclass(obj, Permission):
        # This causes import errors if left outside the function
        from zac.accounts.permissions import Permission, registry

        perms = []
        for perm in registry.values():
            if isinstance(perm, Permission):
                perms.append(perm)

        perms = sorted(perms, key=lambda perm: perm.name)
        for perm in perms:
            lines.append(".. py:data:: %s" % perm.name)
            lines.append("%s" % perm.description)
            lines.append("")

        # Return the extended docstring
    return lines


def setup(app):
    # Register the docstring processor with sphinx
    app.connect("autodoc-process-docstring", process_docstring)

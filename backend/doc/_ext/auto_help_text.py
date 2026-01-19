#
# Taken from https://gist.github.com/abulka/48b54ea4cbc7eb014308
#

import inspect

from django.utils.encoding import force_str
from django.utils.html import strip_tags


def process_docstring(app, what, name, obj, options, lines):
    # This causes import errors if left outside the function
    from django.db import models

    # Only look at objects that inherit from Django's base model class
    if inspect.isclass(obj) and issubclass(obj, models.Model):
        # Grab the field list from the meta class
        fields = obj._meta.get_fields()

        for field in fields:
            # Skip ManyToOneRel and ManyToManyRel fields which have no 'verbose_name' or 'help_text'
            if not hasattr(field, "verbose_name"):
                continue

            # Decode and strip any html out of the field's help text
            help_text = strip_tags(force_str(field.help_text))

            # Decode and capitalize the verbose name, for use if there isn't
            # any help text
            verbose_name = force_str(field.verbose_name).capitalize()

            if help_text:
                # Add the model field to the end of the docstring as a param
                # using the help text as the description
                lines.append(":param %s: %s" % (field.attname, help_text))
            else:
                # Add the model field to the end of the docstring as a param
                # using the verbose name as the description
                lines.append(":param %s: %s" % (field.attname, verbose_name))

            # Add the field's type to the docstring
            if isinstance(field, models.ForeignKey):
                to = field.related_model
                lines.append(
                    ":type %s: %s to :class:`~%s.%s`"
                    % (field.attname, type(field).__name__, to.__module__, to.__name__)
                )
            else:
                lines.append(":type %s: %s" % (field.attname, type(field).__name__))

    # Return the extended docstring
    return lines


def setup(app):
    # Register the docstring processor with sphinx
    app.connect("autodoc-process-docstring", process_docstring)

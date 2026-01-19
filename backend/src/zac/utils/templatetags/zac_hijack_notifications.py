from django import template

register = template.Library()


@register.inclusion_tag("hijack/notification.html", takes_context=True)
def hijack_notification(context):
    return {"context": context}

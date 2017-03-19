# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.template import Library
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from approval.models import Approve
from approval.views import get_object_from_item, get_object_or_null

register = Library()


@register.assignment_tag
def get_item_content_type_instance(item):
    try:
        return get_object_from_item(item)
    except:
        return None


@register.filter
def render_changes(approve):
    c_instance = get_object_from_item(approve)
    result = ''

    changes = approve.changes
    if changes:
        for key,value in changes.iteritems():
            before_string, after_string = get_item_change_from_approve_changes(c_instance, key, value)
            result += '<div class="i-checks"><input type="checkbox" name="{name}" id="{name}id" checked/> ' \
                      '<label for="{name}id"></label><b> "{key}": </b>' \
                      '{before}   -->   {after}</div>' \
                      .format(before=before_string, after=after_string, name=str(key), key=key)
    return mark_safe(result)


@register.filter
def notify_for_changes(item):
    result = ''
    item_instance = ContentType.objects.get_for_model(item)
    approve = Approve.objects.filter(item_content_type_id=item_instance.id, item_object_id=item.id, closed=False).first()
    if approve:
        result = '''
                    <div class="col-lg-12" style="margin-top: 10px">
                        <div class="alert alert-danger alert-dismissable">
                            <button aria-hidden="true" data-dismiss="alert" class="close" type="button">×</button>
                            <h4>{0}</h4>
                            <p>{1}</p>
                 '''.format(_("Below changes are on the queue to be applied to this item. Please wait for admin "
                              "to approve/reject these changes."), _('Changes request '))

        for key, value in approve.changes.iteritems():
            before_string, after_string = get_item_change_from_approve_changes(item, key, value)
            # result += '{0}: <b>"{1}" ---> "{2}"</b><br>'.format(key, before_string, after_string)
            result += '<b>{0}</b>: Change to<b> ----> "{1}"</b><br>'.format(key, after_string)

        result += '''   </div>
                    </div>
                  '''
    return mark_safe(result)


def get_item_change_from_approve_changes(c_instance, key, value):
    before_string = ''
    after_string = ''
    if isinstance(value, dict):
        i_type = ContentType.objects.filter(pk=value['content_type_id']).first()
        if i_type:
            i_instance = i_type.model_class().objects.filter(pk=value['object_id']).first()
            before_string = getattr(c_instance, key)
            after_string = i_instance
    elif isinstance(value, list):
        for i in value:
            i_type = get_object_or_null(ContentType, pk=i['content_type_id'])
            if i_type:
                i_instance = get_object_or_null(i_type.model_class(), pk=i['object_id'])
                after_string += i_instance.__str__() + ', '

    else:
        before_string = getattr(c_instance, key)
        after_string = value
    return before_string, after_string
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import QuerySet
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, _get_queryset
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from account.extra import get_profile_user
from main.main_decorators import profile_privilege_decorator
from models import Approve, ApprovedFieldsList
from notifications.signals import notify


def create_approval(applicator, item, verb, changes_dict, priority='low', description=''):
    profile = get_profile_user(applicator)
    if profile:
        if profile.user_type() == 'administrator':
            if not profile.is_agent:
                for c in changes_dict:
                    setattr(item, c, changes_dict[c])
                item.save()
                return None

    approve_fields_list = get_approve_fields_list(item)
    changes = {}
    for c in changes_dict:
        if c in approve_fields_list:
            x = changes_dict[c]
            if getattr(item, c) == x:
                continue
            if isinstance(x, QuerySet):
                x_changes = []
                for i in x:
                    c_id = ContentType.objects.get_for_model(i).id
                    o_id = i.id
                    x_changes.append({'content_type_id': c_id, 'object_id': o_id})
                changes[c] = x_changes
            else:
                try:
                    c_id = ContentType.objects.get_for_model(x).id
                    o_id = x.id
                    changes[c] = {'content_type_id': c_id, 'object_id': o_id}
                    print changes
                except AttributeError:
                    changes[c] = x
        else:
            setattr(item, c, changes_dict[c])
    item.save()

    if changes:
        approve, created = Approve.objects.get_or_create(item_content_type=ContentType.objects.get_for_model(item),
                                                         item_object_id=item.pk)
        approve.changes = changes
        approve.applicator = applicator
        approve.verb = verb
        approve.description = description
        approve.priority = priority
        approve.closed = False
        approve.save()
        return approve
    return None


def save_approval(approve, approve_list):
    approve_list = [str(i) for i in approve_list]
    o_type = ContentType.objects.filter(pk=approve.item_content_type_id).first()
    o_instance = o_type.model_class().objects.filter(pk=approve.item_object_id).first()
    print o_instance

    for key, value in approve.changes.iteritems():
        if key in approve_list:
            if isinstance(value, dict):
                c_type = get_object_or_null(ContentType, pk=value['content_type_id'])
                if c_type:
                    c_instance = get_object_or_null(c_type.model_class(), pk=value['object_id'])
                    setattr(o_instance, key, c_instance)
            elif isinstance(value, list):
                x = getattr(o_instance, key)
                c_list = []
                for i in value:
                    c_type = get_object_or_null(ContentType, pk=i['content_type_id'])
                    if c_type:
                        c_instance = get_object_or_null(c_type.model_class(), pk=i['object_id'])
                        c_list.append(c_instance)
                        # setattr(o_instance, key, c_instance)
                x = c_list
            else:
                setattr(o_instance, key, value)
    o_instance.save()
    approve.closed = True
    approve.save()


def get_approve_fields_list(item):
    item_instance = ContentType.objects.get_for_model(item)
    approve_fields_list = []
    approve_fields_list_instance = ApprovedFieldsList.objects.filter(item_content_type=item_instance).first()
    if approve_fields_list_instance:
        approve_fields_list = approve_fields_list_instance.fields
    return approve_fields_list


@profile_privilege_decorator(profile_type=['administrator'])
def manage_approvals(request, *args, **kwargs):
    user = request.user
    profile = get_profile_user(user)
    if profile.is_agent:
        raise Http404

    approve_items = Approve.objects.filter(closed=False).order_by('timestamp', 'priority')
    return render_to_response('approval/manage.html', locals(), RequestContext(request))


@profile_privilege_decorator(profile_type=['administrator'])
def action_on_approvals(request, *args, **kwargs):
    if not request.method == 'POST':
        return HttpResponseRedirect(reverse('approval:manage_approves'))

    user = request.user
    profile = get_profile_user(user)
    if profile.is_agent:
        raise Http404

    approve_id = kwargs.pop('approve_id', None)
    if not approve_id:
        raise Http404

    approve = Approve.objects.filter(pk=approve_id).first()
    request.session['redirect'] = True
    if approve:
        action_type = request.POST.get('action_type', 'accept')
        if action_type == 'reject':
            approve.closed = True
            approve.save()
            request.session['success'] = _('Requested modifications have been discarded')
            notify.send(request.user, recipient=approve.applicator, verb='changes rejected to be applied.',
                        description=_('Requested modifications have not been approved by admin.'))
        else:
            approve_list = []
            for i in request.POST.keys():
                if request.POST.get(i, '') == 'on':
                    approve_list.append(i)
            save_approval(approve, approve_list)
            request.session['success'] = _('Requested modifications have been approved.')
            notify.send(request.user, recipient=approve.applicator, verb='changes successfully applied.',
                        description=_('Requested modifications have been approved by admin.'))

    return HttpResponseRedirect(reverse('approval:manage_approves'))


def get_object_from_item(item):
    c_type = ContentType.objects.filter(pk=item.item_content_type_id).first()
    if c_type:
        return c_type.model_class().objects.filter(pk=item.item_object_id).first()
    return None


def get_object_or_null(klass, *args, **kwargs):
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None
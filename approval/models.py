from __future__ import unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from jsonfield import JSONField
from model_utils import Choices

from approval.managers import ApprovalQuerySet
from django.contrib.auth.models import User

try:
    from django.contrib.contenttypes import fields as generic
except ImportError:
    from django.contrib.contenttypes import generic

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now


class Approve(models.Model):
    PRIORITY = Choices('high', 'medium', 'low')
    priority = models.CharField(choices=PRIORITY, default=PRIORITY.low, max_length=20)
    applicator = models.ForeignKey(User, null=True, blank=True)
    item_content_type = models.ForeignKey(ContentType, related_name='item', db_index=True)
    item_object_id = models.CharField(max_length=255, db_index=True)
    item = generic.GenericForeignKey('item_content_type', 'item_object_id')
    changes = JSONField(null=True, blank=True)
    verb = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=now, db_index=True)
    objects = ApprovalQuerySet.as_manager()
    closed = models.BooleanField(default=False)

    class Meta:
        ordering = ('-timestamp', )
        unique_together = ('item_object_id', 'item_content_type')


class ApprovedFieldsList(models.Model):
    name = models.CharField(max_length=30, null=True, blank=True)
    item_content_type = models.OneToOneField(ContentType, related_name='item_fields')
    fields = JSONField(null=True, blank=True)

    def __unicode__(self):
        return self.name


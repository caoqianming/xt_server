from django.conf import settings
from rest_framework import serializers
from django.db.models import DecimalField
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property
from decimal import Decimal


class MyFilePathField(serializers.CharField):

    def to_representation(self, value):
        if 'http' in value:
            return str(value)
        return settings.BASE_URL + str(value)

class PositiveDecimalField(DecimalField):
    
    @cached_property
    def validators(self):
        return [MinValueValidator(Decimal('0.0'))] + super().validators
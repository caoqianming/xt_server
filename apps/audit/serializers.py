from apps.utils.serializers import CustomModelSerializer
from apps.audit.models import Standard, StandardItem, Company

class StandardSerializer(CustomModelSerializer):
    class Meta:
        model = Standard
        fields = "__all__"


class StandardItemSerializer(CustomModelSerializer):
    class Meta:
        model = StandardItem
        fields = "__all__"


class CompanySerializer(CustomModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
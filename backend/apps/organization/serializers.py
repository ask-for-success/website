from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Department, Position


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("id", "name", "description")


class DepartmentSerializer(serializers.ModelSerializer):
    positions = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ("id", "name", "description", "positions")

    @extend_schema_field(PositionSerializer(many=True))
    def get_positions(self, instance):
        positions = [
            position for position in instance.positions.all() if position.is_active
        ]
        return PositionSerializer(positions, many=True).data

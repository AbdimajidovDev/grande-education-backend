
from rest_framework import serializers


class DashboardKPISerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    total_leads_growth = serializers.CharField(allow_null=True)
    new_leads = serializers.IntegerField()
    active_admissions = serializers.IntegerField()
    active_admissions_growth = serializers.CharField()
    enrolled_rate = serializers.CharField()
    total_universities = serializers.IntegerField()
    total_programs = serializers.IntegerField()


class PipelineStagesSerializer(serializers.Serializer):
    CONSULTATION = serializers.IntegerField()
    SELECTION = serializers.IntegerField()
    EXAMS = serializers.IntegerField()
    DOCUMENTS = serializers.IntegerField()
    ARRIVAL = serializers.IntegerField()


class MonthlyTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    count = serializers.IntegerField()


class DirectionDistributionSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.IntegerField()


class DashboardOverviewSerializer(serializers.Serializer):
    kpi = DashboardKPISerializer()
    pipeline_stages = PipelineStagesSerializer()
    monthly_trends = MonthlyTrendSerializer(many=True)
    directions_distribution = DirectionDistributionSerializer(many=True)

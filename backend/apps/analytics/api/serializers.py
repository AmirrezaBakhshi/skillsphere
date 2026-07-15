from rest_framework import serializers


class DailyCountSerializer(serializers.Serializer):
    date = serializers.CharField()
    count = serializers.IntegerField()


class UserDashboardSerializer(serializers.Serializer):
    total_projects = serializers.IntegerField()
    projects_ready = serializers.IntegerField()
    projects_processing = serializers.IntegerField()
    projects_rejected = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    activity_last_14_days = DailyCountSerializer(many=True)


class ActiveUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    action_count = serializers.IntegerField()


class AdminDashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_projects = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    projects_by_status = serializers.DictField(child=serializers.IntegerField())
    signups_last_14_days = DailyCountSerializer(many=True)
    requests_last_14_days = DailyCountSerializer(many=True)
    most_active_users = ActiveUserSerializer(many=True)

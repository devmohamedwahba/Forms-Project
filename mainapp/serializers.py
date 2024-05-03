from rest_framework import serializers
from .models import *
from datetime import date
from django.contrib.auth.models import User, Group

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']

class ListUserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    class Meta:
        model = CustomUser
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'
        
class RequestMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestMethod
        fields = '__all__'
        
class RequestReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestReason
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        
# class DepartmentSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Department
#         fields = '__all__'
        
class DutySerializer(serializers.ModelSerializer):
    class Meta:
        model = Duty
        fields = '__all__'
        
class ClientJobRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientJobRole
        fields = '__all__'
        
class ClientSerializer(serializers.ModelSerializer):
    job_role = ClientJobRoleSerializer()
    class Meta:
        model = Client
        fields = '__all__'
        
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = '__all__'
        
class ListRequestSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer()
    duty = DutySerializer()
    notes = NoteSerializer()
    client_auto_id = ClientSerializer()
    request_method = RequestMethodSerializer()
    request_reason = RequestReasonSerializer()

    class Meta:
        model = Request
        fields = '__all__'
        
class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = '__all__'
        
class RequestNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestNote
        fields = '__all__'
        
class WorkLocationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLocations
        fields = '__all__'
        
class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = '__all__'
        
class VehicleSerializer(serializers.ModelSerializer):
    vehicle_type = VehicleTypeSerializer()
    plate_source = WorkLocationsSerializer()
    class Meta:
        model = Vehicle
        fields = '__all__'
        
class ListAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer()
    request_id = RequestSerializer()
    # request_attachment 
    class Meta:
        model = Attachment
        fields = '__all__'
        
class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'
        
class RequestAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestAttachment
        fields = '__all__'
        
class ShiftSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'
        
class RoutineSerializer(serializers.ModelSerializer):
    shift = ShiftSerializers()
    class Meta:
        model = Routine
        fields = '__all__'
    
class EmployeeRoutineSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer()
    routine = RoutineSerializer()
    class Meta:
        model = EmployeeRoutine
        fields = '__all__'

class AttendenceLogSerializer(serializers.ModelSerializer):
    employee_routine = EmployeeRoutineSerializer()
    class Meta:
        model = AttendenceLog
        fields = '__all__'
    # def get_queryset(self):
    #     today = date.today()
    #     queryset = AttendenceLog.objects.filter(today_date=today)
    #     return queryset
        
# class NotificationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Notification
#         fields = '__all__'
        
class ListEmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    work_location = WorkLocationsSerializer()
    class Meta:
        model = Employee
        fields = '__all__'
        
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        
class ActionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Actions
        fields = '__all__'

class CompanySecurityGuardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySecurityGuard
        fields = '__all__'
        
        
class CasesDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CasesDescription
        fields = '__all__'
        
class CasesActionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CasesActions
        fields = '__all__'

class CompanyCasesSerializer(serializers.ModelSerializer):
    # actions=ActionsSerializer(read_only=True,many=True)
    actions_id = serializers.PrimaryKeyRelatedField(queryset=Actions.objects.all(), write_only=True, many=True)

    class Meta:
        model = CompanyCases
        fields = ('employee', 'group', 'report_number', 'date_of_case', 'time_of_case_receive', 'city', 'duty', 'zone', 'case_summart', 'security_guard', 'company', 'employee_routine', 'comments', 'type_of_case', 'case_description', 'actions_id',)

    def create(self, validated_data):
        actions = validated_data.pop('actions_id')
        company_cases = CompanyCases.objects.create(**validated_data)
        for action in actions:
            company_cases.actions.add(action)
        return company_cases
    
    def update(self, instance, validated_data):
        actions = validated_data.pop('actions_id', None)
        if actions is not None:
            for action in actions:
                instance.actions.add(action)

        return super().update(instance, validated_data)
    
class VehicleFailuresSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleFailures
        fields = '__all__'

class ListVehicleFailuresSerializer(serializers.ModelSerializer):
    case_city = WorkLocationsSerializer()
    employee = EmployeeSerializer()
    group = GroupSerializer()
    company = CompanySerializer()
    duty = DutySerializer()
    vehicle = VehicleSerializer()
    class Meta:
        model = VehicleFailures
        fields = '__all__'

class ListCompanyAttendanceSerializer(serializers.ModelSerializer):
    city = WorkLocationsSerializer()
    employee = EmployeeSerializer()
    group = GroupSerializer()
    company = CompanySerializer()
    duty = DutySerializer()
    vehicle = VehicleSerializer()
    class Meta:
        model = CompanyAttendance
        fields = '__all__'

class ListCompanyCasesSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer()
    city = WorkLocationsSerializer()
    group = GroupSerializer()
    security_guard = CompanySecurityGuardSerializer()
    case_description = CasesDescriptionSerializer()
    company = CompanySerializer()
    duty = DutySerializer()

    class Meta:
        model = CompanyCases
        fields = '__all__'

class CallnameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Callname
        fields = '__all__'

class CompanyAttendanceSerializer(serializers.ModelSerializer):
    # actions=ActionsSerializer(read_only=True,many=True)
    actions_id = serializers.PrimaryKeyRelatedField(queryset=Actions.objects.all(), write_only=True, many=True)

    class Meta:
        model = CompanyAttendance
        fields = ('employee', 'company', 'group', 'city', 'duty', 'city', 'duty', 'vehicle', 'employee_routine', 'callname', 'date', 'milage_start_km', 'milage_finish_km', 'spend_time', 'comments', 'actions_id',)

    def create(self, validated_data):
        actions = validated_data.pop('actions_id')
        company_cases = CompanyAttendance.objects.create(**validated_data)
        for action in actions:
            company_cases.actions.add(action)
        return company_cases
    
    def update(self, instance, validated_data):
        actions = validated_data.pop('actions_id', None)
        if actions is not None:
            for action in actions:
                instance.actions.add(action)

        return super().update(instance, validated_data)
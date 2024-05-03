from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import django
from django.core.exceptions import ValidationError
import datetime
from django.contrib.auth.models import Group
from notifications.base.models import AbstractNotification
from django.contrib.auth.models import AbstractUser


class WorkLocations(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return self.address

class CustomUser(AbstractUser):
    number = models.CharField(max_length=255, null=True, blank=True, default=None)
    email = models.EmailField(null=True, blank=True, default=None)
    work_location = models.ForeignKey(WorkLocations, on_delete=models.CASCADE,null=True, blank=True,)
    is_employee = models.BooleanField(default=False)

    def get_full_name(self):
        
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return ""

class Company(models.Model):
    name = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class Employee(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    number = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True, default=None)
    work_location = models.ForeignKey(WorkLocations, on_delete=models.CASCADE, null=True, blank=True)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return self.username

class Duty(models.Model):
    duty_assigned_employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=255)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return (f"Duty for {self.duty_assigned_employee}")
    
class ClientJobRole(models.Model):
    name = models.CharField(max_length=255)
    is_trash = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Client(models.Model):
    status = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    job_grade = models.CharField(max_length=255)
    job_role = models.ForeignKey(ClientJobRole, on_delete=models.CASCADE, null=True, blank=True)
    head_office_name = models.CharField(max_length=255)
    headquarter_name = models.CharField(max_length=255)
    main_headquarter_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20)
    birth_date = models.DateField()
    UID = models.CharField(max_length=255, unique=True)
    id_number = models.CharField(max_length=255, unique=True)
    designation_date = models.DateField()
    work_location = models.ForeignKey(WorkLocations, on_delete=models.CASCADE)
    email = models.CharField(max_length=255, null=True, blank=True)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return self.name

class Note(models.Model):
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    is_trash = models.BooleanField(default=False)

    def __str__ (self):
        return (f"Note of {self.created_by}")

class RequestMethod(models.Model):
    name = models.CharField(max_length=250, unique=True)
    is_trash = models.BooleanField(default=False)

class RequestReason(models.Model):
    name = models.CharField(max_length=250, unique=True)
    is_trash = models.BooleanField(default=False)
    
class Request(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ac", _("Active")
        IN_ACTIVE = "in", _("Inactive")
    duty = models.ForeignKey('mainapp.Duty', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    # department = models.ForeignKey('mainapp.Department', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    #
    notes = models.ForeignKey('mainapp.Note', on_delete=models.CASCADE)
    client_auto_id = models.ForeignKey('mainapp.Client', on_delete=models.CASCADE, null=True, blank=True)
    client_hq = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.ACTIVE
    )
    client_city = models.CharField(max_length=255, null=True, blank=True)
    request_date = models.DateField(default=django.utils.timezone.now)
    request_time = models.TimeField(default=django.utils.timezone.now)
    request_method = models.ForeignKey(RequestMethod, on_delete=models.CASCADE)
    corresponding_id = models.CharField(max_length=100, null=True, blank=True)
    receive_date_time = models.DateTimeField(auto_now_add=True)
    is_high_priority = models.BooleanField(null=True, blank=True)
    request_reason = models.ForeignKey(RequestReason, on_delete=models.CASCADE)
    requirement = models.TextField(null=True, blank=True)
    attachments = models.TextField(null=True, blank=True)
    attachment_type = models.CharField(max_length=255, null=True, blank=True)
    attachment_count = models.IntegerField(null=True, blank=True)
    consoles_request_status = models.CharField(max_length=255, null=True, blank=True)
    result = models.CharField(max_length=255, null=True, blank=True)
    action_on_system_a = models.CharField(max_length=255, null=True, blank=True)
    request_id_on_system_a = models.IntegerField(null=True, blank=True)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return (f"Request for {self.employee}")

class RequestNote(models.Model):
    note = models.ForeignKey('mainapp.Note', on_delete=models.CASCADE)
    request = models.ForeignKey('mainapp.Request', on_delete=models.CASCADE)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return (f"Request for {self.note}")

class Attachment(models.Model):
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file_name = models.FileField(upload_to='files/')
    upload_date = models.DateTimeField(auto_now_add=True)
    is_trash = models.BooleanField(default=False)
    request_id = models.ForeignKey(Request,on_delete=models.CASCADE)
    
    # def __str__ (self):
    #     return self.file_name

class RequestAttachment(models.Model):
    request = models.ForeignKey('mainapp.Request', on_delete=models.CASCADE)
    attachment = models.ForeignKey('mainapp.Attachment', on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    upload_date = models.DateField(auto_now_add=True)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return (f"Request for {self.attachment}")

class Shift(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_trash = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name}"

class Routine(models.Model):
    class ShiftType(models.TextChoices):
        ON_SITE = "os", _("OnSide")
        ON_REMOTE = "or", _("OnRemote")
    
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, unique=True)
    start_time = models.TimeField() 
    break_time = models.DurationField(null=True, blank=True) 
    end_time = models.TimeField()
    leave_type = models.CharField(max_length=2, choices=ShiftType.choices, default=ShiftType.ON_SITE
    )
    is_trash = models.BooleanField(default=False)
    def clean(self):
        if self.break_time:
            if self.break_time > (self.end_time - self.start_time):
                raise ValidationError(_("Break time duration cannot exceed shift duration."))

            if self.break_time < 0:
                raise ValidationError(_("Break time duration cannot be negative."))

        super().clean()

    def __str__(self):
        return f"Routine of {self.shift.name}"

class EmployeeRoutine(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    is_trash = models.BooleanField(default=False)
    
    def __str__ (self):
        return (f"{self.routine.shift.name} Shift of {self.employee}")
    
class EmployeeLeaves(models.Model):
    class LeaveStatus(models.TextChoices):
        SICK_LEAVE = "sl", _("SickLeave")
        CASUAL_LEAVE = "cl", _("CasualLeave")
        OTHERS = "ol", _("OthersLeave")
        
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=2, choices=LeaveStatus.choices, default=LeaveStatus.CASUAL_LEAVE
    )
    is_trash = models.BooleanField(default=False)
    
class AttendenceLog(models.Model):   
    class Status(models.TextChoices):
        PRESENT = "p", _("Present")
        ABSENT = "a", _("Absent")
    
    employee_routine = models.ForeignKey(EmployeeRoutine, on_delete=models.CASCADE)
    first_in = models.TimeField(auto_now=False)
    last_out = models.TimeField(auto_now=False, null=True, blank=True)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.ABSENT
    )
    is_trash = models.BooleanField(default=False)
    today_date = models.DateField(null=True, blank=True)
    
    def __str__ (self):
        return (f"Attendence of {self.employee_routine.employee}")

class VehicleType(models.Model):
    name = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class Vehicle(models.Model):
    name = models.CharField(max_length=200)
    plate_number = models.IntegerField()
    plate_type = models.CharField(max_length=200)
    plate_source = models.ForeignKey(WorkLocations, on_delete=models.CASCADE)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE)
    vehicle_year = models.IntegerField()
    is_trash = models.BooleanField(default=False)

class VehicleFailures(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    case_city = models.ForeignKey(WorkLocations, on_delete=models.CASCADE)
    duty = models.ForeignKey(Duty, on_delete=models.CASCADE, null=True, blank=True)
    employee_routine = models.ForeignKey(EmployeeRoutine, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    report_number = models.CharField(max_length=200)
    type = models.CharField(max_length=200)
    details = models.TextField()
    vehicle_replace = models.BooleanField(default=False)
    is_trash = models.BooleanField(default=False)

class CompanySecurityGuard(models.Model):
    name = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    nationality = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class CasesDescription(models.Model):
    name = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class Actions(models.Model):
    name = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class CasesActions(models.Model):
    action = models.ForeignKey(Actions, on_delete=models.CASCADE)
    time_stamp = models.TimeField(default=django.utils.timezone.now().time())
    is_trash = models.BooleanField(default=False)

    def __str__(self):
        return self.action.name
 
class CompanyCases(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    report_number = models.CharField(max_length=200)
    date_of_case = models.DateTimeField(auto_now_add=True)
    time_of_case_receive = models.TimeField(default=datetime.time(0, 0))
    city = models.ForeignKey(WorkLocations, on_delete=models.CASCADE)
    duty = models.ForeignKey(Duty, on_delete=models.CASCADE, null=True, blank=True)
    zone = models.CharField(max_length=200)
    case_summart = models.TextField()
    security_guard = models.ForeignKey(CompanySecurityGuard, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee_routine = models.ForeignKey(EmployeeRoutine, on_delete=models.CASCADE)
    comments = models.TextField()
    type_of_case = models.CharField(max_length=200)
    actions = models.ManyToManyField(Actions, null=True, blank=True)
    case_description = models.ForeignKey(CasesDescription, on_delete=models.CASCADE)
    is_trash = models.BooleanField(default=False)

class Callname(models.Model):
    name = models.CharField(max_length=200)
    is_trash = models.BooleanField(default=False)

class CompanyAttendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    city = models.ForeignKey(WorkLocations, on_delete=models.CASCADE)
    duty = models.ForeignKey(Duty, on_delete=models.CASCADE, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    employee_routine = models.ForeignKey(EmployeeRoutine, on_delete=models. CASCADE)
    callname = models.ForeignKey(Callname, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    milage_start_km = models.IntegerField(null=True, blank=True)
    milage_finish_km = models.IntegerField(null=True, blank=True)
    spend_time = models.IntegerField(null=True, blank=True)
    comments = models.TextField()   
    actions = models.ManyToManyField(Actions)
    is_trash = models.BooleanField(default=False)

    @property
    def milage_calculation(self):
        if self.milage_finish_km is not None and self.milage_start_km is not None and self.spend_time is not None:
            milage_calculation = (self.milage_finish_km - self.milage_start_km) * self.spend_time
            return milage_calculation
        else:
            return None

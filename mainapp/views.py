from django.http import JsonResponse, HttpResponse
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render, redirect
from .models import *
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .serializers import *
from rest_framework.decorators import api_view
from django.contrib.auth.models import User
from django.http import (HttpResponse, HttpResponseBadRequest, 
                         HttpResponseForbidden)
from django.contrib.auth.models import Group, Permission, ContentType
from django.utils import timezone
from django.db import IntegrityError
from django.utils.translation import activate


def set_default_language(request):
    if 'ar' and 'en' not in request.path:
        activate('ar')
        request.LANGUAGE_CODE = 'ar'
    return None

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def forbidden_request(request):
    activate('ar')
    return render(request, '403.html')

def switch_language(request):
    if 'language' in request.GET:
        request.session['django_language'] = request.GET['language']
    return redirect(request.GET.get('next', '/'))

def home(request):
    set_default_language(request)
    if request.user.is_authenticated:
        return redirect(f'{request.LANGUAGE_CODE}/dashboard')
    
    message = None
    
    if request.method == 'POST':
        username = request.POST.get("uname")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            user.user_permissions.set(Permission.objects.all())
            messages.success(request, 'Login successful.')
            return redirect(f'{request.LANGUAGE_CODE}/dashboard')
        
        elif user is not None and user.is_active:
            try:
                employee_routine = EmployeeRoutine.objects.get(employee__user=user, is_active=True)
            except EmployeeRoutine.DoesNotExist:
                login(request, user)
                return redirect(f'{request.LANGUAGE_CODE}/dashboard')
            try:
                attendance_log, created = AttendenceLog.objects.get_or_create(
                    employee_routine=employee_routine,
                )
            except IntegrityError:
                attendance_log = AttendenceLog(employee_routine=employee_routine)
            if attendance_log.first_in is None:
                attendance_log.first_in = timezone.now()
            attendance_log.status = AttendenceLog.Status.PRESENT
            attendance_log.today_date = date.today()
            attendance_log.save()
            
            user_permissions = list(user.user_permissions.values_list('codename', flat=True))
            print(user_permissions)
            user_groups = list(user.groups.values_list('name', flat=True))
            print(user_groups)
            
            request.session['user_permissions'] = user_permissions
            request.session['user_groups'] = user_groups
            
            login(request, user)
            messages.success(request, 'Login successful.')
            
            return redirect(f'{request.LANGUAGE_CODE}/dashboard')
        elif user is not None and not user.is_active:
            message = _('You are not an active user')
        else:
            message = _('Invalid username or password')
    
    return render(request, 'sign-in.html', {'message': message})

@login_required(login_url='/')
def logout_view(request):
    if request.user.is_superuser:
        logout(request)
        return redirect(f'/')
    else:
        try:
            employee_routine = EmployeeRoutine.objects.get(employee__user=request.user, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            pass
        else:
            try:
                attendance_log = AttendenceLog.objects.get(employee_routine=employee_routine)
                attendance_log.last_out = timezone.now()
                attendance_log.save()
            except AttendenceLog.DoesNotExist:
                pass
        
        logout(request)
        return redirect(f'/')

@login_required(login_url='/')
def create_employee(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_employee'):
        return HttpResponseForbidden(_("You don't have permission to create employees."))

    else:
        error_messages = []
        success_messages = []
        
        users = CustomUser.objects.filter(is_active=True)
        worklocations = WorkLocations.objects.filter(is_trash=False)
        
        if request.method == 'POST':
            try:
                create_user_id = request.POST.get('create_user_id')
                employee_worklocations_id = request.POST.get('employee_worklocations_id')

                user = get_object_or_404(CustomUser, id=create_user_id)
                worklocation = get_object_or_404(WorkLocations, id=employee_worklocations_id)
                
                Employee.objects.create(
                    user=user,
                    work_location=worklocation,
                    name=user.first_name,
                    username=user.username,
                    password=user.password,
                    email=user.email
                )
                success_messages.append(_('Employee created successfully.'))

                return redirect(f'{request.LANGUAGE_CODE }/create_employee')

            except ValidationError as e:
                error_messages.append(e.message)

            except User.DoesNotExist:
                error_messages.append(_('Failed to create employee. User does not exist.'))

            except WorkLocations.DoesNotExist:
                error_messages.append(_('Failed to create employee. Work location does not exist.'))

            except Exception as e:
                error_messages.append(_('Failed to create employee:') + str(e))
        
        return render(request, 'create-employee.html', {'worklocations': worklocations, 'users': users, 'error_messages': error_messages, 'success_messages': success_messages})

@login_required(login_url='/')
def list_all_employee(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_employee'):
        return HttpResponseForbidden(_("You don't have permission to view employees."))

    else:
        employees = Employee.objects.filter(is_trash=False)
        return render(request, 'all-employee.html', {'employees': employees})

@login_required(login_url='/')
def single_employee(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_employee'):
        return HttpResponseForbidden(_("You don't have permission to view employees."))
    else:
        employee = Employee.objects.get(id=pk)
        return render(request, 'single-employee.html', {'employee': employee})

@login_required(login_url='/')
def update_employee(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_employee'):
        return HttpResponseForbidden(_("You don't have permission to change employees."))
    else:
        error_messages = []
        success_messages = []

        users = CustomUser.objects.filter(is_active=True)
        worklocations = WorkLocations.objects.filter(is_trash=False)

        employee = get_object_or_404(Employee, id=pk)

        if request.method == 'POST':
            try:
                update_user_id = request.POST.get('update_user_id')
                employee_worklocations_id = request.POST.get('update_employee_worklocations_id')

                update_user = get_object_or_404(CustomUser, id=update_user_id)
                update_worklocation = get_object_or_404(WorkLocations, id=employee_worklocations_id)

                employee.user = update_user
                employee.work_location = update_worklocation
                employee.name = update_user.first_name
                employee.username = update_user.username
                employee.password = update_user.password
                employee.email = update_user.email
                employee.save()

                success_messages.append(_('Employee updated successfully.'))

                return redirect(f'/update_employee/{employee.id}/')

            except ValidationError as e:
                error_messages.append(e.message)

            except User.DoesNotExist:
                error_messages.append(_('User does not exist.'))

            except WorkLocations.DoesNotExist:
                error_messages.append(_('Work location does not exist.'))

            except Exception as e:
                error_messages.append(_('Failed to update employee:') + str(e))

        return render(request, 'update-employee.html', {
            'worklocations': worklocations,
            'users': users,
            'employee': employee,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_employee(request, pk):
    if not request.user.has_perm('mainapp.delete_employee'):
        return HttpResponseForbidden(_("You don't have permission to delete employees."))
    else:
        employee = Employee.objects.get(id=pk)
        employee.delete()
        return redirect (f'/all_employee')

@login_required(login_url='/')
def create_shift(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_shift'):
        return HttpResponseForbidden(_("You don't have permission to Create Shift."))
    else:
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                create_shift_name = request.POST.get('create_shift_name')

                Shift.objects.create(name=create_shift_name)
                success_messages.append(_('Shift created successfully.'))
            except ValueError as e:
                error_messages.append(str(e))
            except Exception as e:
                error_messages.append(_('Failed to create Shift:') + str(e))

        return render(request, 'create-shift.html', {
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def create_action(request):
    set_default_language(request)
    error_messages = []
    success_messages = []

    if request.method == 'POST':
        try:
            create_action_name = request.POST.get('create_action_name')

            Actions.objects.create(name=create_action_name)
            success_messages.append(_('Actions created successfully.'))
        except ValueError as e:
            error_messages.append(str(e))
        except Exception as e:
            error_messages.append(_('Failed to create Actions:') + str(e))

    return render(request, 'create-action.html', {
        'error_messages': error_messages,
        'success_messages': success_messages
    })
    
@login_required(login_url='/')
def list_all_action(request):
    set_default_language(request)
    actions = Actions.objects.filter(is_trash=False)
    return render(request, 'all-actions.html', {'actions': actions})

@login_required(login_url='/')
def single_action(request, pk):
    set_default_language(request)
    action = Actions.objects.get(id=pk)
    return render(request, 'single-action.html', {'action': action})

@login_required(login_url='/')
def update_action(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_actions'):
        return HttpResponseForbidden(_("You don't have permission to Update Actions."))
    else:
        error_messages = []
        success_messages = []

        try:
            action = Actions.objects.get(id=pk)

            if request.method == 'POST':
                update_action_name = request.POST.get('update_action_name')
                action.name = update_action_name
                action.save()
                success_messages.append(_('Actions updated successfully.'))
                return redirect(f'{request.LANGUAGE_CODE}/all_action')

        except Actions.DoesNotExist:
            error_messages.append(_('Actions does not exist.'))
        except Exception as e:
            error_messages.append(_('Failed to update Actions:') + str(e))

        return render(request, 'update-action.html', {
            'action': action,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_action(request, pk):
    if not request.user.has_perm('mainapp.delete_actions'):
        return HttpResponseForbidden(_("You don't have permission to delete action."))
    else:
        action = Actions.objects.get(id=pk)
        action.is_trash=True
        action.save()
        return redirect ('/all_action')

@login_required(login_url='/')
def list_all_shift(request):
    set_default_language(request)
    shifts = Shift.objects.filter(is_trash=False)
    return render(request, 'all-shift.html', {'shifts': shifts})

@login_required(login_url='/')
def single_shift(request, pk):
    set_default_language(request)
    shift = Shift.objects.get(id=pk)
    return render(request, 'single-shift.html', {'shift': shift})

@login_required(login_url='/')
def update_shift(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_shift'):
        # return HttpResponseForbidden(_("You don't have permission to Update Shift."))
        return render(request, '403.html')
    else:
        error_messages = []
        success_messages = []

        try:
            shift = Shift.objects.get(id=pk)

            if request.method == 'POST':
                update_department_name = request.POST.get('update_shift_name')
                shift.name = update_department_name
                shift.save()
                success_messages.append(_('Shift updated successfully.'))
                return redirect(f'/all_shift')

        except Shift.DoesNotExist:
            error_messages.append(_('Shift does not exist.'))
        except Exception as e:
            error_messages.append(_('Failed to update Shift:') + str(e))

        return render(request, 'update-shift.html', {
            'shift': shift,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_shift(request, pk):
    if not request.user.has_perm('mainapp.delete_shift'):
        # return HttpResponseForbidden(_("You don't have permission to delete shift."))
        return render(request, '403.html')
    else:
        shift = Shift.objects.get(id=pk)
        shift.delete()
        return redirect (f'/ar/all_shift')

@login_required(login_url='/')
def create_vehicle(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_vehicle'):
        return HttpResponseForbidden(_("You don't have permission to Create Vehicle."))
    else:
        error_messages = []
        success_messages = []
        worklocations = WorkLocations.objects.filter(is_trash=False)
        vehicle_types = VehicleType.objects.filter(is_trash=False)

        if request.method == 'POST':
            try:
                create_vehicle_name = request.POST.get('create_vehicle_name')
                create_vehicle_plate_number = request.POST.get('create_vehicle_plate_number')
                create_vehicle_plate_type = request.POST.get('create_vehicle_plate_type')
                create_vehicle_type_id = request.POST.get('create_vehicle_type_id')
                create_vehicle_plate_source_id = request.POST.get('create_vehicle_plate_source_id')
                create_vehicle_year = request.POST.get('create_vehicle_year')
                create_vehicle_type = VehicleType.objects.get(id=create_vehicle_type_id)
                create_vehicle_plate_source = WorkLocations.objects.get(id=create_vehicle_plate_source_id)
                Vehicle.objects.create(name=create_vehicle_name, plate_number=create_vehicle_plate_number, plate_type=create_vehicle_plate_type, plate_source=create_vehicle_plate_source, vehicle_type=create_vehicle_type, vehicle_year=create_vehicle_year)
                success_messages.append(_('Vehicle created successfully.'))
            except ValueError as e:
                error_messages.append(str(e))
            except Exception as e:
                error_messages.append(_('Failed to create Vehicle:') + str(e))

        return render(request, 'create-vehicle.html', {
            'error_messages': error_messages,
            'success_messages': success_messages,
            'worklocations': worklocations,
            'vehicle_types': vehicle_types,
        })

@login_required(login_url='/')
def list_all_vehicle(request):
    set_default_language(request)
    vehicles = Vehicle.objects.filter(is_trash=False)
    return render(request, 'all-vehicle.html', {'vehicles': vehicles})

@login_required(login_url='/')
def single_vehicle(request, pk):
    set_default_language(request)
    vehicle = Vehicle.objects.get(id=pk)
    return render(request, 'single-vehicle.html', {'vehicle': vehicle})

@login_required(login_url='/')
def update_vehicle(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_vehicle'):
        # return HttpResponseForbidden(_("You don't have permission to Update Vehicle."))
        return render(request, '403.html')
    else:
        error_messages = []
        success_messages = []
        try:
            vehicle_types = VehicleType.objects.filter(is_trash=False)
            worklocations = WorkLocations.objects.filter(is_trash=False)
            vehicle = Vehicle.objects.get(id=pk)
            if request.method == 'POST':
                update_vehicle_name = request.POST.get('update_vehicle_name')
                update_vehicle_plate_number = request.POST.get('update_vehicle_plate_number')
                update_vehicle_plate_type = request.POST.get('update_vehicle_plate_type')
                update_vehicle_type_id = request.POST.get('update_vehicle_type_id')
                update_vehicle_plate_source_id = request.POST.get('update_vehicle_plate_source_id')
                update_vehicle_year = request.POST.get('update_vehicle_year')
                update_vehicle_type = VehicleType.objects.get(id=update_vehicle_type_id)
                update_vehicle_plate_source = WorkLocations.objects.get(id=update_vehicle_plate_source_id)
                vehicle.name = update_vehicle_name
                vehicle.plate_number = update_vehicle_plate_number
                vehicle.plate_type = update_vehicle_plate_type
                vehicle.plate_source = update_vehicle_plate_source
                vehicle.vehicle_type = update_vehicle_type
                vehicle.vehicle_year = update_vehicle_year
                vehicle.save()
                success_messages.append(_('Vehicle updated successfully.'))
        except Vehicle.DoesNotExist:
            error_messages.append(_('Vehicle does not exist.'))
        except Exception as e:
            error_messages.append(_('Failed to update Vehicle:') + str(e))
        return render(request, 'update-vehicle.html', {
            'vehicle': vehicle,
            'error_messages': error_messages,
            'worklocations': worklocations,
            'vehicle_types': vehicle_types,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_vehicle(request, pk):
    if not request.user.has_perm('mainapp.delete_vehicle'):
        # return HttpResponseForbidden(_("You don't have permission to delete vehicle."))
        return render(request, '403.html')
    vehicle = Vehicle.objects.get(id=pk)
    vehicle.delete()
    return redirect (f'/ar/all_vehicle')

@login_required(login_url='/')
def create_vehicle_type(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_vehicletype'):
        return HttpResponseForbidden(_("You don't have permission to Create Vehicle Type."))

    else:
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                create_vehicle_type_name = request.POST.get('create_vehicle_type_name')

                VehicleType.objects.create(name=create_vehicle_type_name)
                success_messages.append(_('Vehicle Type created successfully.'))
            except ValueError as e:
                error_messages.append(str(e))
            except Exception as e:
                error_messages.append(_('Failed to create Vehicle Type:') + str(e))

        return render(request, 'create-vehicle-type.html', {
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def list_all_vehicle_type(request):
    set_default_language(request)
    vehicle_types = VehicleType.objects.filter(is_trash=False)
    return render(request, 'all-vehicle-type.html', {'vehicle_types': vehicle_types})

@login_required(login_url='/')
def single_vehicle_type(request, pk):
    set_default_language(request)
    vehicle_type = VehicleType.objects.get(id=pk)
    return render(request, 'single-vehicle-type.html', {'vehicle_type': vehicle_type})

@login_required(login_url='/')
def update_vehicle_type(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_vehicletype'):
        return HttpResponseForbidden(_("You don't have permission to Update Vehicle Type."))
    error_messages = []
    success_messages = []

    try:
        vehicle_type = VehicleType.objects.get(id=pk)

        if request.method == 'POST':
            update_vehicle_type_name = request.POST.get('update_vehicle_type_name')
            vehicle_type.name = update_vehicle_type_name
            vehicle_type.save()
            success_messages.append(_('VehicleType updated successfully.'))
            return redirect(f'{request.LANGUAGE_CODE }/all_vehicle_type')

    except VehicleType.DoesNotExist:
        error_messages.append(_('VehicleType does not exist.'))
    except Exception as e:
        error_messages.append(_('Failed to update VehicleType:') + str(e))

    return render(request, 'update-vehicle-type.html', {
        'vehicle_type': vehicle_type,
        'error_messages': error_messages,
        'success_messages': success_messages
    })

@login_required(login_url='/')
def delete_vehicle_type(request, pk):
    if not request.user.has_perm('mainapp.delete_vehicletype'):
        return HttpResponseForbidden(_("You don't have permission to delete Vehicle Type."))
    else:
        vehicle_type = VehicleType.objects.get(id=pk)
        vehicle_type.is_trash=True
        vehicle_type.save()
        return redirect ('/all_vehicle_type')
# from here
@login_required(login_url='/')
def create_company_cases(request): 
    set_default_language(request)   
    if not request.user.has_perm('mainapp.add_companycases'):
        return HttpResponseForbidden(_("You don't have permission to Create Company Cases."))
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee first."))
        
        worklocations = WorkLocations.objects.filter(is_trash=False)
        dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        
        try:
            group = Group.objects.get(user=employee.user)
        except Group.DoesNotExist:
            return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
        try:
            routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
        cases_descs = CasesDescription.objects.filter(is_trash=False)
        notes = Note.objects.filter(is_trash=False)
        companys = Company.objects.filter(is_trash=False)
        company_guards = CompanySecurityGuard.objects.filter(is_trash=False)
        actions = Actions.objects.filter(is_trash=False)
    
    return render(request, 'create-company-cases.html', {
        'employee': employee, 
        'dutys': dutys, 
        'cases_descs': cases_descs, 
        'notes': notes, 
        'actions': actions, 
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys, 
        'company_guards': company_guards
    })

@login_required(login_url='/')
def update_company_cases(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_companycases'):
        # return HttpResponseForbidden(_("You don't have permission to Update Company Cases."))
        return render(request, '403.html')
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee profile first."))
        
        worklocations = WorkLocations.objects.filter(is_trash=False)
        
        try:
            dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        except Duty.DoesNotExist:
            return HttpResponseForbidden(_("No duty assigned to the employee. Please assign a duty first."))
        
        try:
            group = Group.objects.get(user=employee.user)
        except Group.DoesNotExist:
            return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
        
        try:
            routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
        
        try:
            company_case = CompanyCases.objects.get(id=pk)
        except CompanyCases.DoesNotExist:
            return HttpResponseForbidden(_("Company case does not exist."))
        
        cases_descs = CasesDescription.objects.filter(is_trash=False)
        notes = Note.objects.filter(is_trash=False)
        companys = Company.objects.filter(is_trash=False)
        company_guards = CompanySecurityGuard.objects.filter(is_trash=False)
        actions = Actions.objects.filter(is_trash=False)
    
    return render(request, 'update-company-cases.html', {
        'employee': employee, 
        'dutys': dutys, 
        'cases_descs': cases_descs, 
        'notes': notes, 
        'actions': actions, 
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys, 
        'company_guards': company_guards, 
        'company_case': company_case
    })

@login_required(login_url='/')
def create_company_attendance(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_companyattendance'):
        return HttpResponseForbidden(_("You don't have permission to Create Company Attendance."))
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee profile first."))
        
        worklocations = WorkLocations.objects.filter(is_trash=False)
        
        try:
            dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        except Duty.DoesNotExist:
            return HttpResponseForbidden(_("No duty assigned to the employee. Please assign a duty first."))
        
        try:
            group = Group.objects.get(user=employee.user)
        except Group.DoesNotExist:
            return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
        
        try:
            routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
        
        actions = Actions.objects.filter(is_trash=False)
        vehicles = Vehicle.objects.filter(is_trash=False)
        companys = Company.objects.filter(is_trash=False)
        callnames = Callname.objects.filter(is_trash=False)
    
    return render(request, 'create-company-attendance.html', {
        'employee': employee, 
        'dutys': dutys, 
        'vehicles': vehicles,
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys, 
        'actions': actions, 
        'callnames': callnames
    })

@login_required(login_url='/')
def update_company_attendance(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_companyattendance'):
        # return HttpResponseForbidden(_("You don't have permission to Update Company Attendance."))
        return render(request, '403.html')
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee profile first."))
        
        try:
            company_attendance = CompanyAttendance.objects.get(id=pk)
        except CompanyAttendance.DoesNotExist:
            return HttpResponseForbidden(_("Company attendance record does not exist."))
        
        worklocations = WorkLocations.objects.filter(is_trash=False)
        
        try:
            dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        except Duty.DoesNotExist:
            return HttpResponseForbidden(_("No duty assigned to the employee. Please assign a duty first."))
        
        try:
            group = Group.objects.get(user=employee.user)
        except Group.DoesNotExist:
            return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
        
        try:
            routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
        
        actions = Actions.objects.filter(is_trash=False)
        vehicles = Vehicle.objects.filter(is_trash=False)
        companys = Company.objects.filter(is_trash=False)
        callnames = Callname.objects.filter(is_trash=False)
    
    return render(request, 'update-company-attendance.html', {
        'employee': employee, 
        'dutys': dutys, 
        'vehicles': vehicles,
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys, 
        'actions': actions, 
        'callnames': callnames, 
        'company_attendance': company_attendance
    })

@login_required(login_url='/')
def create_vehicle_failures(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_vehiclefailures'):
        return HttpResponseForbidden(_("You don't have permission to Create Vehicle Failures."))
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee profile first."))
        
        worklocations = WorkLocations.objects.filter(is_trash=False)
        
        try:
            dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        except Duty.DoesNotExist:
            return HttpResponseForbidden(_("No duty assigned to the employee. Please assign a duty first."))
        
        try:
            group = Group.objects.get(user=employee.user)
        except Group.DoesNotExist:
            return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
        
        try:
            routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
        except EmployeeRoutine.DoesNotExist:
            return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
        
        vehicles = Vehicle.objects.filter(is_trash=False)
        companys = Company.objects.filter(is_trash=False)
    
    return render(request, 'create-vehicle-failure.html', {
        'employee': employee, 
        'dutys': dutys, 
        'vehicles': vehicles,
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys
    })

@login_required(login_url='/')
def create_company(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_company'):
        return HttpResponseForbidden(_("You don't have permission to Create Company."))
    else:
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                create_company_name = request.POST.get('create_company_name')

                Company.objects.create(name=create_company_name)
                success_messages.append(_('Company created successfully.'))
            except ValueError as e:
                error_messages.append(str(e))
            except Exception as e:
                error_messages.append(_('Failed to create Company: %(error)s') % {'error': str(e)})

        return render(request, 'create-company.html', {
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def list_all_company(request):
    set_default_language(request)
    companys = Company.objects.filter(is_trash=False)
    return render(request, 'all-company.html', {'companys': companys})

@login_required(login_url='/')
def list_all_company_cases(request):
    set_default_language(request)
    company_cases = CompanyCases.objects.filter(is_trash=False)
    return render(request, 'all-company-cases.html', {'company_cases': company_cases})

@login_required(login_url='/')
def list_all_company_attendance(request):
    set_default_language(request)
    company_attendances = CompanyAttendance.objects.filter(is_trash=False)
    return render(request, 'all-company-attendance.html', {'company_attendances': company_attendances})

@login_required(login_url='/')
def list_all_vehicle_failures(request):
    set_default_language(request)
    vehicle_failures = VehicleFailures.objects.filter(is_trash=False)
    return render(request, 'all-vehicle-failure.html', {'vehicle_failures': vehicle_failures})

@login_required(login_url='/')
def single_vehicle_failures(request, pk):
    set_default_language(request)
    vehicle_failure = VehicleFailures.objects.get(id=pk)
    return render(request, 'single-vehicle-failure.html', {'vehicle_failure': vehicle_failure})

@login_required(login_url='/')
def update_vehicle_failures(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_vehiclefailures'):
        # return HttpResponseForbidden(_("You don't have permission to Update Vehicle Failures."))
        return render(request, '403.html')
    
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return HttpResponseForbidden(_("Employee does not exist. Please create an employee profile first."))
    
    worklocations = WorkLocations.objects.filter(is_trash=False)
    
    try:
        dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
    except Duty.DoesNotExist:
        return HttpResponseForbidden(_("No duty assigned to the employee. Please assign a duty first."))
    
    try:
        vehicle_failure = VehicleFailures.objects.get(id=pk)
    except VehicleFailures.DoesNotExist:
        return HttpResponseForbidden(_("Vehicle failure record does not exist."))
    
    try:
        group = Group.objects.get(user=employee.user)
    except Group.DoesNotExist:
        return HttpResponseForbidden(_("Group does not exist. Please create a group first."))
    
    try:
        routine = EmployeeRoutine.objects.get(employee=employee, is_active=True)
    except EmployeeRoutine.DoesNotExist:
        return HttpResponseForbidden(_("Routine does not exist. Please assign a routine to the employee first."))
    
    vehicles = Vehicle.objects.filter(is_trash=False)
    companys = Company.objects.filter(is_trash=False)
    
    return render(request, 'update-vehicle-failure.html', {
        'employee': employee, 
        'dutys': dutys, 
        'vehicles': vehicles,
        'worklocations': worklocations, 
        'group': group, 
        'routine': routine, 
        'companys': companys, 
        'vehicle_failure': vehicle_failure
    })

@login_required(login_url='/')
def single_company_cases(request, pk):
    set_default_language(request)
    company_case = CompanyCases.objects.get(id=pk)
    return render(request, 'single-company-cases.html', {'company_case': company_case})

@login_required(login_url='/')
def single_company_attendance(request, pk):
    set_default_language(request)
    company_attendance = CompanyAttendance.objects.get(id=pk)
    return render(request, 'single-company-attendance.html', {'company_attendance': company_attendance})

@login_required(login_url='/')
def delete_company_cases(request, pk):
    if not request.user.has_perm('mainapp.delete_companycases'):
        # return HttpResponseForbidden(_("You don't have permission to delete Company Cases."))
        return render(request, '403.html')
    else:
        company_cases = CompanyCases.objects.get(id=pk)
        company_cases.delete()
        return redirect (f'/ar/all_company_cases')

@login_required(login_url='/')
def delete_company_attendance(request, pk):
    if not request.user.has_perm('mainapp.delete_companyattendance'):
        # return HttpResponseForbidden(_("You don't have permission to Delete Company Attendance."))
        return render(request, '403.html')
    else:
        company_attendance = CompanyAttendance.objects.get(id=pk)
        company_attendance.delete()
        return redirect (f'/ar/all_company_attendance')

@login_required(login_url='/')
def delete_vehicle_failures(request, pk):
    if not request.user.has_perm('mainapp.delete_vehiclefailures'):
        # return HttpResponseForbidden(_("You don't have permission to delete Vehicle Failures."))
        return render(request, '403.html')
    else:
        vehicle_failure = VehicleFailures.objects.get(id=pk)
        vehicle_failure.delete()
        return redirect (f'/ar/all_vehicle_failures')

@login_required(login_url='/')
def single_company(request, pk):
    set_default_language(request)
    company = Company.objects.get(id=pk)
    return render(request, 'single-company.html', {'company': company})

@login_required(login_url='/')
def update_company(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_company'):
        return HttpResponseForbidden(_("You don't have permission to Update Company."))
    else:
        error_messages = []
        success_messages = []

        try:
            company = Company.objects.get(id=pk)

            if request.method == 'POST':
                update_company_name = request.POST.get('update_company_name')
                company.name = update_company_name
                company.save()
                success_messages.append('Company updated successfully.')
                return redirect(f'{request.LANGUAGE_CODE }/all_company')

        except Company.DoesNotExist:
            error_messages.append('Company does not exist.')
        except Exception as e:
            error_messages.append(f'Failed to update Company: {str(e)}')

        return render(request, 'update-company.html', {
            'company': company,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_company(request, pk):
    if not request.user.has_perm('mainapp.delete_company'):
        return HttpResponseForbidden(_("You don't have permission to delete Company."))
    company = Company.objects.get(id=pk)
    company.is_trash=True
    company.save()
    return redirect ('/all_company')

@login_required(login_url='/')
def create_routine(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_routine'):
        return HttpResponseForbidden(_("You don't have permission to create Routines."))
    else:
        shifts = Shift.objects.filter(is_trash=False)
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                shift_id = request.POST.get('shift_id')
                start_time = request.POST.get('routine_start_time')
                break_time = request.POST.get('routine_break_time')
                end_time = request.POST.get('routine_end_time')
                existing_routine = Routine.objects.filter(shift_id=shift_id).first()

                if existing_routine:
                    raise error_messages.append(_("Routine with this shift already exists."))
                shift = get_object_or_404(Shift, id=shift_id)
                if break_time:
                    routine = Routine.objects.create(shift_id=shift_id, start_time=start_time, break_time=break_time, end_time=end_time)
                else:
                    routine = Routine.objects.create(shift_id=shift_id, start_time=start_time, end_time=end_time)
                success_messages.append(_("Routine created successfully."))

            except Shift.DoesNotExist:
                error_messages.append(_("Shift does not exist."))

            except Exception as e:
                error_messages.append(_("Failed to create routine: {}").format(str(e)))

        return render(request, 'create_routine.html', {
            'shifts': shifts,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def list_all_routines(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_routine'):
        return HttpResponseForbidden(_("You don't have permission to View Routines."))
    else:
        routines = Routine.objects.filter(is_trash=False)
        return render(request, 'all-routines.html', {'routines': routines})

@login_required(login_url='/')
def single_routine(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_routine'):
        return HttpResponseForbidden(_("You don't have permission to View Routines."))
    else:
        routine = Routine.objects.get(id=pk)
        return render(request, 'single-routine.html', {'routine': routine})
 
@login_required(login_url='/')
def update_routine(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_routine'):
        # return HttpResponseForbidden(_("You don't have permission to Change Routines."))
        return render(request, '403.html')
    else:
        routine = Routine.objects.get(id=pk)
        formatted_start_time = routine.start_time.strftime('%I:%M %p')
        formatted_end_time = routine.end_time.strftime('%I:%M %p')
        shifts = Shift.objects.filter(is_trash=False)
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                shift_id = request.POST.get('edited_shift_id')
                start_time = request.POST.get('edited_routine_start_time')
                break_time = request.POST.get('edited_routine_break_time')
                end_time = request.POST.get('edited_routine_end_time')

                shift = get_object_or_404(Shift, id=shift_id)
                routine.shift = shift
                routine.start_time = start_time
                routine.break_time = break_time if break_time else None
                routine.end_time = end_time
                routine.save()
                success_messages.append(_('Routine Updated successfully.'))
                return redirect(f'/update_routine/{routine.id}/')

            except Shift.DoesNotExist:
                error_messages.append(_('Shift does not exist.'))

            except Exception as e:
                error_messages.append(_('Failed to update routine: {str(e)}'))

        return render(request, 'update-routine.html', {
            'routine':routine,
            'formatted_start_time':formatted_start_time,
            'formatted_end_time':formatted_end_time,
            'shifts': shifts,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_routine(request, pk):
    if not request.user.has_perm('mainapp.delete_routine'):
        # return HttpResponseForbidden(_("You don't have permission to Delete Routines."))
        return render(request, '403.html')
    else:
        routine = Routine.objects.get(id=pk)
        routine.delete()
        return redirect(f'/ar/all_routine')

@login_required(login_url='/')
def dashboard(request):
    set_default_language(request)
    notification_user = get_object_or_404(CustomUser, id=request.user.id)
    notifications = notification_user.notifications.all()
    unread_notifications = notification_user.notifications.unread()
    unread_notifications_count = notification_user.notifications.unread().count()
    employees = Employee.objects.filter(is_trash=False)
    employees_count = employees.count()
    clients = Client.objects.filter(is_trash=False)
    clients_count = clients.count()
    requests = Request.objects.filter(is_trash=False).order_by('request_date')
    requests_count = requests.count()
    return render(request, 'dashboard.html', {'employees_count': employees_count, 'clients_count':clients_count, 'employees':employees, 'requests_count':requests_count, 'requests':requests, 'notifications':notifications, 'unread_notifications':unread_notifications,"unread_notifications_count":unread_notifications_count})

@login_required(login_url='/')
def user_management(request):
    set_default_language(request)
    if not request.user.has_perm('auth.add_group'):
        return HttpResponseForbidden(_("You don't have permission to create Roles."))
    else:
        all_content_types = ContentType.objects.all()
        all_permissions = Permission.objects.filter(content_type__in=all_content_types)
        groups = Group.objects.all()
        users = CustomUser.objects.filter(is_active=True)
        return render(request, 'user_management.html', {'groups': groups, 'all_permissions': all_permissions, 'users': users})

@login_required(login_url='/')
def role_assign(request):
    if not request.user.has_perm('auth.add_group'):
        return HttpResponseForbidden(_("You don't have permission to create Roles."))
    else:
        if request.method == 'POST':
            role_name = request.POST["role"]
            group = Group.objects.create(name=role_name)
            return redirect(f'{request.LANGUAGE_CODE }/user_management')

@login_required(login_url='/')
def update_permissions(request):
    if request.method == 'POST':
        role_name = request.POST.get('role_permission')
        chosen_permission_names = request.POST.getlist('chosen_permissions', [])
    
        try:
            group = Group.objects.get(name=role_name)
            chosen_permissions = Permission.objects.filter(id__in=chosen_permission_names)
            group.permissions.clear()
            group.permissions.add(*chosen_permission_names)
            group.save()

            users = CustomUser.objects.filter(groups__name=role_name)
            for user in users:
                if user.groups.filter(name=role_name).exists():
                    user.user_permissions.clear()
                    user.user_permissions.add(*chosen_permissions)
                    user.save()

            return redirect(f'{request.LANGUAGE_CODE}/user_management')
        except Exception as e:
            print(e)
            return HttpResponse(e)

@login_required(login_url='/')
def user_permission(request):
    if request.method == 'POST':
        try:
            user_permission_group_id = int(request.POST['user_permission_group_id'])
            user_permission_user_id = int(request.POST['user_permission_user_id'])
        except ValueError:
            return HttpResponseBadRequest(_("Invalid group or user ID"))

        group = get_object_or_404(Group, id=user_permission_group_id)    
        user = get_object_or_404(CustomUser, id=user_permission_user_id)

        user.groups.clear()
        user.groups.add(group)

        user.user_permissions.clear()
        user.user_permissions.add(*group.permissions.all())

        user.save()

        return redirect(f'{request.LANGUAGE_CODE}/user_management')

@login_required(login_url='/')
def employee_routine(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_employeeroutine'):
        return HttpResponseForbidden(_("You don't have permission to create Employee Routines."))
    else:
        employees = Employee.objects.filter(is_trash=False)
        routines = Routine.objects.filter(is_trash=False)
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                employee_id = request.POST.get('employee_routine_id')
                routine_id = request.POST.get('routine_routine_id')
                employee = get_object_or_404(Employee, id=employee_id)
                routine = get_object_or_404(Routine, id=routine_id)

                existing_employee_routines = EmployeeRoutine.objects.filter(employee=employee, is_active=True)
                existing_employee_routines.update(is_active=False)

                EmployeeRoutine.objects.create(employee=employee, routine=routine, is_active=True)

                success_messages.append(_('Employee routine assigned successfully.'))

            except Employee.DoesNotExist:
                error_messages.append(_('Employee does not exist.'))

            except Routine.DoesNotExist:
                error_messages.append(_('Routine does not exist.'))

            except Exception as e:
                error_messages.append(_('Failed to assign employee routine: {str(e)}'))

        return render(request, 'employee_routine.html', {
            'employees': employees,
            'routines': routines,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def assign_employee_routine(request):
    
    if request.method == 'POST':
        try:
            employee_id = request.POST.get('employee_routine_id')
            routine_id = request.POST.get('routine_routine_id')
            employee = get_object_or_404(Employee, id=employee_id)
            routine = get_object_or_404(Routine, id=routine_id)

            existing_employee_routines = EmployeeRoutine.objects.filter(employee=employee, is_active=True)
            existing_employee_routines.update(is_active=False)

            EmployeeRoutine.objects.create(employee=employee, routine=routine, is_active=True)

            success_message = 'Employee routine assigned successfully.'

            return redirect(f'{request.LANGUAGE_CODE }/employee_routine')

        except Employee.DoesNotExist:
            error_message = 'Employee does not exist.'

        except Routine.DoesNotExist:
            error_message = 'Routine does not exist.'

        except Exception as e:
            error_message = f'Failed to assign employee routine: {str(e)}'

        return render(request, 'employee_routine.html', {'error_message': error_message})

    return redirect(f'{request.LANGUAGE_CODE }/employee_routine')
from notifications.signals import notify


@login_required(login_url='/')
def employee_duty(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_duty'):
        return HttpResponseForbidden(_("You don't have permission to create Employee Duty."))
    else:
        employees = Employee.objects.filter(is_trash=False)
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                employee_id = request.POST.get('employee_duty_id')
                title = request.POST.get('duty_title')
                description = request.POST.get('duty_desc')
                status = request.POST.get('duty_status')

                employee = get_object_or_404(Employee, id=employee_id)
                Duty.objects.create(duty_assigned_employee=employee, title=title, description=description, status=status)
                success_messages.append(_('Duty assigned successfully.'))
                notify_message=(_('New Duty Assigned to You' ))
                notify.send(request.user, recipient=employee.user, verb=f'{notify_message} - {employee.user}', description=description)


            except Employee.DoesNotExist:
                error_messages.append(_('Employee does not exist.'))

            except Exception as e:
                error_messages.append(_('Failed to assign duty: {str(e)}'))

        return render(request, 'employee_duty.html', {
            'employees': employees,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def assign_duty(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee_duty_id')
        title = request.POST.get('duty_title')
        description = request.POST.get('duty_desc')
        status = request.POST.get('duty_status')
        employee = get_object_or_404(Employee, id=employee_id)
        
        Duty.objects.create(duty_assigned_employee=employee, title=title, description=description, status=status)
        return redirect(f'{request.LANGUAGE_CODE }/employee_duty')

@login_required(login_url='/')
def create_client(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_client'):
        return HttpResponseForbidden(_("You don't have permission to create Clients."))
    else:
        worklocations = WorkLocations.objects.filter(is_trash=False)
        jobroles = ClientJobRole.objects.filter(is_trash=False)
        error_messages = []
        success_messages = []

        if request.method == 'POST':
            try:
                client_name = request.POST.get('client_name')
                job_grade = request.POST.get('job_grade')
                job_role_id = request.POST.get('job_role_id')
                head_office = request.POST.get('head_office')
                headquarter_name = request.POST.get('headquarter_name')
                main_headquarter = request.POST.get('main_headquarter')
                client_mobile = request.POST.get('client_mobile')
                client_birthdate = request.POST.get('client_birthdate')
                client_designation_date = request.POST.get('client_designation_date')
                client_uid = request.POST.get('client_uid')
                client_email = request.POST.get('client_email')
                client_status = request.POST.get('client_status')
                client_work_location_id = request.POST.get('client_work_location_id')
                client_id_number = request.POST.get('client_id_number')

                work_location = get_object_or_404(WorkLocations, id=client_work_location_id)
                job_role = get_object_or_404(ClientJobRole, id=job_role_id)

                Client.objects.create(
                    name=client_name,
                    status=client_status,
                    job_grade=job_grade,
                    job_role=job_role,
                    head_office_name=head_office,
                    headquarter_name=headquarter_name,
                    main_headquarter_name=main_headquarter,
                    mobile=client_mobile,
                    birth_date=client_birthdate,
                    UID=client_uid,
                    designation_date=client_designation_date,
                    work_location=work_location,
                    id_number=client_id_number,
                    email=client_email
                )

                success_messages.append(_('Client created successfully.'))
                return redirect(f'/ar/create_client')
            except ValueError as e:
                error_messages.append(_('Invalid value provided: {error}').format(error=str(e)))
            except WorkLocations.DoesNotExist:
                error_messages.append(_('Work location does not exist.'))
            except Exception as e:
                error_messages.append(_('Failed to create client: {error}').format(error=str(e)))

        return render(request, 'create_client.html', {
            'worklocations': worklocations,
            'error_messages': error_messages,
            'success_messages': success_messages,
            'jobroles': jobroles
        })

@login_required(login_url='/')
def create_worklocation(request):
    if request.method == 'POST':
        worklocation_name = request.POST['worklocation_name']
        worklocation_address = request.POST['worklocation_address']
        redirect_to = request.POST.get('redirect_to', 'default')
        WorkLocations.objects.create(name=worklocation_name, address=worklocation_address)
        if redirect_to == 'create_client_worklocation':
            return redirect(f'{request.LANGUAGE_CODE }/create_client')
        elif redirect_to == 'create_employee_worklocation':
            return redirect(f'{request.LANGUAGE_CODE }/create_employee')

@login_required(login_url='/')
def list_all_clients(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_client'):
        return HttpResponseForbidden(_("You don't have permission to view Clients."))
    else:
        clients = Client.objects.filter(is_trash=False)
        return render(request, 'all-clients.html', {'clients': clients})

@login_required(login_url='/')
def single_client(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_client'):
        return HttpResponseForbidden(_("You don't have permission to view Clients."))
    else:
        client = get_object_or_404(Client, id=pk)
        return render(request, 'single-client.html', {'client': client})

@login_required(login_url='/')
def update_client(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_client'):
        # return HttpResponseForbidden(_("You don't have permission to Update Clients."))
        return render(request, '403.html')
    else:
        error_messages = []
        success_messages = []
        client = get_object_or_404(Client, id=pk)
        jobroles = ClientJobRole.objects.filter(is_trash=False)
        formatted_designation_date = client.designation_date.strftime('%Y-%m-%d') if client.designation_date else ''
        formatted_birth_date = client.birth_date.strftime('%Y-%m-%d') if client.designation_date else ''
        worklocations = WorkLocations.objects.filter(is_trash=False)

        if request.method == 'POST':
            try:
                client.name = request.POST.get('edit_client_name')
                client.status = request.POST.get('edit_client_status')
                client.job_grade = request.POST.get('edit_job_grade')
                client.head_office_name = request.POST.get('edit_head_office')
                client.headquarter_name = request.POST.get('edit_headquarter_name')
                client.main_headquarter_name = request.POST.get('edit_main_headquarter')
                client.mobile = request.POST.get('edit_client_mobile')
                client.birth_date = request.POST.get('edit_client_birthdate')
                client.designation_date = request.POST.get('edit_client_designation_date')
                client.UID = request.POST.get('edit_client_uid')
                client.id_number = request.POST.get('edit_client_id_number')
                client.email = request.POST.get('edit_client_email')

                client_work_location_id = request.POST.get('edit_client_work_location_id')
                work_location = get_object_or_404(WorkLocations, id=client_work_location_id)
                client.work_location = work_location

                client_job_role_id = request.POST.get('edit_job_role_id')
                jobrole = get_object_or_404(ClientJobRole, id=client_job_role_id)
                client.job_role = jobrole

                client.save()

                return redirect(f'/ar/all_clients')

            except ValueError as e:
                error_messages.append(str(e))
            except WorkLocations.DoesNotExist:
                error_messages.append(_('Work location does not exist.'))
            except Exception as e:
                error_messages.append(_('Failed to update client: {str(e)}'))

        return render(request, 'update-client.html', {
            'client': client,
            'formatted_designation_date': formatted_designation_date,
            'formatted_birth_date': formatted_birth_date,
            'worklocations': worklocations,
            'jobroles': jobroles,
            'error_messages': error_messages,
            'success_messages': success_messages
        })

@login_required(login_url='/')
def delete_client(request, pk):
    if not request.user.has_perm('mainapp.delete_client'):
        # return HttpResponseForbidden(_("You don't have permission to Delete Clients."))
        return render(request, '403.html')
    
    else:
        client = Client.objects.get(id=pk)
        client.delete()
        return redirect(f'/ar/all_clients')

@login_required(login_url='/')
def create_user(request):
    set_default_language(request)
    worklocations = WorkLocations.objects.filter(is_trash=False)
    if not request.user.has_perm('mainapp.add_customuser'):
        return HttpResponseForbidden(_("You don't have permission to Create Users."))
    else:
        error_messages = []
        success_messages = []

        form_data = {
            'first_name': '',
            'last_name': '',
            'username': '',
            'email': ''
        }

        if request.method == 'POST':
            try:
                form_data['first_name'] = request.POST['first_name']
                form_data['last_name'] = request.POST['last_name']
                form_data['username'] = request.POST['username']
                form_data['email'] = request.POST['email']
                password = request.POST['user_password']
                confirm_password = request.POST['user_confirm_password']
                mobile_number = request.POST['user_mobile_number']

                if password != confirm_password:
                    raise ValidationError(_("Passwords do not match."))

                if CustomUser.objects.filter(email=form_data['email']).exists():
                    raise IntegrityError(_("This email address is already in use."))

                user = CustomUser.objects.create_user(username=form_data['username'], email=form_data['email'], password=password)
                user.first_name = form_data['first_name']
                user.last_name = form_data['last_name']
                user.number = request.POST['user_mobile_number']
                user.work_location_id = request.POST.get('user_worklocations_id')
                is_employee = request.POST.get('isEmployee') == 'on'
                user.is_employee = is_employee
                user.save()

                if is_employee:
                    Employee.objects.create(user=user, work_location_id=user.work_location_id, name=user.get_full_name(), username=user.username, email=user.email, number=user.number, password=user.password)
                success_messages.append(_("User Created Successfully!"))

                form_data = {
                    'first_name': '',
                    'last_name': '',
                    'username': '',
                    'email': ''
                }

            except KeyError as e:
                error_messages.append(f'Missing field in request: {e}')

            except ValidationError as e:
                error_messages.append(e.message)

            except IntegrityError as e:
                error_messages.append(e.args[0])
    
        return render(request, 'create-user.html', {'form_data': form_data, 'error_messages': error_messages, 'success_messages': success_messages, 'worklocations':worklocations})

@login_required(login_url='/')
def update_user(request, pk):
    set_default_language(request)
    worklocations = WorkLocations.objects.filter(is_trash=False)
    if not request.user.has_perm('mainapp.change_customuser'):
        # return HttpResponseForbidden(_("You don't have permission to Update Users."))
        return render(request, '403.html')
    else:
        error_messages = []
        success_messages = []

        user = get_object_or_404(CustomUser, id=pk)

        if request.method == 'POST':
            try:
                fname = request.POST['edit_first_name']
                lname = request.POST['edit_last_name']
                email = request.POST['edit_email']
                username = request.POST['edit_username']
                password = request.POST['edit_user_password']
                confirm_password = request.POST['edit_user_confirm_password']
                mobilenumber = request.POST['edit_user_mobile_number']
                worklocation = WorkLocations.objects.get(id=request.POST['edit_user_worklocations_id'])
                if password != confirm_password:
                    raise ValidationError(_('Passwords do not match.'))

                if CustomUser.objects.filter(email=email).exclude(id=pk).exists():
                    raise IntegrityError(_('This email address is already in use.'))

                user.first_name = fname
                user.last_name = lname
                user.email = email
                user.username = username
                user.number = mobilenumber
                user.work_location = worklocation
                is_employee = request.POST.get('editisEmployee') == 'on'
                user.is_employee = is_employee

                if password:
                    user.set_password(password)

                user.save()
                
                employee, created = Employee.objects.update_or_create(
                user=user,
                defaults={
                    'name': user.get_full_name(),
                    'username': user.username,
                    'email': user.email,
                    'number': user.number,
                    'password': user.password,
                    'work_location': user.work_location
                    }
                )
                success_messages.append(_('User Updated Successfully!'))

            except KeyError as e:
                error_messages.append(f'Missing field in request: {e}')

            except ValidationError as e:
                error_messages.append(e.message)

            except IntegrityError as e:
                error_messages.append(e.args[0])

        return render(request, 'update-user.html', {'user': user, 'error_messages': error_messages, 'success_messages': success_messages, 'worklocations':worklocations})

@login_required(login_url='/')
def delete_user(request, pk):
    if not request.user.has_perm('mainapp.delete_customuser'):
        # return HttpResponseForbidden(_("You don't have permission to Delete Users."))
        activate('ar')
        return render(request, '403.html')
    else:
        user = CustomUser.objects.get(id=pk)
        user.delete()
        return redirect(f'/ar/all_users')

@login_required(login_url='/')
def list_all_users(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_customuser'):
        return HttpResponseForbidden(_("You don't have permission to View Users."))
    else:
        users = CustomUser.objects.filter(is_active=True)
        return render(request, 'all-users.html', {'users': users})

@login_required(login_url='/')
def single_user(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_customuser'):
        return HttpResponseForbidden(_("You don't have permission to View Users."))
    else:
        user = get_object_or_404(CustomUser, id=pk)
        return render(request, 'single-user.html', {'user': user})

@login_required(login_url='/')
def attendence(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_attendencelog'):
        return HttpResponseForbidden(_("You don't have permission to Check Attendance."))
    else:
        today_date = date.today()
        return render(request, 'attendence.html', {'today_date': today_date})


@login_required(login_url='/')
def single_attendence(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_attendencelog'):
        return HttpResponseForbidden(_("You don't have permission to Check Attendance."))
    else:
        return render(request, 'single-attendence.html')

@login_required(login_url='/')
def create_note(request):
    if request.method == 'POST':
        note_name = request.POST['note_name']
        user = CustomUser.objects.get(user = request.user)
        Note.objects.create(created_by = user, content=note_name)
        return redirect(f'{request.LANGUAGE_CODE }/request_form')

@login_required(login_url='/')
def create_request_method(request):
    if request.method == 'POST':
        request_method_name = request.POST['request_method_name']
        RequestMethod.objects.create(name=request_method_name)
        return redirect(f'{request.LANGUAGE_CODE }/request_form')

@login_required(login_url='/')
def create_request_reason(request):
    if request.method == 'POST':
        request_reason_name = request.POST['request_reason_name']
        RequestReason.objects.create(name=request_reason_name)
        return redirect(f'{request.LANGUAGE_CODE }/request_form')

@login_required(login_url='/')
def request_form(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.add_request'):
        return HttpResponseForbidden(_("You don't have permission to Create Request Form."))
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee first."))
        clients = Client.objects.filter(is_trash=False)
        dutys = Duty.objects.filter(duty_assigned_employee__user=request.user, is_trash=False)
        groups = Group.objects.all()
        request_methods = RequestMethod.objects.filter(is_trash=False)
        notes = Note.objects.filter(is_trash=False)
        reasons = RequestReason.objects.filter(is_trash=False)
        return render(request, 'request-form.html', {'employee': employee, 'dutys': dutys, 'request_methods':request_methods, 'notes':notes, 'reasons':reasons, 'clients':clients, 'groups':groups})

@login_required(login_url='/')
def client_request_forms(request):
    clients = Client.objects.filter(is_trash=False)
    dutys = Duty.objects.filter(is_trash=False)
    request_methods = RequestMethod.objects.filter(is_trash=False)
    notes = Note.objects.filter(is_trash=False)
    reasons = RequestReason.objects.filter(is_trash=False)
    return render(request, 'client-request-form.html', {'clients': clients, 'dutys': dutys, 'request_methods':request_methods, 'notes':notes, 'reasons':reasons})

@login_required(login_url='/')
def update_request_form(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_request'):
        # return HttpResponseForbidden(_("You don't have permission to Update Request Form."))
        return render(request, '403.html')
    else:
        try:
            employee = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            return HttpResponseForbidden(_("Employee does not exist. Please create an employee first."))
        clients = Client.objects.filter(is_trash=False)
        dutys = Duty.objects.filter(is_trash=False)
        request_methods = RequestMethod.objects.filter(is_trash=False)
        notes = Note.objects.filter(is_trash=False)
        reasons = RequestReason.objects.filter(is_trash=False)
        custom_request = get_object_or_404(Request, id=pk)
        formatted_request_date = custom_request.request_date.strftime('%Y-%m-%d')
        formatted_request_time = custom_request.request_time.strftime('%I:%M %p')
        groups = Group.objects.all()
        return render(request, 'update-request-form.html', {'employee': employee, 'dutys': dutys, 'request_methods':request_methods, 'notes':notes, 'reasons':reasons, 'custom_request':custom_request, 'formatted_request_date':formatted_request_date, 'formatted_request_time':formatted_request_time, 'clients':clients, 'groups':groups})

@login_required(login_url='/')
def cases_log(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_request'):
        # return HttpResponseForbidden(_("You don't have permission to Update Request Form."))
        return render(request, '403.html')
    else:
        custom_requests = Request.objects.filter(is_trash=False)
        return render(request, 'cases_log.html', {'custom_requests':custom_requests})

@login_required(login_url='/')
def trafic_log(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_request'):
        # return HttpResponseForbidden(_("You don't have permission to Update Request Form."))
        return render(request, '403.html')
    else:
        custom_requests = Request.objects.filter(is_trash=False)
        return render(request, 'trafic_log.html', {'custom_requests':custom_requests})

@login_required(login_url='/')
def person_id(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_request'):
        # return HttpResponseForbidden(_("You don't have permission to Update Request Form."))
        return render(request, '403.html')
    else:
        custom_requests = Request.objects.filter(is_trash=False)
        return render(request, 'person_id.html', {'custom_requests':custom_requests})

@login_required(login_url='/')
def list_employee_request_form(request):
    if not request.user.has_perm('mainapp.view_request'):
        return HttpResponseForbidden(_("You don't have permission to View Request Form."))
    else:
        return render(request, 'list-request-form.html')

@login_required(login_url='/')
def list_all_attachments(request):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_attachment'):
        return HttpResponseForbidden(_("You don't have permission to View Attachment Form."))
    else:
        return render(request, 'list-attachments.html')

@login_required(login_url='/')
def list_client_request_form(request):
    set_default_language(request)
    return render(request, 'client-list-request-form.html')

@login_required(login_url='/')
def single_request(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.view_request'):
        return HttpResponseForbidden(_("You don't have permission to View Request Form."))
    else:
        print(request.user)
        custom_request = get_object_or_404(Request, id=pk)
        return render(request, 'single-request.html', {'custom_request': custom_request})

@login_required(login_url='/')
def update_request(request, pk):
    set_default_language(request)
    if not request.user.has_perm('mainapp.change_request'):
        return HttpResponseForbidden("You don't have permission to Update Request Form.")
    else:
        users = CustomUser.objects.filter(is_active = True)
        worklocations = WorkLocations.objects.filter(is_trash=False)

        custom_request = Request.objects.get(id=pk)

        if request.method == 'POST':
            update_user_id = request.POST.get('update_user_id')
            employee_department_id = request.POST.get('update_employee_department_id')
            employee_worklocations_id = request.POST.get('update_employee_worklocations_id')

            update_user = get_object_or_404(CustomUser, id=update_user_id)
            update_worklocation = get_object_or_404(WorkLocations, id=employee_worklocations_id)

            employee.user = update_user
            employee.work_location = update_worklocation
            employee.name = update_user.first_name
            employee.username = update_user.username
            employee.password = update_user.password
            employee.email = update_user.email
            employee.save()

            return redirect(f'/update_employee/{employee.id}/')

        return render(request, 'update-employee.html', {
            'worklocations': worklocations,
            'users': users,
            'custom_request': custom_request
        })

@login_required(login_url='/')
def delete_request(request, pk):
    if not request.user.has_perm('mainapp.delete_request'):
        # return HttpResponseForbidden(_("You don't have permission to Delete Request Form."))
        
        return render(request, '403.html')
    else:
        request_item = Request.objects.get(id=pk)
        request_item.delete()
        return redirect('/ar/list_employee_request_form')

def create_information_form(request):
    if request.method == 'POST':
        request_id = request.POST.get('created_request_id_name')
        print(request_id)
        custom_request = get_object_or_404(Request, id=request_id)
        uploaded_file = request.FILES.get('information_form_file')
        Attachment.objects.create(file=uploaded_file, uploaded_by=request.user, request = custom_request)
        return redirect(f'{request.LANGUAGE_CODE }/request_form')


# @login_required(login_url='/')
# def information_form(request):
#     return render(request, 'information-form.html')

# @login_required(login_url='/')
# def attachment_form(request):
#     return render(request, 'attachment-form.html')

@login_required(login_url='/')
def attendance_report(request):
    set_default_language(request)
    import datetime
    current_date = datetime.date.today()
    current_month = current_date.month
    current_year = current_date.year
    
    monthly_attendance = AttendenceLog.objects.filter(today_date__year=current_year, today_date__month=current_month)
    
    check_in_count = monthly_attendance.aggregate(total_check_ins=Count('first_in'))
    check_out_count = monthly_attendance.aggregate(total_check_outs=Count('last_out'))
    
    context = {
        'check_in_count': check_in_count['total_check_ins'],
        'check_out_count': check_out_count['total_check_outs']
        
    }
    
    return render(request, 'attendence-report.html', context)

@login_required(login_url='/')
def request_report(request):
    set_default_language(request)
    requests_form = Request.objects.all()
    requests_count = requests_form.count()
    employee_requests = Request.objects.filter(is_trash=False, employee__isnull=False).count()
    client_requests = Request.objects.filter(is_trash=False, client_auto_id__isnull=False).count()
    employees = Employee.objects.filter(is_trash=False)
    employees_count = employees.count()
    return render(request, 'request-report.html', {'requests_count':requests_count, 'employee_requests':employee_requests, 'client_requests':client_requests, 'employees': employees, 'employees_count':employees_count})

@login_required(login_url='/')
def client_report(request):
    set_default_language(request)
    clients = Client.objects.filter(is_trash=False)
    clients_count = clients.count()
    requests = Request.objects.filter(is_trash=False)
    clients_requests = Request.objects.filter(is_trash=False).count()
    return render(request, 'client-report.html', {'clients':clients, 'clients_count':clients_count, 'clients_requests':clients_requests, 'requests':requests})

@login_required(login_url='/')
def employee_report(request):
    set_default_language(request)
    return render(request, 'employee-report.html')



# Rest Framework API   
@api_view(['GET', 'POST'])
def request_method_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = RequestMethodSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)
    
@api_view(['GET', 'POST'])
def request_reason_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = RequestReasonSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET'])
def today_attendence_api(request):
    if request.method == 'GET':
        attendances = AttendenceLog.objects.filter(today_date = date.today(),is_trash=False).select_related('employee_routine')
        for attendance in attendances:
            attendance.first_in = attendance.first_in.strftime('%I:%M %p') if attendance.first_in else ''
            attendance.last_out = attendance.last_out.strftime('%I:%M %p') if attendance.last_out else ''
            attendance.status = "Absent" if attendance.status == "a" else "Present"
        serializer = AttendenceLogSerializer(attendances, many=True)
        response = {'data': serializer.data}
        return Response(response)

from django.db.models import Count
from .models import EmployeeRoutine, AttendenceLog
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.db.models import F

from django.utils import timezone

@api_view(['GET'])
def month_attendance(request):
    if request.method == 'GET':
        today = timezone.now().date()
        month = today.month
        year = today.year
        
        employees = Employee.objects.all()
        
        employee_attendance = {}
        
        for employee in employees:
            attendances = AttendenceLog.objects.filter(
                employee_routine__employee=employee,
                today_date__year=year,
                today_date__month=month,
                is_trash=False
            )
            attendance_statuses = [attendance.status for attendance in attendances]
            employee_attendance[employee.name] = attendance_statuses
        
        dates = AttendenceLog.objects.filter(
            today_date__year=year,
            today_date__month=month,
            is_trash=False
        ).values_list('today_date', flat=True).distinct()
        
        return render(request, 'sample-attendance-report.html', {'employee_attendance': employee_attendance, 'dates': dates})

from django.utils.timezone import now

@api_view(['GET'])
def month_attendence_api(request):
    if request.method == 'GET':
        today = now().date()
        month = today.month
        year = today.year
        
        attendances = AttendenceLog.objects.filter(
            today_date__year=year,
            today_date__month=month,
            is_trash=False
        ).select_related('employee_routine')
        
        dates = set(attendance.today_date for attendance in attendances)
        
        serialized_attendances = []
        for date in dates:
            attendance_for_date = attendances.filter(today_date=date)
            serialized_attendances.append({
                'date': date,
                'attendances': AttendenceLogSerializer(attendance_for_date, many=True).data
            })
        
        response = {'data': serialized_attendances}
        return Response(response)

@api_view(['GET', 'POST'])
def request_note_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = NoteSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def company_cases_api(request):
    if request.method == 'POST':
        actions = request.POST.getlist('actions_id[]')
        serializer = CompanyCasesSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(actions_id=actions)
            response_data = serializer.data
            return Response(response_data, status=201)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'GET':
        cases = CompanyCases.objects.filter(is_trash=False).select_related('city', 'employee', 'group', 'security_guard', 'case_description', 'company', 'duty')
        serializer = ListCompanyCasesSerializer(cases, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def vehicle_type_api(request):
    if request.method == 'POST':
        serializer = VehicleTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return Response(response_data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['PUT'])
def update_company_cases_api(request, pk):
    company_case = get_object_or_404(CompanyCases, pk=pk)
    if request.method == 'PUT':
        data = request.data
        actions = request.POST.getlist('actions_id[]')
        serializer = CompanyCasesSerializer(company_case, data=data)
        if serializer.is_valid():
            serializer.save(actions_id=actions)
            response_data = serializer.data
            return JsonResponse(response_data, status=200)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def client_job_role_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = ClientJobRoleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def company_attendance_api(request):
    if request.method == 'POST':
        actions = request.POST.getlist('actions_id[]')
        serializer = CompanyAttendanceSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(actions_id=actions)
            response_data = serializer.data
            return Response(response_data, status=201)
        
        return Response(serializer.errors, status=400)

    elif request.method == 'GET':
        cases = CompanyAttendance.objects.filter(is_trash=False).select_related('city', 'employee', 'group', 'company', 'duty', 'vehicle')
        serializer = ListCompanyAttendanceSerializer(cases, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def actions_api(request):
    if request.method == 'GET':
        actions = Actions.objects.filter(is_trash=False)
        serializer = ActionsSerializer(actions, many=True)
        response = {'data':serializer.data}
        return Response(response)
    
    elif request.method == 'POST':
        serializer = ActionsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def callname_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = CallnameSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['PUT'])
def update_company_attendance_api(request, pk):
    company_attendance = get_object_or_404(CompanyAttendance, pk=pk)
    if request.method == 'PUT':
        data = request.data
        actions = request.POST.getlist('actions_id[]')
        serializer = CompanyAttendanceSerializer(company_attendance, data=data)
        if serializer.is_valid():
            serializer.save(actions_id=actions)
            response_data = serializer.data
            return JsonResponse(response_data, status=200)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == 'GET':
        cases = CompanyAttendance.objects.filter(is_trash=False).select_related('city', 'employee', 'group', 'company', 'duty', 'vehicle')
        serializer = ListCompanyAttendanceSerializer(cases, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['PUT'])
def update_vehicle_failures_api(request, pk):
    vehicle_failure = get_object_or_404(VehicleFailures, pk=pk)
    if request.method == 'PUT':
        data = request.data
        serializer = VehicleFailuresSerializer(vehicle_failure, data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=200)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def vehicle_failures_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = VehicleFailuresSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)
    elif request.method == 'GET':
        cases = VehicleFailures.objects.filter(is_trash=False).select_related('case_city', 'employee', 'group', 'company', 'duty', 'vehicle')
        serializer = ListVehicleFailuresSerializer(cases, many=True)
        response = {'data':serializer.data}
        return Response(response)

    elif request.method == 'GET':
        cases = CompanyCases.objects.filter(is_trash=False).select_related('city', 'employee', 'group', 'security_guard', 'cases_actions', 'case_description', 'company', 'duty')
        serializer = ListCompanyCasesSerializer(cases, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def cases_descrption_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = CasesDescriptionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def cases_action_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = CasesActionsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def company_guard_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = CompanySecurityGuardSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def user_form_api(request):
    if request.method == 'GET':
        users = CustomUser.objects.filter(is_active = True)
        serializer = ListUserSerializer(users, many=True)
        response = {'data':serializer.data}
        return Response(response)

    elif request.method == 'POST':
        data = request.data
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'PUT'])
def user_form_update(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'PUT':
        data = request.data
        serializer = UserSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=200)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def worklocation_form_api(request):
    if request.method == 'POST':
        data = request.data
        serializer = WorkLocationsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def shift_form_api(request):
    if request.method == 'GET':
        shifts = Shift.objects.filter(is_trash=False)
        serializer = ShiftSerializers(shifts, many=True)
        response = {'data':serializer.data}
        return Response(response)
    
    elif request.method == 'POST':
        data = request.data
        serializer = ShiftSerializers(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def client_form_api(request):
    if request.method == 'GET':
        clients = Client.objects.filter(is_trash=False).select_related('job_role')
        serializer = ClientSerializer(clients, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def employee_form_api(request):
    if request.method == 'GET':
        employees = Employee.objects.filter(is_trash=False).select_related('user', 'work_location')
        serializer = ListEmployeeSerializer(employees, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def vehicle_type_form_api(request):
    if request.method == 'GET':
        vehicle_types = VehicleType.objects.filter(is_trash=False)
        serializer = VehicleTypeSerializer(vehicle_types, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def company_form_api(request):
    if request.method == 'GET':
        companys = Company.objects.filter(is_trash=False)
        serializer = CompanySerializer(companys, many=True)
        response = {'data':serializer.data}
        return Response(response)

    elif request.method == 'POST':
        data = request.data
        serializer = CompanySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def vehicle_form_api(request):
    if request.method == 'GET':
        vehicle_types = Vehicle.objects.filter(is_trash=False).select_related('vehicle_type', 'plate_source')
        serializer = VehicleSerializer(vehicle_types, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET', 'POST'])
def routine_form_api(request):
    if request.method == 'GET':
        routines = Routine.objects.filter(is_trash=False).select_related('shift')
        serializer = RoutineSerializer(routines, many=True)
        response = {'data':serializer.data}
        return Response(response)

@api_view(['GET'])
def single_employee_routine_api(request):
    employee_routine_id = request.GET.get('employee_routine_id')
    if employee_routine_id is None:
        return JsonResponse({"error": "employee_routine_id parameter is required."}, status=400)

    employee_routine_instance = get_object_or_404(Employee, id=employee_routine_id)
    employee_routines = EmployeeRoutine.objects.filter(employee=employee_routine_instance, is_active=True)
    serializer = EmployeeRoutineSerializer(employee_routines, many=True)
    
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET'])
def group_permissions_api(request):
    group_id = request.GET.get('group_id')
    if group_id is None:
        return JsonResponse({"error": "group_id parameter is required."}, status=400)

    try:
        group_instance = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return JsonResponse({"error": "Group with specified ID does not exist."}, status=404)

    permissions = group_instance.permissions.all()
    permission_list = list(permissions.values())

    return JsonResponse(permission_list, safe=False)

@api_view(['GET'])
def employee_request_form_api(request):
    if request.method == 'GET':
        requests = Request.objects.filter(is_trash=False).select_related('employee', 'duty', 'client_auto_id', 'notes','request_method', 'request_reason')
        serializer = ListRequestSerializer(requests, many=True)
        response = {'data': serializer.data}
        return Response(response)

@api_view(['GET'])
def client_request_form_api(request):
    if request.method == 'GET':
        requests = Request.objects.filter(is_trash=False, client_auto_id__isnull=False).select_related('client_auto_id', 'duty', 'department', 'client_auto_id', 'notes','request_method', 'request_reason')
        serializer = ListRequestSerializer(requests, many=True)
        response = {'data': serializer.data}
        return Response(response)

@api_view(['POST'])
def request_form_api(request):
    if request.method == 'POST':
        data = request.data
        group_id = data.get('group')
        user = data.get('user')
        employee_id = data.get('employee')
        serializer = RequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            employee = Employee.objects.get(id=employee_id)
            try:
                group = Group.objects.get(pk=group_id)
            except Group.DoesNotExist:
                return JsonResponse({"error": "Group does not exist"}, status=400)
            
            group_users = group.user_set.all()
            for user in group_users:
                request_notify_msg = (_('New Request Notifications'))
                notify.send(employee.user, recipient=user, verb=f'{request_notify_msg} - {employee.user}', description=f'{request_notify_msg} - {employee.user}')

            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'PUT'])
def request_form_update(request, pk):
    custom_request = get_object_or_404(Request, pk=pk)
    if request.method == 'PUT':
        data = request.data
        serializer = RequestSerializer(custom_request, data=data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=200)
        return JsonResponse(serializer.errors, status=400)

@api_view(['GET', 'POST'])
def information_form_api(request):
    if request.method == 'GET':
        attachments = Attachment.objects.filter(is_trash=False).select_related('uploaded_by', 'request_id')
        serializer = ListAttachmentSerializer(attachments, many=True)
        response = {'data':serializer.data}
        return Response(response)
    
    if request.method == 'POST':
        serializer = AttachmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            return JsonResponse(response_data, status=201)
        return JsonResponse(serializer.errors, status=400)

@api_view(['DELETE'])
def information_form_api_delete(request, pk):
    attachment = get_object_or_404(Attachment, pk=pk)
    if request.method == 'DELETE':
        attachment.delete()
        response = {'message':'Deleted Successfully'}
        return Response(response)



# # Rest API code
# @api_view(['GET', 'POST'])
# def user_list(request):
#     if request.method == 'GET':
#         username = request.GET.get('username')
#         email = request.GET.get('email')
#         first_name = request.GET.get('first_name')
#         last_name = request.GET.get('last_name')
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         users = CustomUserbjects.filter(is_active = True)
#         if username is not None:
#             users = users.filter(username__icontains=username)
#         if email is not None:
#             users = users.filter(email__icontains=email)
#         if first_name is not None:
#             users = users.filter(first_name__icontains=first_name)
#         if last_name is not None:
#             users = users.filter(last_name__icontains=last_name)

#         total = users.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(users, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = UserSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         data['password'] = make_password(data['password'])
#         serializer = UserSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)
 

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def user_detail(request, pk):
#     user = get_object_or_404(User, pk=pk)

#     if request.method == 'GET':
#         serializer = UserSerializer(user)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             if 'password' in data:
#                 data['password'] = make_password(data['password'])
#             serializer = UserSerializer(user, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         user.is_trash = True
#         user.save()
#         return JsonResponse({'message': 'User has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "User not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def department_list(request):
#     if request.method == 'GET':
#         name = request.GET.get('name')
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         department = Department.objects.all()
        
#         if name is not None:
#             department = department.filter(name__icontains=name)

#         total = department.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(department, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = DepartmentSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = DepartmentSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def department_detail(request, pk):
#     department = get_object_or_404(Department, pk=pk)

#     if request.method == 'GET':
#         serializer = DepartmentSerializer(department)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = DepartmentSerializer(department, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         department.is_trash = True
#         department.save()
#         return JsonResponse({'message': 'Department has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Department not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def employee_list(request):
#     if request.method == 'GET':
#         username = request.GET.get('username')
#         name = request.GET.get('name')
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         employee = Employee.objects.all()
        
#         if username is not None:
#             employee = employee.filter(username__icontains=username)
#         if name is not None:
#             employee = employee.filter(name__icontains=name)

#         total = employee.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(employee, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = EmployeeSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         data['password'] = make_password(data['password'])
#         serializer = EmployeeSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def employee_detail(request, pk):
#     employee = get_object_or_404(Employee, pk=pk)

#     if request.method == 'GET':
#         serializer = EmployeeSerializer(employee)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             if 'password' in data:
#                 data['password'] = make_password(data['password'])
#             serializer = EmployeeSerializer(employee, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         employee.is_trash = True
#         employee.save()
#         return JsonResponse({'message': 'Employee has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Employee not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def duty_list(request):
#     if request.method == 'GET':
#         title = request.GET.get('title')
#         status = request.GET.get('status')
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         duty = Duty.objects.all()
        
#         if title is not None:
#             duty = duty.filter(title__icontains=title)
#         if status is not None:
#             duty = duty.filter(status__icontains=status)

#         total = duty.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(duty, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = DutySerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = DutySerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def duty_detail(request, pk):
#     duty = get_object_or_404(Duty, pk=pk)

#     if request.method == 'GET':
#         serializer = DutySerializer(duty)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = DutySerializer(duty, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         duty.is_trash = True
#         duty.save()
#         return JsonResponse({'message': 'Duty has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Duty not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def client_list(request):
#     if request.method == 'GET':
#         name = request.GET.get('name')
#         email = request.GET.get('email')
#         status = request.GET.get('status')
#         job_grade = request.GET.get('job_grade')
        
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         client = Client.objects.all()
        
#         if name is not None:
#             client = client.filter(name__icontains=name)
#         if status is not None:
#             client = client.filter(status__icontains=status)
#         if email is not None:
#             client = client.filter(email__icontains=email)
#         if job_grade is not None:
#             client = client.filter(job_grade__icontains=job_grade)

#         total = client.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(client, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = ClientSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = ClientSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def client_detail(request, pk):
#     client = get_object_or_404(Client, pk=pk)

#     if request.method == 'GET':
#         serializer = ClientSerializer(client)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = ClientSerializer(client, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         client.is_trash = True
#         client.save()
#         return JsonResponse({'message': 'Client has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Client not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def note_list(request):
#     if request.method == 'GET':
        
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         note = Note.objects.all()

#         total = note.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(note, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = NoteSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = NoteSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def note_detail(request, pk):
#     note = get_object_or_404(Note, pk=pk)

#     if request.method == 'GET':
#         serializer = NoteSerializer(note)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = NoteSerializer(note, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         note.is_trash = True
#         note.save()
#         return JsonResponse({'message': 'Note has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Note not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def request_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         requests = Request.objects.all()

#         total = requests.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(requests, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = RequestSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = RequestSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def request_detail(request, pk):
#     requests = get_object_or_404(Request, pk=pk)

#     if request.method == 'GET':
#         serializer = RequestSerializer(requests)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = RequestSerializer(requests, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         requests.is_trash = True
#         requests.save()
#         return JsonResponse({'message': 'Request has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Request not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def requestnote_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         requestnote = RequestNote.objects.all()

#         total = requestnote.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(requestnote, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = RequestNoteSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = RequestNoteSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def requestnote_detail(request, pk):
#     requestnote = get_object_or_404(RequestNote, pk=pk)

#     if request.method == 'GET':
#         serializer = RequestNoteSerializer(requestnote)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = RequestNoteSerializer(requestnote, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         requestnote.is_trash = True
#         requestnote.save()
#         return JsonResponse({'message': 'RequestNote has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "RequestNote not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def worklocation_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         name = request.GET.get('name')
#         worklocation = WorkLocations.objects.all()
        
#         if name is not None:
#             worklocation = worklocation.filter(name__icontains=name)
#         total = worklocation.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(worklocation, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = WorkLocationsSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = WorkLocationsSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def worklocation_detail(request, pk):
#     worklocation = get_object_or_404(WorkLocations, pk=pk)

#     if request.method == 'GET':
#         serializer = WorkLocationsSerializer(worklocation)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = WorkLocationsSerializer(worklocation, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         worklocation.is_trash = True
#         worklocation.save()
#         return JsonResponse({'message': 'WorkLocation has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "WorkLocation not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def attachment_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         file_name = request.GET.get('file_name')
#         attachment = Attachment.objects.all()
        
#         if file_name is not None:
#             attachment = attachment.filter(file_name__icontains=file_name)
#         total = attachment.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(attachment, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = AttachmentSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = AttachmentSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def attachment_detail(request, pk):
#     attachment = get_object_or_404(Attachment, pk=pk)

#     if request.method == 'GET':
#         serializer = AttachmentSerializer(attachment)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = AttachmentSerializer(attachment, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         attachment.is_trash = True
#         attachment.save()
#         return JsonResponse({'message': 'Attachment has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Attachment not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def requestattachment_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         requestattachment = RequestAttachment.objects.all()
        
#         total = requestattachment.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(requestattachment, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = RequestAttachmentSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = RequestAttachmentSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def requestattachment_detail(request, pk):
#     requestattachment = get_object_or_404(RequestAttachment, pk=pk)

#     if request.method == 'GET':
#         serializer = RequestAttachmentSerializer(requestattachment)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = RequestAttachmentSerializer(requestattachment, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         requestattachment.is_trash = True
#         requestattachment.save()
#         return JsonResponse({'message': 'Request Attachment has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Request Attachment not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def attendencelog_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         attendencelog = AttendenceLog.objects.all()
        
#         total = attendencelog.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(attendencelog, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = AttendenceLogSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = AttendenceLogSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def attendencelog_detail(request, pk):
#     attendencelog = get_object_or_404(AttendenceLog, pk=pk)

#     if request.method == 'GET':
#         serializer = AttendenceLogSerializer(attendencelog)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = AttendenceLogSerializer(attendencelog, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         attendencelog.is_trash = True
#         attendencelog.save()
#         return JsonResponse({'message': 'Attendence Log has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Attendence Log not Found"}, status=400)

# @api_view(['GET', 'POST'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def notification_list(request):
#     if request.method == 'GET':
#         page = request.GET.get('page', 1)
#         count = request.GET.get('count', 10)
#         notification = Notification.objects.all()
        
#         total = notification.count()

#         pages = ceil(total / int(count))
#         paginator = Paginator(notification, int(count))
#         try:
#             paginated_data = paginator.page(page)
#         except PageNotAnInteger:
#             paginated_data = paginator.page(1)
#         except EmptyPage:
#             paginated_data = paginator.page(paginator.num_pages)

#         serialized_data = NotificationSerializer(paginated_data, many=True).data
#         res = {"results": serialized_data, "total": total, "page": page, "pages": pages, 'count': count}
#         return Response(res)

#     elif request.method == 'POST':
#         data = JSONParser().parse(request)
#         serializer = NotificationSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             response_data = serializer.data
#             return JsonResponse(response_data, status=201)
#         return JsonResponse(serializer.errors, status=400)

# @api_view(['GET', 'PUT', 'DELETE'])
# @authentication_classes([JWTAuthentication])
# @permission_classes([IsAuthenticated])
# def notification_detail(request, pk):
#     notification = get_object_or_404(Notification, pk=pk)

#     if request.method == 'GET':
#         serializer = NotificationSerializer(notification)
#         return JsonResponse(serializer.data)

#     elif request.method == 'PUT':
#             data = JSONParser().parse(request)
#             serializer = NotificationSerializer(notification, data=data)
#             if serializer.is_valid():
#                 serializer.save()
#                 response_data = serializer.data
#                 return JsonResponse(response_data)
#             return JsonResponse(serializer.errors, status=400)

#     elif request.method == 'DELETE':
#         notification.is_trash = True
#         notification.save()
#         return JsonResponse({'message': 'Notification Log has been deleted successfully'}, status=200)
#     return JsonResponse({"Error": "Notification Log not Found"}, status=400)

def my_view(request):
    return render(request, 'my_template.html')

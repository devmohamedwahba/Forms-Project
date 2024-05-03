
def navigation_permissions(request):
    permission_strings = ['Mainapp.view_client', 'Mainapp.add_client', 'Mainapp.change_client']
    return {'permission_strings': permission_strings}
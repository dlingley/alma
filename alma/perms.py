from permissions import PermissionsRegistry

# just create a permissions object we can tack permissions onto in app/perms.py
permissions = PermissionsRegistry()

# you can put "project level" permissions in here. For app specific
# permissions, put them in app_dir/perms.py

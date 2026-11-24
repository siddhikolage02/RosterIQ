
def has_role(employee, allowed_roles):
    """Check whether an employee has one of the permitted roles."""

    if employee is None:
        return False

    return employee.role in allowed_roles


def is_manager(employee):
    return has_role(employee, ["Manager"])


def is_pod_lead(employee):
    return has_role(employee, ["Pod Lead"])


def can_manage_roster(employee):
    return has_role(employee, ["Manager", "Pod Lead"])


def can_manage_employees(employee):
    return is_manager(employee)


def can_approve_roster(employee):
    return is_manager(employee)


def can_publish_roster(employee):
    return is_manager(employee)

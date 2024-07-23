# my_employee_module/__manifest__.py
{
    'name': 'Employee Module',
    'version': '1.0',
    'summary': 'Custom Employee Module',
    'license': 'LGPL-3',
    'depends': ['hr', 'mail'],
    'data': [
        'views/employee_view.xml',
        'views/email_template.xml',
    ],
    'installable': True,
    'application': False,
    'images': ['static/description/icon.png'],
}

# my_employee_module/models/hr_employee.py

from odoo import models, fields, api


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def action_send_email(self):
        # Get the base URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Get the action ID for the employee form view (replace with your specific action ID)
        action_id = self.env.ref('hr.open_view_employee_list').id

        for record in self:
            # Construct the URL for the employee form
            form_url = f"{base_url}/web#id={record.id}&model=hr.employee&view_type=form&action={action_id}"

            mail_values = {
                'subject': 'Employee Information',
                'body_html': '''
                    <p>Dear {name},</p>
                    <p>Here is your information:</p>
                    <p><strong>Work Mobile:</strong> {work_mobile}</p>
                    <p><strong>Work Phone:</strong> {work_phone}</p>
                    <p><strong>Work Email:</strong> {work_email}</p>
                    <p><strong>Department:</strong> {department}</p>
                    <p><strong>Job Position:</strong> {job_position}</p>
                    <p><strong>Manager:</strong> {manager}</p>
                    <p><strong>Coach:</strong> {coach}</p>
                    <p><a href="{form_url}">Update Information</a></p>
                '''.format(
                    name=record.name or '',
                    work_mobile=record.mobile_phone or '',
                    work_phone=record.work_phone or '',
                    work_email=record.work_email or '',
                    department=record.department_id.name or '',
                    job_position=record.job_id.name or '',
                    manager=record.parent_id.name or '',
                    coach=record.coach_id.name or '',
                    form_url=form_url
                ),
                'email_to': record.work_email,
            }

            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

# from odoo import models, fields, api
#
# class HREmployee(models.Model):
#     _inherit = 'hr.employee'
#
#     def action_send_email(self):
#         for record in self:
#             mail_values = {
#                 'subject': 'Employee Information',
#                 'body_html': '''
#                     <p>Dear {name},</p>
#                     <p>Here is your information:</p>
#                     <p><strong>Work Mobile:</strong> {work_mobile}</p>
#                     <p><strong>Work Phone:</strong> {work_phone}</p>
#                     <p><strong>Work Email:</strong> {work_email}</p>
#                     <p><strong>Department:</strong> {department}</p>
#                     <p><strong>Job Position:</strong> {job_position}</p>
#                     <p><strong>Manager:</strong> {manager}</p>
#                     <p><strong>Coach:</strong> {coach}</p>
#                 '''.format(
#                     name=record.name or '',
#                     work_mobile=record.mobile_phone or '',
#                     work_phone=record.work_phone or '',
#                     work_email=record.work_email or '',
#                     department=record.department_id.name or '',
#                     job_position=record.job_id.name or '',
#                     manager=record.parent_id.name or '',
#                     coach=record.coach_id.name or '',
#                 ),
#                 'email_to': record.work_email,
#             }
#
#             mail = self.env['mail.mail'].create(mail_values)
#             mail.send()

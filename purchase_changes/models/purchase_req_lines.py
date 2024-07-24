from dateutil.relativedelta import relativedelta

from odoo import fields, api, models, _, tools
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from datetime import timedelta


# Code to create lines
class PurchaseReqProductLinesRFQ(models.Model):
    _name = 'pur.req.lines'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char('Name', required=True)
    product_uom_qty = fields.Float('Quantity', default=1)
    price_unit = fields.Float('Unit Price', )
    pur_id = fields.Many2one('purchase.newchanges')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    requisition_action = fields.Many2one('stock.picking.type', string='Requisition Action')

    vendor_name = fields.Many2one('res.partner', string='Vendor Name',
                                  domain=[('is_company', '=', True),
                                          ('invoice_ids.name', '!=',
                                           False)])
    quantity = fields.Float(string='Quantity')

    # Code to the default values of the product in the PO
    @api.onchange('product_id')
    def prod_onchange_get_order_id(self):
        for rec in self:
            self.price_unit = rec.product_id.standard_price
            self.uom_id = rec.product_id.uom_id.id
            self.name = rec.product_id.name


# Code to get source and destination location
class LocationQuality(models.Model):
    _inherit = 'quality.point'

    src_location = fields.Many2one('stock.location', string='Source Location')
    destination_location = fields.Many2one('stock.location', string='Destination Location')


# code to inherit quality check wizard
class QualityCheckWizardNew(models.TransientModel):
    _inherit = 'quality.check.wizard'

    stock_picking = fields.Many2one('stock.picking')


# code to move the products individaully to restricted or unrestricted or control sample loction based on parameters
class CheckQualityInherit(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(CheckQualityInherit, self).button_validate()

        unrestricted_location_id = self.env['stock.location'].search([('is_location_type', '=', 'is_unrestricted')],
                                                                     limit=1).id
        blocked_location_id = self.env['stock.location'].search([('is_location_type', '=', 'is_blocked')], limit=1).id
        quality_control_location_id = self.env['stock.location'].search(
            [('is_location_type', '=', 'is_quality_control')], limit=1).id

        for picking in self:
            # Retrieve quality checks related to the picking
            quality_checks = self.env['quality.check'].search([('picking_id', '=', picking.id)])

            passed_product_ids = quality_checks.filtered(lambda qc: qc.quality_state == 'pass').mapped('product_id').ids
            failed_product_ids = quality_checks.filtered(lambda qc: qc.quality_state == 'fail').mapped('product_id').ids
            move_lines = self.env['stock.move.line'].search([('picking_id', '=', picking.id)])

            for move in move_lines:
                qc_loc = move.filtered(lambda m: m.picking_id == picking).location_dest_id

                if move.product_id.id in passed_product_ids:
                    if move.location_dest_id == qc_loc:
                        move.location_dest_id = unrestricted_location_id
                        print("passed to unrestricted")

                elif move.product_id.id in failed_product_ids:
                    if move.location_dest_id == qc_loc:
                        move.location_dest_id = blocked_location_id
                        print("failed to blocked")

        return res

    # Code to update the context
    def check_quality(self):
        x = super(CheckQualityInherit, self).check_quality()

        x['context'].update({
            'stock_picking': self.id
        })
        return x

    # code to open the wizard with respect to the particular product
    def check_quality_for_product(self, product=None):
        self.ensure_one()
        print('self', self)

        if product:
            checkable_products = self.mapped('move_line_ids').filtered(
                lambda line: line.product_id == product).mapped('product_id')
        else:
            checkable_products = self.mapped('move_line_ids').mapped('product_id')

        print('checkable_products', checkable_products)
        checks = self.check_ids.filtered(lambda check: check.quality_state == 'none' and (
                check.product_id in checkable_products or check.measure_on == 'operation'))
        print('checks', checks)

        if checks:
            print('tttttttttttttttttttt', checks.action_open_quality_check_wizard())
            return checks.action_open_quality_check_wizard()
        if not checks:
            raise ValidationError(
                _("No quality checks found for the selected product(s): %s") % product.display_name)

        return False

    # code to move the products to the Reanalysis location on expiry (cron Job)
    @api.model
    def move_expired_products(self):
        loc_unrestricted = self.env['stock.location'].search([('is_location_type', '=', 'is_unrestricted')],
                                                             limit=1)

        loc_reanalysis = self.env['stock.location'].search([('is_location_type', '=', 'is_retest')], limit=1)

        # Filter stock records based on the expiry date of the product
        expired_stock = self.env['stock.quant'].search([
            ('location_id', '=', loc_unrestricted.id),
            ('product_id.expiry_date_calculated', '=', fields.Date.today())
        ])

        # Create a picking for the movement
        picking_values = {
            'location_id': loc_unrestricted.id,
            'location_dest_id': loc_reanalysis.id,
            'picking_type_id': 1,  # Adjust the picking type ID according to your system
            'move_type': 'direct',
            'state': 'draft',
            'origin': 'Expired Product Movement',
        }
        picking = self.env['stock.picking'].create(picking_values)

        # Create move lines for each expired product in the picking
        move_line_values = []
        for product in expired_stock:
            move_line_values.append({
                'name': product.product_id.name,
                'product_id': product.product_id.id,
                'product_uom_qty': product.quantity,
                'quantity': product.quantity,
                'location_id': loc_unrestricted.id,
                'location_dest_id': loc_reanalysis.id,
                'picking_id': picking.id,
            })
        s = self.env['stock.move'].create(move_line_values)
        s.write({'state': 'assigned'})
        s.move_line_ids.write({'state': 'done'})

        # Confirm and validate the picking to move products to Reanalysis location
        picking.action_confirm()
        picking.button_validate()

        # Create quality check records for the moved products
        quality_check_values = []
        x = self.env['quality.alert.team'].search([], limit=1)
        y = self.env['quality.point.test_type'].search([], limit=1)
        z = self.env['quality.point'].search([], limit=1)
        for product in expired_stock:
            quality_check_values.append({
                'product_id': product.product_id.id,
                'team_id': x.id,
                'test_type_id': y.id,
                'point_id': z.id,
                'picking_id': picking.id
                # 'quantity': product.quantity,
                # 'location_id': loc_reanalysis.id,
                # Add other fields as needed
            })
        quality_checks = self.env['quality.check'].create(quality_check_values)

        # Print moved product names for verification
        for product in expired_stock:
            print(product.product_id.name)


# Code to Open the wizard from the puchase order lines for individual products
class StockMoveClass(models.Model):
    _inherit = 'stock.move'
    quality_check_todo = fields.Boolean('Pending checks', compute='_compute_check', invisible=True)
    quality_check_fail = fields.Boolean(compute='_compute_check')

    def check_quality(self):
        print('move_line_ids', self.move_line_ids)
        print('Original context:', self.env.context)
        picking_id = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
        print(self.ids)

        print('picking_id', picking_id)
        print('picking_id.state:', picking_id.state)

        if picking_id:

            for move_line in self.move_line_ids:

                new_context = picking_id.check_quality_for_product(move_line.product_id)

                if new_context:
                    new_context['context'].update({
                        'stock_picking': picking_id.id
                    })

                    print('1111', new_context)
                    if 'form_view_ref' in new_context['context']:
                        del new_context['context']['form_view_ref']

                    print('22222', new_context)

                    # Return the modified context
                    return new_context
            return False

    # Code to check the state of the product in quality
    @api.depends('picking_id.check_ids', 'picking_id.check_ids.quality_state')
    def _compute_check(self):
        for move in self:
            todo = False
            fail = False
            picking = move.picking_id
            checkable_products = picking.mapped('move_line_ids').mapped('product_id')
            for check in picking.check_ids:
                if check.quality_state == 'none' and (
                        check.product_id in checkable_products or check.measure_on == 'operation'):
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            move.quality_check_fail = fail
            move.quality_check_todo = todo


# Code to create multiple selection fields
class StockingLocationNew(models.Model):
    _inherit = "stock.location"

    is_restricted = fields.Boolean(string='Is restricted')
    is_unrestricted = fields.Boolean(string='Is Unrestricted')
    is_location_type = fields.Selection(selection=[('is_restricted', 'Is restricted'),
                                                   ('is_unrestricted', 'Is Unrestricted'),
                                                   ('is_retest', 'Is Reanalysis'),
                                                   ('is_blocked', 'Is Blocked'),
                                                   ('is_quality_control', 'Is Quality Control'),
                                                   ('is_control_sample', 'Is Control Sample')])


# Code to add new fields to the product template
class productTemplateInherit(models.Model):
    _inherit = 'product.template'

    inward_date = fields.Date(string='Inward Date', compute='_compute_inward_date', store=True, readonly=True)
    expiry_date = fields.Char(string="Expiry Date")
    expire_in = fields.Selection([('months', 'Months'), ('years', 'years')], string="Expiry period")
    expiry_date_calculated = fields.Date(string="Calculated Expiry Date", store=True, compute='_compute_expiry_date',
                                         readonly=False)
    is_control_sample_taken = fields.Boolean(string='Will Control Sample be Taken?')
    control_sample = fields.Float(string='Control Sample(%)')
    expiry_warning = fields.Boolean(string="Expiry Warning", compute='_compute_expiry_warning', store=True)

    # Code to display the banner in product.template if the expiry date is within one month
    @api.depends('expiry_date_calculated')
    def _compute_expiry_warning(self):
        for product in self:
            if product.expiry_date_calculated:
                today = datetime.now().date()
                one_month_after_today = today + timedelta(days=30)
                if product.expiry_date_calculated >= today and product.expiry_date_calculated <= one_month_after_today:
                    product.expiry_warning = True
                else:
                    product.expiry_warning = False

    # Code to take the control sample
    @api.onchange('is_control_sample_taken')
    def _onchange_is_control_sample_taken(self):
        if not self.is_control_sample_taken:
            self.control_sample = 0.0

    # Code to compute the inward date
    @api.depends('default_code')
    def _compute_inward_date(self):
        for template in self:
            picking = self.env['stock.picking'].search([('origin', '=', template.default_code)], limit=1)
            if picking:
                template.inward_date = picking.date_deadline

    # Code to compute the expiry date
    @api.depends('inward_date', 'expiry_date', 'expire_in')
    def _compute_expiry_date(self):
        for template in self:
            if template.inward_date and template.expiry_date and template.expire_in:
                inward_date = fields.Date.from_string(template.inward_date)
                if '-' in template.expiry_date:
                    expiry_date = fields.Date.from_string(template.expiry_date)
                else:
                    expiry_date = inward_date + relativedelta(
                        months=int(
                            template.expiry_date)) if template.expire_in == 'months' else inward_date + relativedelta(
                        years=int(template.expiry_date))

                template.expiry_date_calculated = expiry_date

    # Code to send the expiry notification of the product before one month of expiry to the user
    @api.model
    def send_expiry_notifications(self):
        print("JJJJJJJJJJJJJJj")
        today = datetime.now().date()
        one_month_before = today + timedelta(days=30)
        admin_email = self.env.user.login

        expiring_products = self.env['product.product'].search([])
        print(expiring_products, "yyugqgdvdvqwdgqwjdh")

        for rec in expiring_products:
            expiry_date1 = rec.expiry_date_calculated if rec.expiry_date_calculated else None
            print(expiry_date1, "hhhhhhhhhhhhhhh")

            if expiry_date1:
                days_until_expiry = (expiry_date1 - today).days
                print(days_until_expiry, "wstgsashdudyudid")

                if days_until_expiry == 30:
                    self.env['mail.mail'].create({
                        'email_from': admin_email,
                        'subject': 'Product Expiry Reminder',
                        'body_html': f"Dear User,\n\nThis is to remind you that the product '{rec.name}' is expiring on {expiry_date1}.\n\nRegards,\nThank You",
                        'email_to': admin_email,
                    })


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Code to move the control sample products to Control Sample location

    def action_view_picking(self):
        loc_control_sample = self.env['stock.location'].search([('is_location_type', '=', 'is_control_sample')],
                                                               limit=1)

        self.ensure_one()
        # Create quants for products with control sample
        quants_to_create = []
        for line in self.order_line:
            if line.product_id.control_sample > 0 and not line.control_sample_sent:
                control_sample_qty = line.product_qty * (line.product_id.control_sample / 100)

                # Adjust quantity based on control_sample percentage
                adjusted_qty = line.product_qty - control_sample_qty

                # Create record in stock.picking for the subtracted quantity
                picking_vals = {
                    'picking_type_id': self.picking_type_id.id,
                    'location_id': self.partner_id.property_stock_supplier.id,
                    'location_dest_id': loc_control_sample.id,
                    'partner_id': self.partner_id.id,
                    'state': 'assigned',
                    'origin': self.name,
                    'move_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': control_sample_qty,
                        'product_uom': line.product_uom.id,
                        'name': line.name,
                        'location_id': line.product_id.property_stock_inventory.id,  # Set to default inventory location
                        'location_dest_id': loc_control_sample.id,
                    })],
                }
                new_picking = self.env['stock.picking'].create(picking_vals)

                # Adjust quantity based on control_sample percentage
                line.product_qty = adjusted_qty

                # Confirm the picking to change state to 'assigned'
                new_picking.action_confirm()

                # Mark control sample as sent for this line
                line.control_sample_sent = True

        # Call the original action_view_picking method
        return self._get_action_view_picking(self.picking_ids)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    control_sample_sent = fields.Boolean(string="Control Sample Sent")


# Code to put validation error and not allow the user to create the Manufacturing order if the expiry date is within one month
class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.constrains('product_id', 'product_id.expiry_date_calculated')
    def _check_expiry_date(self):
        for production in self:
            if production.product_id and production.product_id.expiry_date_calculated:
                today = datetime.now().date()
                one_month_after_today = today + timedelta(days=30)
                if (production.product_id.expiry_date_calculated >= today and
                        production.product_id.expiry_date_calculated <= one_month_after_today):
                    raise ValidationError(
                        'This production order cannot be processed as the product will expire on %s, and is within one month of expiry.'
                        % production.product_id.expiry_date_calculated)


class productTemplateInherit(models.Model):
    _inherit = 'product.template'
    manufacturing_control_sample = fields.Float(string='Manufacturing Control Sample(%)')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


def action_confirm(self):
    res = super(MrpProduction, self).action_confirm()

    loc_control_sample = self.env['stock.location'].search([('is_location_type', '=', 'is_control_sample')],
                                                           limit=1)

    for production in self:
        for line in production.move_raw_ids:
            if line.product_id.manufacturing_control_sample > 0:
                manufacturing_control_sample = line.product_qty * (
                        line.product_id.manufacturing_control_sample / 100)
                print(manufacturing_control_sample)

                adjusted_qty = line.product_qty - manufacturing_control_sample
                print(adjusted_qty)

                picking_vals = {
                    'picking_type_id': self.picking_type_id.id,
                    'location_id': production.location_src_id.id,
                    'location_dest_id': loc_control_sample.id,
                    # 'partner_id': self.partner_id.id,
                    'state': 'assigned',
                    'origin': self.name,
                    'move_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': manufacturing_control_sample,
                        'product_uom': line.product_uom.id,
                        'name': line.name,
                        'location_id': production.location_src_id.id,

                        'location_dest_id': loc_control_sample.id,
                    })],
                }

                new_picking = self.env['stock.picking'].create(picking_vals)

                line.product_uom_qty = line.product_qty

                new_picking.action_confirm()

    return res


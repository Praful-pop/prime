from odoo import api, fields, models, _


class InternalWorkOrder(models.Model):
    _name = 'internal.work.order'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin']

    employee_name = fields.Many2one('res.users', string="Name", default=lambda self: self.env.user)
    date = fields.Date(string='Date')
    description = fields.Text(string='Description')
    order_lines = fields.One2many('internal.work.order.line', 'order_id', string='Order Lines')
    is_verified = fields.Boolean("verify")
    is_req_sent = fields.Boolean("send")
    name = fields.Char('Order Reference', required=True, index='trigram', copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('mo created', 'MO created'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    # @api.depends('prod_line_ids')
    # def _compute_manufacturing_count(self):
    #     for record in self:
    #         product_ids = record.prod_line_ids.mapped('product_id')
    #         manufacturing_orders = self.env['mrp.production'].search([('product_id', 'in', product_ids.ids)])
    #         record.manufacturing_count = len(manufacturing_orders)

    # Code to Change the state of the PR to Confirm
    def button_confirm_new(self):
        for rec in self:
            self.state = 'confirm'

    # Code to Change the state of the PR to reset the state to draft
    def reset_to_draft(self):
        for rec in self:
            rec.is_verified = True
            rec.is_req_sent = False
            self.state = 'draft'

    # Code to Change the state of the PR to Cancelled

    def button_reject(self):
        for rec in self:
            rec.is_verified = True
            rec.is_req_sent = False
            self.state = 'cancel'

    def internal_order1(self):
        self.ensure_one()
        self.state = 'mo created'
        print("kkkkkkkkkkkkkk")
        manufacturing_orders = self.env['mrp.production']
        for order in self:
            for line in order.order_lines:
                if line.product_id.type == 'product' and line.product_id.bom_ids:
                    bom = line.product_id.bom_ids[0]
                    if bom:
                        bom_vals = {
                            'product_id': line.product_id.id,
                            'product_qty': line.product_uom_qty,
                            'bom_id': bom.id,
                        }
                        mo = self.env['mrp.production'].create(bom_vals)
                        manufacturing_orders += mo
        return manufacturing_orders

    def action_my_manufacturing_button(self):
        self.ensure_one()
        manufacturing_orders = self.internal_order1()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', manufacturing_orders.ids)],
        }
        return action

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.work.order')
        return super(InternalWorkOrder, self).create(vals)


class InternalWorkOrderLine(models.Model):
    _name = 'internal.work.order.line'

    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity')
    order_id = fields.Many2one('internal.work.order', string='Order')

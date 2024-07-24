# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


class purchaserequesition(models.Model):
    _name = 'purchase.newchanges'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin']

    is_verified = fields.Boolean("verify")
    is_req_sent = fields.Boolean("send")
    employee_name = fields.Many2one('res.users',string="Employee Name")
    department_name = fields.Many2one('hr.department', string='Department Name')
    managers_id = fields.Many2one('hr.department', string='Department Manager')
    req_date = fields.Date('Request Date')
    src_location = fields.Many2one('stock.quant', string='Source Location')
    destination_location = fields.Many2one('stock.quant', string='Destination Location')
    deliver_to = fields.Many2one('stock.picking.type', string='Deliver To')
    internal_picking = fields.Many2one('stock.picking.type', string='Internal Picking Location')

    name = fields.Char('Order Reference', required=True, index='trigram', copy=False, default='New')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], 'Priority', default='0', index=True)
    purchase_count = fields.Integer(compute="_compute_purchase_count")
    invoice_ids = fields.Many2many('account.move', compute="_compute_invoice", string='Bills', copy=False, store=True)
    prod_line_ids = fields.One2many('pur.req.lines', 'pur_id', string='Products')
    requisition_action = fields.Many2one('stock.picking.type', string='Requisition Action')
    vendor_name = fields.Many2one('res.partner', string='Vendor Name',
                                  domain=[('is_company', '=', True),
                                          ('invoice_ids.name', '!=',
                                           False)])

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('department', 'Department Approval'),
        ('approve', 'Approved'),
        ('po created', 'PO Created'),
        ('cancel', 'Cancelled')

    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

#Code to Count the No. of Purchase Orders
    @api.depends('prod_line_ids')
    def _compute_purchase_count(self):
        for record in self:
            product_ids = record.prod_line_ids.mapped('product_id')
            purchase_orders = self.env['purchase.order'].search([('product_id', 'in', product_ids.ids)])
            record.purchase_count = len(purchase_orders)

#Code to Count the No. of Purchase Orders in smart button to redirect to Purchase Order
    def action_my_smart_button(self):
        if self.purchase_count > 0:
            purchase_order = self.env['purchase.order'].search([('product_id', '=', self.prod_line_ids.product_id.id)],
                                                               limit=1)
            if purchase_order:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Purchase Order',
                    'res_model': 'purchase.order',
                    'view_mode': 'tree,form',
                    'domain': [('product_id', '=', self.prod_line_ids.product_id.id)],
                }
        return {}

    def action_view_invoice(self):
        pass

#Code to Change the state of the PR to Confirm
    def button_confirm_new(self):
        for rec in self:
            self.state = 'confirm'

# Code to Change the state of the PR to departmental Approval
    def req_send_department(self):
        for rec in self:
            self.state = 'department'

# Code to Change the state of the PR to final Approval
    def approve_quotation(self):
        for rec in self:
            self.state = 'approve'

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

#Code to update PR Values in PO
    def purchase_quotation(self):
        self.ensure_one()
        self.state = 'po created'
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]

        line_vals = []
        for rec in self:
            for line in rec.prod_line_ids:
                lines = {
                    'product_id': line.product_id.id,
                    # 'requisition_action': line.requisition_action.id,
                    'name': line.name,
                    'product_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'date_planned': datetime.now(),
                    'product_uom': line.uom_id.id,

                }
                line_vals.append(Command.create(lines))
                print(line_vals)

                action['context'] = {
                    # 'default_requisition_action': self.requisition_action.id,
                    'default_order_line': line_vals,
                    'default_origin': self.name,
                    'default_opportunity_id': self.id,
                    'default_pur_req': self.id,
                    'default_partner_id': self.vendor_name
                }

            return action

#Code to generate the sequence for the PO
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.newchanges')
        return super(purchaserequesition, self).create(vals)

#Code to Update the Inward date in the PO
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    pur_req = fields.Many2one('purchase.newchanges', string='Pur Req')

    @api.model
    def create(self, values):
        order = super(PurchaseOrder, self).create(values)
        order.update_product_inward_date()
        return order

    def action_view_picking(self):
        result = super(PurchaseOrder, self).action_view_picking()
        self.update_product_inward_date()
        return result

    def update_product_inward_date(self):
        for order in self:
            for line in order.order_line:
                if line.product_id:
                    inward_date = order.date_planned
                    print(f"Inward Date: {inward_date}")
                    self.env['product.product'].browse(line.product_id.id).write({
                        'inward_date': inward_date,
                    })


#To Create two new categories of product
class productCategoryInherit(models.Model):
    _inherit = 'product.category'

    type_of_category = fields.Selection(selection=[('active', 'Active'),
                                                   ('excepiant', 'Excepiant')])

#code to get the quantity from the PR to PO
class purchase_changes_line(models.Model):
    _inherit = 'purchase.order.line'

    requisition_action = fields.Many2one('stock.picking.type', string='Requisition Action')


    @api.depends('product_qty', 'product_uom', 'company_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            params = {'order_id': line.order_id}
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            if not seller:
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                po_line_uom = line.product_uom or line.product_id.uom_po_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.taxes_id,
                    line.company_id,
                )
                price_unit = line.product_id.cost_currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    False
                )
                line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                               self.env[
                                                                                   'decimal.precision'].precision_get(
                                                                                   'Product Price')))
                continue

            price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                 line.product_id.supplier_taxes_id,
                                                                                 line.taxes_id,
                                                                                 line.company_id) if seller else 0.0
            price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id,
                                                     line.date_order or fields.Date.context_today(line), False)
            price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                      self.env['decimal.precision'].precision_get(
                                                                          'Product Price')))
            line.discount = seller.discount or 0.0

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))




#Code to set multiple states in stock.picking model
class StockingPickingNew(models.Model):
    _inherit = "stock.picking"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")

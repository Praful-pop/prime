from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class sale_order_line_for_dc(models.Model):
    _inherit = 'sale.order.line'

    class sale_order_line_for_dc(models.Model):
        _inherit = 'sale.order.line'
        branch_names = fields.Many2one(
            'res.company',
            string='Company',
            store=True,
            readonly=False,

        )

        contact_name = fields.Many2one('res.partner', domain=lambda self: "[('is_company','=',True)]",
                                       string="Contact Name")


class SaleInternal(models.Model):
    _inherit = 'sale.order'

    order_type = fields.Selection([
        ('internal', 'Is Internal Work Order'),
        ('normal', 'Is Sale Order')
    ], string='Order Type')

    def action_confirm(self):
        # Ensure we call the original action_confirm method
        res = super(SaleInternal, self).action_confirm()
        # Update the user_id to the current logged-in user
        for order in self:
            order.write({'user_id': self.env.user.id})
        return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    main_pharma_sale_order_id = fields.Many2one('sale.order', string='Source Sale Order', readonly=True, copy=False)
    # main_pharma_company = fields.Many2one('res.company', string='Company', required=True)

    @api.model
    def create(self, values):
        purchase_order = super(PurchaseOrder, self.sudo()).create(values)
        main_company = self.env['res.company'].sudo().search([('name', '=', 'Anglo French Drugs')], limit=1)
        if not main_company:
            raise ValueError("Main company 'Anglo French Drugs' not found")
        branch_companies = ['C&F Agent Hyderabad', 'C&F Agent Chennai']
        if purchase_order.company_id.name in branch_companies:
            partner_company_name = purchase_order.company_id.name
            sale_order_lines = []
            for line in purchase_order.order_line:
                sale_order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom.id,
                }))
            partner = self.env['res.partner'].sudo().search([('name', '=', partner_company_name)], limit=1)
            if not partner:
                raise ValueError(f"Partner '{partner_company_name}' not found")
            sale_order = self.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'company_id': main_company.id,
                'order_line': sale_order_lines,
                'user_id': False,
            })
            purchase_order.main_pharma_sale_order_id = sale_order.id
        return purchase_order


class CrmInherit(models.Model):
    _inherit = 'crm.lead'

    order_line_ids = fields.One2many('crm.lead.order.line', 'lead_id', string='Order Lines')


class CRMLeadOrderLine(models.Model):
    _name = 'crm.lead.order.line'
    _description = 'CRM Lead Order Line'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    demand = fields.Integer(string='Demand', required=True)



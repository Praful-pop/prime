from odoo import fields, api, models
from odoo.exceptions import UserError, ValidationError


class CustomQualityCheckLocation(models.Model):
    _inherit = 'quality.check'

    move_lines_ids = fields.Many2one('stock.picking')

    # After the Cron job is executed then this code it used to move the products from Reanalysis to Unrestricted location
    def do_pass(self):
        for rec in self:
            picking_id = rec.picking_id
            if picking_id:
                print(picking_id)
                if picking_id.state != 'done':
                    picking_id.button_validate()
                stock_move = self.env['stock.move'].search([
                    ('picking_id', '=', picking_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('state', '=', 'done')
                ], limit=1)
                print(stock_move)
                # print(stock_move_1)
                if stock_move:
                    print(stock_move)
                    unrestricted_location = self.env['stock.location'].search([('name', '=', 'Unrestricted Location')],
                                                                              limit=1)
                    print('unrestricted_location', unrestricted_location.name)
                    if unrestricted_location:
                        loc_reanalysis = self.env['stock.location'].search([('name', '=', 'Reanalysis')], limit=1)

                        # Filter stock records based on the expiry date of the product
                        expired_stock = self.env['stock.quant'].search([
                            ('location_id', '=', loc_reanalysis.id),
                            ('product_id.expiry_date_calculated', '=', fields.Date.today()),
                            ('product_id.id', '=', rec.product_id.id)
                        ])

                        # Create a picking for the movement
                        picking_values = {
                            'location_id': loc_reanalysis.id,
                            'location_dest_id': unrestricted_location.id,
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
                                'location_id': loc_reanalysis.id,
                                'location_dest_id': unrestricted_location.id,
                                'picking_id': picking.id,
                            })
                        s = self.env['stock.move'].create(move_line_values)
                        s.write({'state': 'assigned'})
                        s.move_line_ids.write({'state': 'done'})

                        # Confirm and validate the picking to move products to Reanalysis location
                        picking.action_confirm()
                        picking.button_validate()
                        # stock_move.write({'location_dest_id': unrestricted_location.id})
                        # stock_move.move_line_ids.write({'state': 'done'})
                        return super(CustomQualityCheckLocation, rec).do_pass()
                    else:
                        raise ValidationError('Reanalysis location not found')
                else:
                    return super(CustomQualityCheckLocation, rec).do_pass()
            else:
                production_id = rec.production_id
                print(production_id.name,"protufhfhd")
                return super(CustomQualityCheckLocation, rec).do_pass()

    # After the Cron job is executed then this code it used to move the products from Reanalysis to Blocked Location
    def do_fail(self):
        for rec in self:
            picking_id = rec.picking_id

            if picking_id:
                print(picking_id, "picking id print")
                if picking_id.state != 'done':
                    picking_id.button_validate()
                stock_move = self.env['stock.move'].search([
                    ('picking_id', '=', picking_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('state', '=', 'done')
                ], limit=1)

                if stock_move:
                    print(stock_move, "stock moves")
                    reanalysis_location = self.env['stock.location'].search([('name', '=', 'Reanalysis')],
                                                                            limit=1)
                    if reanalysis_location:
                        loc_blocked = self.env['stock.location'].search([('name', '=', 'Restricted')], limit=1)

                        # Filter stock records based on the expiry date of the product
                        expired_stock = self.env['stock.quant'].search([
                            ('location_id', '=', reanalysis_location.id),
                            ('product_id.expiry_date_calculated', '=', fields.Date.today()),
                            ('product_id.id', '=', rec.product_id.id)
                        ])

                        # Create a picking for the movement
                        picking_values = {
                            'location_id': reanalysis_location.id,
                            'location_dest_id': loc_blocked.id,
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
                                'location_id': reanalysis_location.id,
                                'location_dest_id': loc_blocked.id,
                                'picking_id': picking.id,
                            })
                        s = self.env['stock.move'].create(move_line_values)
                        s.write({'state': 'assigned'})
                        s.move_line_ids.write({'state': 'done'})

                        # Confirm and validate the picking to move products to Reanalysis location
                        picking.action_confirm()
                        picking.button_validate()
                        # stock_move.write({'location_dest_id': unrestricted_location.id})
                        # stock_move.move_line_ids.write({'state': 'done'})
                        return super(CustomQualityCheckLocation, rec).do_fail()
                    else:
                        raise ValidationError('Restricted location not found')
                else:
                    return super(CustomQualityCheckLocation, rec).do_fail()
            else:
                production_id = rec.production_id
                print(production_id.name, "production_id")
                return super(CustomQualityCheckLocation, rec).do_fail()

    # code to call the validate button
    def button_validate(self):
        for rec in self:
            print(rec.picking_id)
            rec.picking_id.button_validate()

# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseChanges(http.Controller):
#     @http.route('/purchase_changes/purchase_changes', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_changes/purchase_changes/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_changes.listing', {
#             'root': '/purchase_changes/purchase_changes',
#             'objects': http.request.env['purchase_changes.purchase_changes'].search([]),
#         })

#     @http.route('/purchase_changes/purchase_changes/objects/<model("purchase_changes.purchase_changes"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_changes.object', {
#             'object': obj
#         })


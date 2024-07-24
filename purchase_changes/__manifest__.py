# -*- coding: utf-8 -*-
{
    'name': "purchase_changes",

    'version': '1.0',
    'summary': 'Purchase Requisition ',
    'sequence': 10,
    'price':'10.0',
    'currency':'USD',
    'description': """

    """,

    'depends': ['base', 'purchase', 'stock', 'quality_control', 'sale', 'sale_stock','sale_mrp','crm'],

    'data': [
        'security/ir.model.access.csv',
        'views/purchase_req_lines.xml',
        'views/sale_multiple_dc.xml',
        'views/puchase_req.xml',
        'views/quality_check_form.xml',
        'views/GroupsAcess.xml',
    ],

    'installable': True,
    'application': True,

    'license': 'LGPL-3',

}

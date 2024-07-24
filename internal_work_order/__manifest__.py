# -*- coding: utf-8 -*-
{
    'name': "internal_work_order",

    'version': '17.0',
    'sequence': 5,
    'price':'10.0',
    'currency':'USD',
    'description': """

    """,

    'depends': ['base', 'purchase', 'stock', 'quality_control', 'sale', 'sale_stock','sale_mrp'],

    'data': [
        'security/ir.model.access.csv',
        'views/internal_work_views.xml',

    ],

    'installable': True,
    'application': True,

    'license': 'LGPL-3',

}

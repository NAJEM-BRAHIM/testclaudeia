# -*- coding: utf-8 -*-
  {                                                                                                                                                                         
      'name': 'Virtual Boxes',
      'summary': 'Número de cajas por línea en pedidos de venta y albaranes',                                                                                               
      'version': '19.0.1.0.0',                                    
      'category': 'Inventory',                                                                                                                                              
      'author': 'Custom',
      'license': 'LGPL-3',                                                                                                                                                  
      'depends': ['sale_stock', 'account'],                       
      'data': [
          'views/sale_order_views.xml',                                                                                                                                     
          'views/report_sale_views.xml',
          'views/report_stock_views.xml',                                                                                                                                   
          'views/report_invoice_views.xml',                       
      ],
      'installable': True,                                                                                                                                                  
      'application': False,
  }                                  
# -*- encoding: utf-8 -*-
##############################################################################
#
# ERP Heritage
# Copyright (C) 2025 (https://www.erpheritage.com.au/)
#
##############################################################################

{
    'name': "AI Claude (Anthropic) Integration",
    'summary': """Integrate Anthropic's Claude AI models into your Odoo AI ecosystem. Add Claude's advanced reasoning capabilities alongside your existing ChatGPT and Gemini options.""",
    'description': """
        Integrate Anthropic's Claude AI models into your Odoo AI ecosystem. Add Claude's advanced reasoning capabilities alongside your existing ChatGPT and Gemini options.
    """,
    'author': "ERP Heritage",
    'website': "https://www.erpheritage.com.au/",
    'license': 'LGPL-3',
    'category': 'Productivity/AI',
    'version': '19.0.1.0',
    'depends': ['ai', 'ai_app'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
}
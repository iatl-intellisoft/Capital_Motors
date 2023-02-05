# -*- coding: utf-8 -*-
# from odoo import http


# class IsHrCapital(http.Controller):
#     @http.route('/is_hr_capital/is_hr_capital/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/is_hr_capital/is_hr_capital/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('is_hr_capital.listing', {
#             'root': '/is_hr_capital/is_hr_capital',
#             'objects': http.request.env['is_hr_capital.is_hr_capital'].search([]),
#         })

#     @http.route('/is_hr_capital/is_hr_capital/objects/<model("is_hr_capital.is_hr_capital"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('is_hr_capital.object', {
#             'object': obj
#         })

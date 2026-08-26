# from odoo import http


# class Modultest(http.Controller):
#     @http.route('/modultest/modultest', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/modultest/modultest/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('modultest.listing', {
#             'root': '/modultest/modultest',
#             'objects': http.request.env['modultest.modultest'].search([]),
#         })

#     @http.route('/modultest/modultest/objects/<model("modultest.modultest"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('modultest.object', {
#             'object': obj
#         })


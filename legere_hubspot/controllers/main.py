import json

from odoo import http
from odoo.http import request
from datetime import datetime, timezone
from werkzeug.exceptions import Forbidden, NotFound

class Hubspot(http.Controller):

    @http.route('/webhook/hubspot', type='json', auth='public')
    def hubspot(self, **kwargs):
        print ("===========call hubspot")
        print ("===========request.httprequest.data", request.httprequest.data)
        req = json.loads(request.httprequest.data)

        return True
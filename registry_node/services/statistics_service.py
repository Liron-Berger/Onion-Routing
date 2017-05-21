#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common.utilities import util
from registry_node.services import base_service


GUI_HTML = util.read_file(
    os.open(
        "files/statistics_gui.html",
        os.O_RDONLY,
    ),
)

UNREGISTER_BUTTON = '''
 <tr><td>
    <button
        class="myButton"
        type="button" 
        onclick="location.href='/unregister?name=%s'"
        class="log-btn reg-text"
    >
        %s: Unregister
    </button>
</td></tr>
'''



class Socks5StatisticsService(base_service.BaseService):
    NAME = "/statistics"

    def before_response_headers(self):
        self._request_context["response"] = util.text_to_html(
            GUI_HTML,
        )
        super(Socks5StatisticsService, self).before_response_headers()

    def _unregister_form(
        self,
    ):
        forms = ""
        for node in self._application_context["registry"]:
            forms += UNREGISTER_BUTTON % (
                node,
                node,
            )
        return forms

#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


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



class Socks5StatisticsService(BaseService):
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
        
    def _table_data(
        self,
    ):
        rows = ""
        connection_num = 1
        for sock in self._application_context["connections"]:
            rows += ROW % (
                connection_num,
                self._application_context["connections"][sock]["in"]["fd"],
                self._application_context["connections"][sock]["in"]["bytes"],
                DISCONNECT_BUTTON % sock.fileno(),
                self._application_context["connections"][sock]["out"]["fd"],
                self._application_context["connections"][sock]["out"]["bytes"]
            )
            connection_num += 1
        return rows

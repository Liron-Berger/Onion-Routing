#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


GUI_HTML = '''
    <meta http-equiv="refresh" content="5" />
    <head>
        <link rel="stylesheet" href="pagewrap.css">
    </head>
    <div id="pagewrap">
        <header>
            <center>
                <h1>Onion Routing</h1>
            </center>
        </header>

        <section id="content">
            <h2>New Node Sign Up</h2>
        <form action="register">
            Node Name:<br>
            <input type="text" name="name">
            <br>
            Bind Address:<br>
            <input type="text" name="address">
            <br>
            Bind Port:<br>
            <input type="text" name="port">
            <br><br>
            <input type="submit" value="Register">
        </form>
        </section>

        <section id="middle">
            <h2>
                <center>
                Statistics
                </center>
            </h2>
            <table border="5" width=700 cellpadding="4" cellspacing="3">
                <tr><th colspan="5"> Connections: %s</th></tr>
                <tr><th> </th><th> Socket Type </th><th> Socket File Descriptor </th><th> Bytes </th><th> </th></tr>
                %s
            </table>
        </section>

        <aside id="sidebar">
            <center>
                <h2>Existing Nodes</h2>
                %s
            </center>
        </aside>

        <footer>
            <h4>Onion Chain Visualizer</h4>
            <p>Coming soon...</p>
        </footer>
    </div>
'''

UNREGISTER_BUTTON = '''
    <button 
        type="button" 
        onclick="location.href='/unregister?name=%s'"
        class="log-btn reg-text"
    >
        %s: Unregister
    </button>
'''

ROW = '''
    <tr align="center"> 
        <td rowspan="2"> %s </td>
        <td> server </td>
        <td> %s </td>
        <td> %s </td>
        <td rowspan="2"> %s </td>            
    </tr>
    <tr align="center"> 
        <td> partner </td>
        <td> %s </td>
        <td> %s </td>
    </tr>
'''

DISCONNECT_BUTTON = '''
    <button 
        type="button" 
        onclick="location.href='/disconnect?connection=%d'"
        class="log-btn reg-text"
    >
        Disconnect
    </button>
'''



class Socks5StatisticsService(BaseService):
    NAME = "/statistics"

    def before_response_headers(self):
        self._request_context["response"] = util.text_to_html(
            GUI_HTML % (
                len(self._application_context["connections"]),
                self._table_data(),
                self._unregister_form(),
            )
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

#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


class Socks5StatisticsService(BaseService):
    NAME = "/statistics"

    def __init__(
        self,
        request_context,
        application_context,
        parse,
    ):
        super(Socks5StatisticsService, self).__init__(
            request_context,
            application_context,
            parse,
        )

    def _content(
        self,
    ):
        self._request_context["response"] = self._create_table()

    def _create_table(
        self,
    ):
        table = '''<table border="5" width="50%" cellpadding="4" cellspacing="3">'''
        table += '''<tr><th colspan="5"><br><h3> %s </h3></th></tr>''' % "Socks Statistics"
        table += '''<tr><th colspan="5"> Connections: %s </th></tr>''' % len(self._application_context["connections"])
        table += "<tr><th> %s </th><th> %s </th><th> %s </th><th> %s </th><th> %s </th></tr>" % (
            "",
            "Socket Type",
            "Socket File Descriptor",
            "Bytes",
            "Disconnect",
        )
        connection_num = 1
        for sock in self._application_context["connections"]:
            table += '''<tr align="center"> %s </tr>''' % (
                '''<td rowspan="2"> %s </td>''' % connection_num +
                "<td> %s </td>" % "server" +
                "<td> %s </td>" % self._application_context["connections"][sock]["in"]["fd"] +
                "<td> %s </td>" % self._application_context["connections"][sock]["in"]["bytes"] +
                '''<td rowspan="2"> %s </td>''' % self._get_disconnect_form(
                    sock, 
                )
            )           

            table += '''<tr align="center"> %s </tr>''' % (
                "<td> %s </td>" % "partner" +
                "<td> %s </td>" % self._application_context["connections"][sock]["out"]["fd"] +
                "<td> %s </td>" % self._application_context["connections"][sock]["out"]["bytes"]
            )
            connection_num += 1
        return table

    def _get_disconnect_form(
        self,
        sock1,
    ):
        return '''
        <form action="disconnect">
            <input type="hidden" name="connection" value="%d" />
            <input type="submit" value="Disconnect">
        </form>
        ''' % (
            sock1,
        )

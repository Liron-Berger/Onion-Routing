#!/usr/bin/python

import base64
import Cookie
import datetime
import os
import urlparse

from common import constants
from common import util
from baseService import BaseService


REGISTER_FORM = "/register.html"


class Socks5StatisticsService(BaseService):
    NAME = "/statistics"

    def before_response_headers(self):
        try:
            register = os.path.normpath(
                '%s%s' % (
                    "./files",
                    os.path.normpath(REGISTER_FORM),
                )
            )
            register_form_fd = os.open(register, os.O_RDONLY)
        except Exception as e:
            raise util.HTTPError(500, "Internal Error", str(e))


        self._request_context["response"] = util.text_to_html(
            self._register_form(register_form_fd) +
            self._unregister_form() +
            self._create_table(),
        )
        super(Socks5StatisticsService, self).before_response_headers()

    def _register_form(
        self,
        fd,
    ):
        return os.read(
            fd,
            self._application_context["max_buffer_size"] - len(self._request_context["response"]),
        )


    def _unregister_form(
        self,
    ):
        forms = ""
        for node in self._application_context["registry"]:
            forms += '''
                <form style="float:right" action="unregister">
                    <input type="hidden" name="name" value="%s" />
                    <input type="submit" value="unregister: %s">
                </form>
            ''' % (
                node,
                node,
            )
        return forms

    def _create_table(
        self,
    ):
        table = '''<table style="float:left" border="5" width="50%" cellpadding="4" cellspacing="3">'''
        table += '''<tr><th colspan="5"><br><h3> %s </h3></th></tr>''' % "Socks Statistics"
        table += '''<tr><th colspan="5"> Connections: %s </th></tr>''' % len(self._application_context["connections"])
        table += "<tr><th> %s </th><th> %s </th><th> %s </th><th> %s </th><th> %s </th></tr>" % (
            "",
            "Socket Type",
            "Socket File Descriptor",
            "Bytes",
            "",
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
        sock,
    ):
        return '''
        <form action="disconnect">
            <input type="hidden" name="connection" value="%d" />
            <input type="submit" value="Disconnect">
        </form>
        ''' % (
            sock.fileno(),
        )

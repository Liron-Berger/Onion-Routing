#!/usr/bin/python
## @package onion_routing.common.utilities.http_util
# utilities for HTTP/1.1.
#

import urlparse

from common import constants


## Error used for handling errors in HTTP protocol.
class HTTPError(RuntimeError):

    ## Constructor.
    # @param code (int) code of HTTP error.
    # @param status (str) status of http error.
    # @param message (str) the error.
    #
    def __init__(
        self,
        code,
        status,
        message="",
    ):
        super(HTTPError, self).__init__(message)
        self.code = code
        self.status = status
        self.message = message


## Get first line of HTTP request.
# @param buffer (str) request buffer.
# @param request_context (dict) request context
# of @ref registry_socket.pollables.http_socket.
#
# @returns (bool) whether first line is HTTP protocol
# request with supported methods.
#
def get_first_line(
    buffer,
    request_context,
):
    req, buffer = recv_line(buffer)

    if not req:
        return False, buffer

    req_comps = req.split(" ", 2)
    if len(req_comps) != 3:
        raise RuntimeError("Incomplete HTTP protocol")
    if req_comps[2] != constants.HTTP_SIGNATURE:
        raise RuntimeError("Not HTTP protocol")

    method, uri, signature = req_comps
    if method != 'GET':
        raise RuntimeError(
            "HTTP unsupported method '%s'" % method
        )
    if not uri or uri[0] != '/':
        raise RuntimeError("Invalid URI")

    request_context["uri"] = uri
    request_context["parse"] = urlparse.urlparse(uri)

    return True, buffer


## Get headers of HTTP request.
# @param buffer (str) request buffer.
# @param request_context (dict) request context.
# @param service_class (service) service class for wanted headers.
# @returns (bool) whether end of headers was read.
#
# Goes over buffer and reads lines until buffer is empty.
# More headers than MAX_NUMBER_OF_HEADERS raises RuntimeError.
#
def get_headers(
    buffer,
    request_context,
    service_class,
):
    finished = False
    for i in range(constants.MAX_NUMBER_OF_HEADERS):
        line, buffer = recv_line(buffer)
        if line is None:
            break
        if line == "":
            finished = True
            break
        line = parse_header(line)
        if line[0] in service_class.wanted_headers():
            request_context["request_headers"][line[0]] = line[1]
    else:
        raise RuntimeError("Exceeded max number of headers")
    return finished, buffer


## Get content of HTTP request.
# @param buffer (str) request buffer.
# @param request_context (dict) request context.
# @returns (str) buffer without read content.
#
# Goes over buffer and reads all content according to content_length header.
#
def get_content(
    buffer,
    request_context,
):
    if "content_length" in request_context:
        content = buffer[:min(
            request_context["content_length"],
            request_context[
                "app_context"
            ]["max_buffer_size"] - len(request_context["content"]),
        )]
        request_context["content"] += content
        request_context["content_length"] -= len(content)
        buffer = buffer[len(content):]
    return buffer


## Set headers for HTTP response.
# @param buffer (str) request buffer.
# @param request_context (dict) request context.
# @returns (bool, str) whether finished setting all headers,
# buffer with additional headers.
#
# Goes over buffer and reads all content according to content_length header.
#
def set_headers(
    buffer,
    request_context,
):
    for key, value in request_context["response_headers"].iteritems():
        buffer += (
            "%s: %s\r\n" % (key, value)
        )
    buffer += ("\r\n")
    return True, buffer


## Recv line.
# @param buffer (str) request buffer.
#
# @returns (str, str) buffer until "\r\n", buffer after "\r\n".
#
def recv_line(buffer):
    n = buffer.find(constants.CRLF_BIN)

    if n == -1:
        return None

    line = buffer[:n].decode("utf-8")
    buffer = buffer[n + len(constants.CRLF_BIN):]
    return line, buffer


## Parse HTTP header.
# @param header (string) original header line from request.
# @returns (str, str) header title, header content.
#
def parse_header(header):
    SEP = ':'
    n = header.find(SEP)
    if n == -1:
        raise RuntimeError('Invalid header received')
    return header[:n].rstrip(), header[n + len(SEP):].lstrip()


## Wrapping a certain text with html headers.
# @param text (str) the message to turn into html.
# @returns (str) html message.
#
def text_to_html(
    text,
):
    return (
        "<HTML>\r\n<BODY>\r\n%s\r\n</BODY>\r\n</HTML>" % text
    ).decode('utf-8')

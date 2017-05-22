#!/usr/bin/python
## @package onion_routing.common.utilities.http_util
# utilities for HTTP/1.1.
#


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

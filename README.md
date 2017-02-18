Socks5 asynchronous server
=======================================

ABOUT
        This project implements an asynchronous server using the Socks5 protocol.
        Socks5 is used in order to create a connection between client and server.

        For further reading about the Socks5 protocol look at https://www.ietf.org/rfc/rfc1928.txt

FEATURES
        In this version, no authentication methods are supported via socks 5 protocol.
        Connecting procedure is:
            Greeting Request
                    |
            Greeting Response
                    |
            Authentication Request      |
                    |                   |   Not implemented and differs for each method (if supported)
            Authentication Response     |
                    |
            Socks5 Request
                    |
            Socks5 Response
                    |
            connection established

EXECUTE EXAMPLE
        Windows: python main.py --proxy 0.0.0.0:1080
        Linux: $ ./main.py --proxy 0.0.0.0:1080

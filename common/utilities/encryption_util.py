#!/usr/bin/python
## @package onion_routing.common.utilities.encryption_util
# utilities for handling encryption.
## @file encryption_util.py
# Implementation of @ref onion_routing.common.utilities.encryption_util
#


## Encrypt data based on a certain key.
# @param buffer (str) the future encrypt message.
# @param key (int) key for encryption.
# @returns (str) encrypted message.
#
# Ecryption is xor based.
#
def encrypt(
    buffer,
    key,
):
    return "".join(chr(ord(a) ^ key) for a in buffer)


## Decrypt data based on a certain key.
# @param buffer (str) the encrypted message.
# @param key (int) key for encryption.
# @returns (str) decrypted message.
#
# Decryption is xor based.
#
def decrypt(
    buffer,
    key,
):
    return "".join(chr(ord(a) ^ key) for a in buffer)

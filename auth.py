import hmac
import hashlib
import struct
import time

def HOTP(K, C, digits=6, digestmod=hashlib.sha1):
    C_bytes = struct.pack(b"!Q", C)
    hmac_digest = hmac.new(key=K, msg=C_bytes,
                           digestmod=digestmod).hexdigest()
    return Truncate(hmac_digest)[-digits:]


def TOTP(K, digits=6, window=30, clock=None, digestmod=hashlib.sha1):
    if clock is None:
        clock = time.time()
    C = int(clock / window)
    return HOTP(K, C, digits=digits, digestmod=digestmod)


def Truncate(hmac_digest):
    offset = int(hmac_digest[-1], 16)
    binary = int(hmac_digest[(offset * 2):((offset * 2) + 8)], 16) & 0x7fffffff
    return str(binary)

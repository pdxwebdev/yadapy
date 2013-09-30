import re, logging
from uuid import uuid4, UUID
from Crypto.Cipher import AES
from base64 import b64encode, b64decode

def decrypt(key, iv, data):
# the block size for the cipher object; must be 16, 24, or 32 for AES
    BLOCK_SIZE = 16
    key = UUID(key).bytes
    iv = UUID(iv).bytes
    
    # the character used for padding--with a block cipher such as AES, the value
    # you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
    # used to ensure that your value is always a multiple of BLOCK_SIZE
    PADDING = '`'
    p = re.compile('[`]+$')
    p.sub('',data)
    # one-liner to sufficiently pad the text to be encrypted
    pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

    DecodeAES = lambda c, e: c.decrypt(b64decode(e)).rstrip(PADDING)
    
    # create a cipher object using the random secret
    cipher = AES.new(key, AES.MODE_ECB)
    
    # encode a string
    #encoded = EncodeAES(cipher, data)
    #print('Encrypted string:', encoded)
    decoded = DecodeAES(cipher, data)
    
    return decoded[:decoded.rfind('}')+1]

def encrypt( key, iv, data):
    # the block size for the cipher object; must be 16, 24, or 32 for AES
    BLOCK_SIZE = 16
    key = UUID(key).bytes
    iv = UUID(iv).bytes
    # the character used for padding--with a block cipher such as AES, the value
    # you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
    # used to ensure that your value is always a multiple of BLOCK_SIZE
    PADDING = '`'
    
    # one-liner to sufficiently pad the text to be encrypted
    pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING

    #cipher = self.build_cipher(key, iv, enc)
    EncodeAES = lambda c, s: b64encode(c.encrypt(pad(s)))

    # create a cipher object using the random secret
    cipher = AES.new(key, AES.MODE_ECB)
    
    # encode a string
    encoded = EncodeAES(cipher, data)
    #print('Encrypted string:', encoded)

    return encoded
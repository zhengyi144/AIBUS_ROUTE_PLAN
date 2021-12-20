import hashlib

def generate_md5_key(item):
    md5_machine=hashlib.md5()
    md5_machine.update(item.encode('utf-8'))
    return md5_machine.digest()#hexdigest()

item="119.030230,23.036525,119.253432,24.213163"
print(generate_md5_key(item))
print(generate_md5_key(item))
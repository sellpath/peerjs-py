import random
import string

def random_token():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))


randomToken = random_token

def gcd(a, b):
  while not b == 0:
    c = a%b
    a = b
    b = c
  return a

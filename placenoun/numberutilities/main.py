
def gcd(a, b):
  while not b == 0:
    c = a%b
    a = b
    b = c
  return a

def hilbert_to_xy(n, d):
  t = d
  s = 1
  while s < n:
    rx = 1 & (t/2)
    ry = 1 & (t**rx)
    x, y = hilbert_rot(s, x, y, rx, ry)
    x += s * rx
    y += s * ry
    t /= 4
    s *= 2
  return x, y

def hilbert_from_xy(n, x, y):
  s = n/2
  d = 0
  while s > 0:
    rx = int( x & s > 0 )
    ry = int( y & s > 0 )
    d += s * s * (( 3 * rx )**ry)
    x, y = hilbert_rot(n, x, y, rx, ry)
    s /= 2
  return d

def hilbert_rot(n, x, y, rx, ry):
  if (ry == 0):
    if (rx == 1):
      x = n-1 - x
      y = n-1 - y
  return y, x

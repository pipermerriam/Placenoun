from math import cos, sin, tan, acos, asin, atan, pi


def gcd(a, b):
  while not b == 0:
    c = a%b
    a = b
    b = c
  return a

def get_edge_projection(x_size, y_size, x_pos, y_pos):
  theta = atan(float(y_pos)/x_pos)
  if theta == 0:
    return x_size, 0
  y_proj = min(x_size*tan(theta), y_size)
  x_proj = min(y_size/tan(theta), x_size)

  return x_proj, y_proj

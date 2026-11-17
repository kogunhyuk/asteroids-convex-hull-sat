"""2D 벡터 연산 모음 (Mathematics 01, 06, 07 강의 내용)

벡터는 (x, y) 튜플로 표현한다.
"""
from math import sqrt, sin, cos


def add(*vectors):
    """여러 벡터의 합"""
    return tuple(map(sum, zip(*vectors)))


def subtract(v1, v2):
    """v1 - v2"""
    return tuple(a - b for a, b in zip(v1, v2))


def scale(s, v):
    """스칼라 곱 s * v"""
    return tuple(s * c for c in v)


def dot(u, v):
    """내적 u · v = ux*vx + uy*vy (Mathematics 07)"""
    return sum(a * b for a, b in zip(u, v))


def length(v):
    """벡터의 크기 |v|"""
    return sqrt(dot(v, v))


def distance(p1, p2):
    """두 점 사이의 거리"""
    return length(subtract(p1, p2))


def to_cartesian(polar):
    """극좌표 (r, θ) → 직교좌표 (x, y)"""
    r, theta = polar
    return (r * cos(theta), r * sin(theta))


def rotate2d(angle, v):
    """회전 행렬 [[cos, -sin], [sin, cos]] 적용 (Mathematics 06)"""
    x, y = v
    return (x * cos(angle) - y * sin(angle),
            x * sin(angle) + y * cos(angle))


#추가됨
def normalize(v):
    """크기가 1인 단위 벡터 (디버그 화면에서 축을 그릴 때 사용)"""
    n = length(v)
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


#추가됨
def perpendicular(v):
    """90° 회전 R90 = [[0, -1], [1, 0]] 적용 → 원래 벡터와 수직 (Mathematics 06, 4쪽)
    변 벡터에 적용하면 그 변의 법선이 된다. 내적: -vy*vx + vx*vy = 0"""
    return (-v[1], v[0])

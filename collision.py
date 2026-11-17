"""충돌 검출 (LectureNote 06 Collision Detection)

1단계: AABB 판정 + 레이저용 선분 교차 판정
#추가됨
2단계: 볼록 다각형 SAT (Separating Axis Theorem)
#추가됨
3단계: Convex Hull (Monotone Chain 알고리즘)
#변경됨
4단계: 바운딩 원으로 먼저 거르는 2단계 판정 (Broad phase → Narrow phase)
"""
from dataclasses import dataclass
from itertools import combinations

import vectors


# ---------------------------------------------------------------------------
# AABB (Axis-Aligned Bounding Box)
# ---------------------------------------------------------------------------
@dataclass
class AABB:
    min_pt: tuple   # (x_min, y_min)
    max_pt: tuple   # (x_max, y_max)


def compute_aabb(points):
    """월드 좌표 꼭짓점들을 감싸는 축 정렬 상자
    회전할 때마다 꼭짓점이 바뀌므로 매 프레임 다시 계산해야 한다 (06강 31쪽)"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return AABB((min(xs), min(ys)), (max(xs), max(ys)))


def aabb_overlap(a, b):
    """06강 28쪽 의사코드: 한 축이라도 떨어져 있으면 충돌 아님"""
    if a.max_pt[0] < b.min_pt[0] or b.max_pt[0] < a.min_pt[0]:
        return False
    if a.max_pt[1] < b.min_pt[1] or b.max_pt[1] < a.min_pt[1]:
        return False
    return True  # 모든 축에서 겹침 → 충돌


def find_colliding_pairs_aabb(aabbs):
    """모든 쌍을 검사해서 AABB가 겹치는 (i, j) 쌍 목록을 반환"""
    pairs = []
    for i, j in combinations(range(len(aabbs)), 2):
        if aabb_overlap(aabbs[i], aabbs[j]):
            pairs.append((i, j))
    return pairs


#추가됨
# ---------------------------------------------------------------------------
# SAT: 임의의 볼록 다각형 (06강 35~37쪽을 박스에서 다각형으로 일반화)
# ---------------------------------------------------------------------------
def get_axes(points):
    """분리축 후보 = 각 변의 법선
    변 e_i = p_(i+1) - p_i 를 90° 회전한 벡터. 마지막 변은 p_(n-1) → p_0.
    겹침 '여부'만 볼 때는 정규화하지 않아도 된다 (양쪽 투영에 같은 배율이 곱해지므로)."""
    axes = []
    n = len(points)
    for i in range(n):
        edge = vectors.subtract(points[(i + 1) % n], points[i])
        if edge == (0, 0):
            continue  # 길이 0인 변은 축을 만들 수 없음
        axes.append(vectors.perpendicular(edge))
    return axes


#추가됨
def project(points, axis):
    """모든 꼭짓점을 축에 내적으로 투영한 구간 [min, max] (Mathematics 07)"""
    dots = [vectors.dot(p, axis) for p in points]
    return min(dots), max(dots)


#추가됨
def find_separating_axis(points_a, points_b):
    """두 다각형의 모든 변 법선을 검사해서 처음 찾은 분리축을 반환, 없으면 None
    분리축을 하나라도 찾으면 그 즉시 '충돌 아님'으로 끝낸다 (early exit)."""
    for axis in get_axes(points_a) + get_axes(points_b):
        min_a, max_a = project(points_a, axis)
        min_b, max_b = project(points_b, axis)
        if max_a < min_b or max_b < min_a:
            return axis  # 이 축 위에서 두 구간 사이에 틈이 있음
    return None


#추가됨
def sat_overlap(points_a, points_b):
    """분리축이 하나도 없으면 충돌 (볼록 다각형일 때만 정확함)"""
    return find_separating_axis(points_a, points_b) is None


#추가됨
def find_colliding_pairs_sat(polygons):
    """모든 쌍을 SAT로 검사 (4단계에서 바운딩 원으로 먼저 거르도록 개선 예정)"""
    pairs = []
    for i, j in combinations(range(len(polygons)), 2):
        if sat_overlap(polygons[i], polygons[j]):
            pairs.append((i, j))
    return pairs


#추가됨
# ---------------------------------------------------------------------------
# Convex Hull: 오목 다각형을 볼록 껍질로 감싸 SAT를 쓸 수 있게 만든다
# ---------------------------------------------------------------------------
def cross(o, a, b):
    """외적의 z 성분 (Mathematics 08의 공식에서 z = 0으로 둔 것)
    o → a → b 가  > 0 : 왼쪽(반시계)으로 꺾임
                  < 0 : 오른쪽(시계)으로 꺾임
                  = 0 : 일직선"""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


#추가됨
def convex_hull(points):
    """Monotone Chain (Andrew) 알고리즘, O(n log n)
    1) 점을 x(같으면 y) 기준으로 정렬
    2) 왼쪽→오른쪽으로 아래 껍질, 오른쪽→왼쪽으로 위 껍질을 만든다
    3) 새 점을 넣을 때 마지막 두 점과 왼쪽으로 꺾이지 않으면(cross <= 0)
       마지막 점은 껍질 안쪽(오목한 점) 또는 일직선 위의 점이므로 버린다
    결과: 반시계 방향 순서의 꼭짓점 목록"""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # 각 껍질의 마지막 점은 다른 껍질의 첫 점과 같으므로 중복 제거
    return lower[:-1] + upper[:-1]


#추가됨
# ---------------------------------------------------------------------------
# 2단계 판정: 바운딩 원(싼 판정)으로 먼저 거르고, 통과한 쌍만 SAT(비싼 판정)
# 06강 23쪽: 비싼 판정 앞에 싼 판정을 두어 일찍 빠져나오는 "early out"
# ---------------------------------------------------------------------------
def circles_overlap(c1, r1, c2, r2):
    """r1 + r2 > 중심 사이 거리 (06강 25쪽)
    제곱끼리 비교하면 제곱근 계산을 생략할 수 있다."""
    dx = c1[0] - c2[0]
    dy = c1[1] - c2[1]
    return dx * dx + dy * dy < (r1 + r2) ** 2


#추가됨
def find_colliding_pairs_two_phase(centers, radii, polygons):
    """1차: 바운딩 원 판정 → 2차: 원이 겹친 쌍만 SAT
    바운딩 원은 모든 꼭짓점(=Hull 전체)을 감싸므로, 1차에서 걸러진 쌍은
    실제로도 절대 충돌하지 않는다 → 결과는 '모든 쌍 SAT'와 완전히 같다.
    반환: (충돌 쌍 목록, SAT를 실제로 실행한 횟수)"""
    pairs = []
    sat_runs = 0
    for i, j in combinations(range(len(polygons)), 2):
        if not circles_overlap(centers[i], radii[i], centers[j], radii[j]):
            continue  # early out: SAT 생략
        sat_runs += 1
        if sat_overlap(polygons[i], polygons[j]):
            pairs.append((i, j))
    return pairs, sat_runs


# ---------------------------------------------------------------------------
# 레이저 판정: 선분 교차 (04강 5쪽, 연립일차방정식)
# ---------------------------------------------------------------------------
def standard_form(p1, p2):
    """두 점을 지나는 직선을 ax + by = c 꼴로"""
    x1, y1 = p1
    x2, y2 = p2
    a = y2 - y1
    b = x1 - x2
    c = x1 * y2 - x2 * y1
    return a, b, c


def line_intersection(s1, s2):
    """두 직선의 교점 (크래머 공식). 평행하면 None"""
    a1, b1, c1 = standard_form(*s1)
    a2, b2, c2 = standard_form(*s2)
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-12:
        return None
    x = (c1 * b2 - c2 * b1) / det
    y = (a1 * c2 - a2 * c1) / det
    return (x, y)


def segments_intersect(s1, s2):
    """교점이 두 선분 '안'에 있으면 True"""
    p = line_intersection(s1, s2)
    if p is None:
        return False
    d1 = vectors.distance(*s1)
    d2 = vectors.distance(*s2)
    eps = 1e-9
    return (vectors.distance(s1[0], p) <= d1 + eps and
            vectors.distance(s1[1], p) <= d1 + eps and
            vectors.distance(s2[0], p) <= d2 + eps and
            vectors.distance(s2[1], p) <= d2 + eps)


def laser_hits(model, laser):
    """레이저가 다각형의 어느 한 변이라도 지나면 명중"""
    return any(segments_intersect(seg, laser) for seg in model.segments())

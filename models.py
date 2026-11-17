"""게임 객체 (LectureNote 04 Physics의 Asteroids 구조)

PolygonModel
 ├─ Ship      : 플레이어가 조종하는 삼각형
 └─ Asteroid  : 무작위 다각형 소행성
"""
from math import pi
from random import randint, uniform

import vectors
#추가됨
from collision import convex_hull

# 수학 좌표계의 범위: x, y 모두 -10 ~ 10 (LectureNote 04, 10쪽)
WORLD_MIN, WORLD_MAX = -10, 10
WORLD_SIZE = WORLD_MAX - WORLD_MIN


class PolygonModel:
    """모양(로컬 좌표 꼭짓점)은 그대로 두고 회전·이동만 하는 강체"""

    def __init__(self, points):
        self.points = points          # 로컬 좌표 꼭짓점 (중심이 원점)
        self.rotation_angle = 0
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0
        self.angular_velocity = 0

    #변경됨
    def transformed(self, points=None):
        #변경됨
        """로컬 꼭짓점 → 월드 좌표 (회전을 먼저, 이동을 나중에 적용)
        points를 주면 그 점들(예: Hull)을 같은 회전·위치로 변환한다."""
        #추가됨
        if points is None:
            points = self.points
        #변경됨
        rotated = [vectors.rotate2d(self.rotation_angle, v) for v in points]
        return [vectors.add((self.x, self.y), v) for v in rotated]

    def move(self, milliseconds):
        """등속 운동 + 등각속도 회전, 화면 밖으로 나가면 반대편에서 등장"""
        dt = milliseconds / 1000.0
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rotation_angle += self.angular_velocity * dt

        if self.x < WORLD_MIN:
            self.x += WORLD_SIZE
        elif self.x > WORLD_MAX:
            self.x -= WORLD_SIZE
        if self.y < WORLD_MIN:
            self.y += WORLD_SIZE
        elif self.y > WORLD_MAX:
            self.y -= WORLD_SIZE

    def segments(self):
        """월드 좌표 기준 변(선분) 목록"""
        pts = self.transformed()
        n = len(pts)
        return [(pts[i], pts[(i + 1) % n]) for i in range(n)]


class Ship(PolygonModel):
    def __init__(self):
        super().__init__([(0.5, 0), (-0.25, 0.25), (-0.25, -0.25)])  # 삼각형

    def laser_segment(self, laser_length=20):
        """우주선 앞쪽 꼭짓점에서 바라보는 방향으로 뻗는 레이저"""
        nose = self.transformed()[0]
        direction = vectors.to_cartesian((laser_length, self.rotation_angle))
        return nose, vectors.add(nose, direction)


class Asteroid(PolygonModel):
    #변경됨
    def __init__(self, min_radius=0.5, max_radius=1.0):
        sides = randint(5, 9)  # 5~9각형
        # 각도는 일정 간격, 중심으로부터의 거리는 무작위
        # → 이웃보다 짧은 꼭짓점이 생기면 안쪽으로 패여 '오목'해질 수 있음
        #추가됨
        # 강의 기본값은 0.5~1.0. min_radius를 줄이면 더 깊게 패인 소행성이 나온다.
        #변경됨
        vs = [vectors.to_cartesian((uniform(min_radius, max_radius), 2 * pi * i / sides))
              for i in range(sides)]
        super().__init__(vs)
        self.vx = uniform(-1, 1)
        self.vy = uniform(-1, 1)
        self.angular_velocity = uniform(-pi / 2, pi / 2)

        #추가됨
        # 소행성은 강체(모양이 변하지 않음)이므로 로컬 좌표에서 Hull을 '한 번만' 계산.
        # 회전·이동은 모양을 바꾸지 않으니, 매 프레임에는 Hull 꼭짓점만 변환하면 된다.
        self.hull = convex_hull(self.points)
        #추가됨
        # Hull에 포함되지 않은 꼭짓점 = 안쪽으로 패인 오목한 꼭짓점
        self.concave_points = [p for p in self.points if p not in self.hull]
        #추가됨
        self.is_concave = len(self.concave_points) > 0

        #추가됨
        # 바운딩 원 반지름 = 중심에서 가장 먼 꼭짓점까지의 거리
        # 원은 회전해도 모양이 같으므로 AABB와 달리 다시 계산할 필요가 없다.
        self.bound_radius = max(vectors.length(p) for p in self.points)

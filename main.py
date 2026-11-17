#변경됨
"""Asteroids 충돌 검출 데모 - 3단계: AABB vs SAT vs Hull + SAT

조작법
#변경됨
  1 / 2 / 3 : 판정 방식 전환 (1 = AABB, 2 = 원래 다각형 SAT, 3 = Hull + SAT)
  ← / →   : 우주선 회전
  ↑ / ↓   : 전진 / 후진 가속
  SPACE   : 레이저 발사 (맞은 소행성 파괴)
  B       : AABB 상자 표시 켜기/끄기
  #추가됨
  C       : 바운딩 원 표시 켜기/끄기
  #추가됨
  D       : 디버그 화면 (가장 가까운 두 소행성의 분리축과 투영 구간)
  #추가됨
  K       : 오목 정도 전환 (강의 기본 0.5~1.0 ↔ 깊게 패임 0.3~1.0) 후 재배치
  #추가됨
  S       : 누적 통계 초기화
  P       : 일시정지
  R       : 소행성 새로 배치
  + / -   : 소행성 개수 늘리기 / 줄이기
  ESC     : 종료
"""
import random
from math import cos, sin
#추가됨
from itertools import combinations

import pygame

import vectors
from models import Ship, Asteroid
#변경됨
from collision import (compute_aabb, find_colliding_pairs_aabb,
                       find_colliding_pairs_sat, find_colliding_pairs_two_phase,
                       find_separating_axis, project, laser_hits)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 800
FPS = 60
NUM_ASTEROIDS = 12
SEED = 7                 # 같은 장면을 재현하고 싶을 때 고정 (None이면 매번 무작위)
ACCELERATION = 3
ROTATION_SPEED = 3       # rad/s

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (80, 220, 120)
RED = (255, 70, 70)
GRAY = (110, 110, 130)
YELLOW = (255, 210, 80)

#추가됨
#변경됨
MODES = {pygame.K_1: "AABB", pygame.K_2: "SAT", pygame.K_3: "HULL+SAT"}
#추가됨
ORANGE = (255, 160, 60)
#추가됨
CYAN = (80, 200, 255)
#추가됨
DIM = (60, 60, 80)
#추가됨
RADIUS_PRESETS = [0.5, 0.3]   # min_radius: 강의 기본값 / 깊게 패인 소행성


# ---------------------------------------------------------------------------
# 좌표 변환과 그리기 (04강 10~11쪽)
# ---------------------------------------------------------------------------
def to_pixels(x, y):
    """수학 좌표(-10~10, y 위쪽) → Pygame 픽셀 좌표(y 아래쪽)
    충돌 계산은 반드시 수학 좌표에서 하고, 그릴 때만 이 함수를 쓴다."""
    return (WIDTH / 2 + WIDTH * x / 20, HEIGHT / 2 - HEIGHT * y / 20)


def draw_poly(screen, points, color, width=2):
    pixel_points = [to_pixels(x, y) for x, y in points]
    pygame.draw.lines(screen, color, True, pixel_points, width)


def draw_aabb(screen, box, color):
    left, top = to_pixels(box.min_pt[0], box.max_pt[1])
    right, bottom = to_pixels(box.max_pt[0], box.min_pt[1])
    pygame.draw.rect(screen, color, pygame.Rect(left, top, right - left, bottom - top), 1)


def draw_segment(screen, segment, color, width=1):
    pygame.draw.line(screen, color, to_pixels(*segment[0]), to_pixels(*segment[1]), width)


#추가됨
def draw_text_block(screen, font, lines, x, y, colors=None):
    """반투명 검은 배경 위에 여러 줄 글자 (소행성과 겹쳐도 읽히도록)"""
    if not lines:
        return
    surfaces = [font.render(line, True, (colors or {}).get(k, WHITE))
                for k, line in enumerate(lines)]
    w = max(s.get_width() for s in surfaces) + 12
    h = 20 * len(lines) + 6
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 170))
    screen.blit(panel, (x - 6, y - 3))
    for k, s in enumerate(surfaces):
        screen.blit(s, (x, y + 20 * k))


#추가됨
def draw_dashed_poly(screen, points, color, dash=6, gap=4):
    """Hull 외곽선을 점선으로 그린다 (Pygame에는 점선 함수가 없어서 직접 구현)"""
    pixel_points = [to_pixels(x, y) for x, y in points]
    n = len(pixel_points)
    for i in range(n):
        start = pygame.math.Vector2(pixel_points[i])
        end = pygame.math.Vector2(pixel_points[(i + 1) % n])
        edge_length = start.distance_to(end)
        if edge_length == 0:
            continue
        direction = (end - start) / edge_length
        pos = 0.0
        while pos < edge_length:
            seg_end = min(pos + dash, edge_length)
            pygame.draw.line(screen, color, start + direction * pos, start + direction * seg_end, 1)
            pos += dash + gap


# ---------------------------------------------------------------------------
# 게임 상태
# ---------------------------------------------------------------------------
class Game:
    def __init__(self, num_asteroids=NUM_ASTEROIDS, seed=SEED):
        self.seed = seed
        self.ship = Ship()
        self.asteroids = []
        self.show_boxes = True
        self.paused = False
        self.laser = None
        #추가됨
        self.mode = "AABB"
        #추가됨
        self.show_circles = False
        #추가됨
        self.debug = False
        #추가됨
        self.min_radius = RADIUS_PRESETS[0]
        #추가됨
        self.sat_runs = 0
        #추가됨
        self.stats = {}
        self.reset(num_asteroids)

        # 프레임마다 갱신되는 판정 결과
        self.world_points = []
        self.aabbs = []
        #추가됨
        self.aabb_pairs = []
        #추가됨
        self.sat_pairs = []
        #추가됨
        self.hull_points = []
        #추가됨
        self.hull_pairs = []
        #추가됨
        self.aabb_colliding = set()
        self.colliding_pairs = []
        self.colliding = set()

    def reset(self, num_asteroids):
        if self.seed is not None:
            random.seed(self.seed)
        self.asteroids = [self.spawn_asteroid() for _ in range(num_asteroids)]
        #추가됨
        self.reset_stats()

    #추가됨
    def reset_stats(self):
        """누적 통계 (단위: 프레임별 '쌍' 수를 모두 더한 값)"""
        self.stats = {"frames": 0, "pairs": 0, "sat_runs": 0,
                      "aabb": 0, "sat": 0, "hull": 0,
                      "aabb_extra": 0, "sat_extra": 0}

    def spawn_asteroid(self):
        """우주선(원점) 근처를 피해서 배치"""
        #변경됨
        ast = Asteroid(min_radius=self.min_radius)
        while True:
            ast.x, ast.y = random.uniform(-9, 9), random.uniform(-9, 9)
            if vectors.length((ast.x - self.ship.x, ast.y - self.ship.y)) > 3:
                return ast

    # -- 입력 ---------------------------------------------------------------
    def handle_keys(self, keys, milliseconds):
        dt = milliseconds / 1000.0
        if keys[pygame.K_LEFT]:
            self.ship.rotation_angle += ROTATION_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.ship.rotation_angle -= ROTATION_SPEED * dt

        # 04강 21~22쪽: 바라보는 방향으로 가속
        direction = 0
        if keys[pygame.K_UP]:
            direction = 1
        elif keys[pygame.K_DOWN]:
            direction = -1
        if direction:
            ax = direction * ACCELERATION * cos(self.ship.rotation_angle)
            ay = direction * ACCELERATION * sin(self.ship.rotation_angle)
            self.ship.vx += ax * dt
            self.ship.vy += ay * dt

        self.laser = self.ship.laser_segment() if keys[pygame.K_SPACE] else None

    # -- 갱신 ---------------------------------------------------------------
    def update(self, milliseconds):
        if not self.paused:
            self.ship.move(milliseconds)
            for ast in self.asteroids:
                ast.move(milliseconds)

        # 레이저에 맞은 소행성 제거
        if self.laser:
            self.asteroids = [a for a in self.asteroids if not laser_hits(a, self.laser)]

        self.detect_collisions()
        #추가됨
        if not self.paused:
            self.accumulate_stats()

    #추가됨
    def accumulate_stats(self):
        n = len(self.asteroids)
        hull_set = set(self.hull_pairs)
        s = self.stats
        s["frames"] += 1
        s["pairs"] += n * (n - 1) // 2
        s["sat_runs"] += self.sat_runs
        s["aabb"] += len(self.aabb_pairs)
        s["sat"] += len(self.sat_pairs)
        s["hull"] += len(self.hull_pairs)
        s["aabb_extra"] += len(set(self.aabb_pairs) - hull_set)
        s["sat_extra"] += len(set(self.sat_pairs) - hull_set)

    def detect_collisions(self):
        #변경됨
        """소행성끼리 충돌 판정
        비교를 위해 AABB와 SAT를 매 프레임 둘 다 계산하고,
        화면 색은 현재 모드의 결과를 따른다."""
        # 꼭짓점 변환과 AABB 계산은 소행성마다 프레임당 한 번만
        self.world_points = [a.transformed() for a in self.asteroids]
        self.aabbs = [compute_aabb(pts) for pts in self.world_points]

        #변경됨
        self.aabb_pairs = find_colliding_pairs_aabb(self.aabbs)
        #추가됨
        self.sat_pairs = find_colliding_pairs_sat(self.world_points)
        #추가됨
        # Hull은 생성 시 계산해 둔 것을 현재 회전·위치로 변환만 한다
        self.hull_points = [a.transformed(a.hull) for a in self.asteroids]
        #변경됨
        # 바운딩 원으로 먼저 거르고, 원이 겹친 쌍만 Hull에 SAT 실행
        centers = [(a.x, a.y) for a in self.asteroids]
        #추가됨
        radii = [a.bound_radius for a in self.asteroids]
        #변경됨
        self.hull_pairs, self.sat_runs = find_colliding_pairs_two_phase(
            centers, radii, self.hull_points)
        #추가됨
        self.aabb_colliding = {i for pair in self.aabb_pairs for i in pair}

        #변경됨
        self.colliding_pairs = {"AABB": self.aabb_pairs,
                                "SAT": self.sat_pairs,
                                "HULL+SAT": self.hull_pairs}[self.mode]
        self.colliding = {i for pair in self.colliding_pairs for i in pair}

    # -- 그리기 -------------------------------------------------------------
    def render(self, screen, font, fps=0.0):
        screen.fill(BLACK)

        for i, pts in enumerate(self.world_points):
            color = RED if i in self.colliding else GREEN
            draw_poly(screen, pts, color)
            #추가됨
            # Hull 모드: Hull 외곽선(점선)과 오목한 꼭짓점(주황 점) 표시
            if self.mode == "HULL+SAT":
                draw_dashed_poly(screen, self.hull_points[i], color)
                ast = self.asteroids[i]
                for p in ast.transformed(ast.concave_points):
                    pygame.draw.circle(screen, ORANGE, to_pixels(*p), 4)
            if self.show_boxes:
                #변경됨
                # 상자 색은 항상 AABB 결과 → SAT 모드에서 "상자는 빨강, 소행성은 초록"이면 AABB 오판정
                draw_aabb(screen, self.aabbs[i], RED if i in self.aabb_colliding else GRAY)
            #추가됨
            if self.show_circles:
                ast = self.asteroids[i]
                pygame.draw.circle(screen, DIM, to_pixels(ast.x, ast.y),
                                   ast.bound_radius * WIDTH / 20, 1)

        draw_poly(screen, self.ship.transformed(), WHITE)
        if self.laser:
            draw_segment(screen, self.laser, YELLOW, 2)

        #추가됨
        debug_text = self.draw_debug(screen) if self.debug else None

        n = len(self.asteroids)
        #변경됨
        # Hull + SAT를 기준으로, 다른 방식이 '충돌'이라 했지만 Hull + SAT는 아니라고 한 쌍
        hull_set = set(self.hull_pairs)
        #변경됨
        aabb_extra = len(set(self.aabb_pairs) - hull_set)
        #추가됨
        sat_extra = len(set(self.sat_pairs) - hull_set)
        #추가됨
        concave_count = sum(a.is_concave for a in self.asteroids)
        #추가됨
        total_pairs = n * (n - 1) // 2
        hud = [
            #변경됨
            f"Mode: {self.mode}   (1: AABB  2: SAT  3: HULL+SAT)",
            #변경됨
            f"Asteroids: {n} (concave: {concave_count}, min r = {self.min_radius})   Pairs: {total_pairs}",
            #변경됨
            f"Colliding pairs  AABB: {len(self.aabb_pairs)}  SAT: {len(self.sat_pairs)}"
            f"  HULL+SAT: {len(self.hull_pairs)}",
            #변경됨
            f"Extra vs HULL+SAT  AABB: {aabb_extra}  SAT(raw): {sat_extra}",
            #추가됨
            f"SAT runs (after circle filter): {self.sat_runs} / {total_pairs}",
            f"FPS: {fps:.0f}" + ("   [PAUSED]" if self.paused else ""),
            #변경됨
            "B: boxes  C: circles  D: debug  K: concavity  S: reset stats",
            #추가됨
            "P: pause  R: reset  +/-: count",
        ]
        #변경됨
        draw_text_block(screen, font, hud, 10, 10)

        #추가됨
        # 화면 아래: 누적 통계 (최종 보고서에 쓸 수치)
        s = self.stats
        def pct(a, b):
            return f"{100 * a / b:.1f}%" if b else "-"
        bottom = [
            f"[Cumulative over {s['frames']} frames]",
            f"AABB positives: {s['aabb']}  -> false vs HULL+SAT: {s['aabb_extra']} ({pct(s['aabb_extra'], s['aabb'])})",
            f"Raw SAT positives: {s['sat']}  -> false vs HULL+SAT: {s['sat_extra']} ({pct(s['sat_extra'], s['sat'])})",
            f"SAT skipped by circle early out: {pct(s['pairs'] - s['sat_runs'], s['pairs'])}"
            f"  ({s['sat_runs']} runs / {s['pairs']} pair checks)",
        ]
        if debug_text:
            bottom.insert(0, debug_text)
        draw_text_block(screen, font, bottom, 10, HEIGHT - 20 * len(bottom) - 6,
                        {0: YELLOW} if debug_text else None)

    #추가됨
    def draw_debug(self, screen):
        """가장 가까운 두 소행성에 대해 SAT가 판단한 근거를 그린다
        - 두 소행성의 바운딩 원
        - 분리축(흰 선)과 그 위의 두 투영 구간(주황/하늘색), 그리고 그 사이 틈
        반환: 화면 아래에 표시할 설명 문장"""
        n = len(self.asteroids)
        if n < 2:
            return None
        centers = [(a.x, a.y) for a in self.asteroids]
        #변경됨
        # 분리축을 보여줄 수 있도록 '충돌하지 않은 쌍' 중 가장 가까운 쌍을 고른다
        #추가됨
        hull_set = set(self.hull_pairs)
        #추가됨
        candidates = [p for p in combinations(range(n), 2) if p not in hull_set]
        #변경됨
        i, j = min(candidates or combinations(range(n), 2),
                   key=lambda p: vectors.distance(centers[p[0]], centers[p[1]]))

        for k in (i, j):
            ast = self.asteroids[k]
            pygame.draw.circle(screen, YELLOW, to_pixels(ast.x, ast.y),
                               ast.bound_radius * WIDTH / 20, 1)

        hull_i, hull_j = self.hull_points[i], self.hull_points[j]
        axis = find_separating_axis(hull_i, hull_j)
        if axis is None:
            return f"Debug #{i}-#{j}: no separating axis -> COLLIDING"

        # 축은 두 소행성 옆으로 비켜서 그린다 (축 방향 투영값은 옆으로 옮겨도 변하지 않음)
        u = vectors.normalize(axis)
        mid = vectors.scale(0.5, vectors.add(centers[i], centers[j]))
        side = max(self.asteroids[i].bound_radius, self.asteroids[j].bound_radius) + 0.6
        # 화면 가장자리로 빠지지 않도록, 두 방향 중 화면 중심에 가까운 쪽으로 비켜 그림
        base = min((vectors.add(mid, vectors.scale(sign * side, vectors.perpendicular(u)))
                    for sign in (1, -1)), key=vectors.length)
        draw_segment(screen, (vectors.add(base, vectors.scale(-4, u)),
                              vectors.add(base, vectors.scale(4, u))), WHITE, 1)

        for pts, color in ((hull_i, ORANGE), (hull_j, CYAN)):
            # 중점 기준으로 투영한 구간 [lo, hi]를 축 위에 그림
            rel = [vectors.subtract(p, mid) for p in pts]
            lo, hi = project(rel, u)
            start = vectors.add(base, vectors.scale(lo, u))
            end = vectors.add(base, vectors.scale(hi, u))
            draw_segment(screen, (start, end), color, 5)
            # 가장 바깥 꼭짓점에서 축으로 내린 투영선 (축과 수직)
            for p, value in ((min(pts, key=lambda q: vectors.dot(vectors.subtract(q, mid), u)), lo),
                             (max(pts, key=lambda q: vectors.dot(vectors.subtract(q, mid), u)), hi)):
                draw_segment(screen, (p, vectors.add(base, vectors.scale(value, u))), color, 1)

        return f"Debug #{i}-#{j}: separating axis found -> NOT colliding"


# ---------------------------------------------------------------------------
# 메인 루프
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    #변경됨
    pygame.display.set_caption("Asteroids Collision Detection - AABB vs SAT vs Hull + SAT")
    font = pygame.font.SysFont("consolas", 16)
    clock = pygame.time.Clock()

    game = Game()
    done = False
    while not done:
        clock.tick(FPS)
        milliseconds = clock.get_time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done = True
                #추가됨
                elif event.key in MODES:
                    game.mode = MODES[event.key]
                elif event.key == pygame.K_b:
                    game.show_boxes = not game.show_boxes
                #추가됨
                elif event.key == pygame.K_c:
                    game.show_circles = not game.show_circles
                #추가됨
                elif event.key == pygame.K_d:
                    game.debug = not game.debug
                #추가됨
                elif event.key == pygame.K_k:
                    idx = RADIUS_PRESETS.index(game.min_radius)
                    game.min_radius = RADIUS_PRESETS[(idx + 1) % len(RADIUS_PRESETS)]
                    game.reset(NUM_ASTEROIDS)
                #추가됨
                elif event.key == pygame.K_s:
                    game.reset_stats()
                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                elif event.key == pygame.K_r:
                    game.seed = random.randrange(10**6)
                    game.reset(NUM_ASTEROIDS)
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    game.asteroids.append(game.spawn_asteroid())
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and game.asteroids:
                    game.asteroids.pop()

        game.handle_keys(pygame.key.get_pressed(), milliseconds)
        game.update(milliseconds)
        game.render(screen, font, clock.get_fps())
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

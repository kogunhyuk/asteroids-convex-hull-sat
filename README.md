# Beyond AABB: Convex Hull SAT Collision for Asteroids

SWCON211 게임프로그래밍입문 Term Project — Pygame으로 구현한 물리 엔진 기능

수업에서 만든 Asteroids 게임에 **소행성끼리의 충돌 검출**을 추가합니다.
단순한 AABB 판정에서 출발해, 회전하고 오목할 수 있는 소행성도 정확하게 판정하는
**Convex Hull + SAT(Separating Axis Theorem)** 방식으로 발전시켰습니다.

## 기능

| 구분 | 내용 |
|---|---|
| 기본 | Asteroids 구조(`PolygonModel`, 회전·이동), 레이저 선분 교차, **AABB** 충돌 판정 |
| 심화 ① | 임의의 볼록 다각형 **SAT** (변 법선을 축으로 내적 투영 후 구간 비교) |
| 심화 ② | **Convex Hull** 직접 구현 (Monotone Chain, 외적으로 꺾임 방향 판정), 생성 시 1회만 계산 |
| 심화 ③ | **바운딩 원 early out** → 원이 겹친 쌍만 SAT 실행 (2단계 판정) |
| 데모 | 판정 방식 전환, 누적 정확도 통계, 분리축·투영 구간 디버그 시각화 |

## 실행

```bash
pip install -r requirements.txt
python main.py
```

## 조작

| 키 | 기능 |
|---|---|
| `1` / `2` / `3` | 판정 방식: AABB / 원래 다각형 SAT / Hull + SAT |
| `B` / `C` / `D` | AABB 상자 / 바운딩 원 / 디버그(분리축과 투영 구간) 표시 |
| `K` | 오목 정도 전환 (강의 기본 0.5~1.0 ↔ 깊게 패임 0.3~1.0) |
| `S` | 누적 통계 초기화 |
| `←` `→` / `↑` `↓` / `Space` | 우주선 회전 / 가속 / 레이저 |
| `P` / `R` / `+` `-` | 일시정지 / 재배치 / 소행성 수 조절 |

화면 색: 초록 = 충돌 아님, 빨강 = 충돌. SAT 모드에서 **상자는 빨강인데 소행성은 초록**이면 AABB 오판정입니다.

## 파일 구조

```
vectors.py    2D 벡터 연산 (내적, 회전, 90° 회전 법선 등)
models.py     PolygonModel / Ship / Asteroid (Hull·바운딩 원을 생성 시 계산)
collision.py  AABB, SAT, Convex Hull, 바운딩 원 2단계 판정, 레이저 선분 교차
main.py       게임 루프, 그리기, 모드 전환, 통계, 디버그 화면
```

## 결과 (소행성 16개, 4000프레임)

| 항목 | 강의 기본값 (0.5~1.0) | 깊게 패임 (0.3~1.0) |
|---|---|---|
| 오목한 소행성 | 4 / 16 | 10 / 16 |
| AABB 오판정 비율 | 25.1% | 24.1% |
| 원래 다각형 SAT 오판정 비율 | 0.2% | 0.9% |
| 바운딩 원으로 생략한 SAT | 97.5% | 97.6% |

## 실행 파일 만들기 (Windows)

`build_exe.bat`을 더블클릭하면 `dist/AsteroidsCollision.exe`가 만들어집니다.

## 참고

- SWCON211 LectureNote 04 (Physics), 06 (Collision Detection), Mathematics 06~08
- Jason Gregory, *Game Engine Architecture*
- Christer Ericson, *Real-Time Collision Detection*
- Paul Orland, *Math for Programmers*

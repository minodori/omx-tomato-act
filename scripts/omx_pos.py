#!/home/minodori/Projects/lerobot_lab/lerobot/.venv/bin/python
"""OMX follower 관절값을 읽기만 한다 (아무것도 쓰지 않는다). 종료는 Ctrl+C.

실행: ~/Projects/lerobot_lab/scripts/omx_pos.py
  - 모터에 쓰기(토크, 게인, 동작 모드)를 하지 않는다. 프로그램이 끝난 뒤 토크는 꺼진 상태라
    팔을 손으로 홈 자세에 놓고 값을 볼 수 있다. 다른 lerobot 프로그램이 포트를 잡고 있으면 실행하지 않는다.
  - 값은 데이터셋의 observation.state 와 같은 단위(정규화 -100~100)다.
  - 기준: omx_tomato 50개 에피소드의 첫 프레임 state (평균, 표준편차). 2026-11-10 계산.
"""
import time

from lerobot.robots.omx_follower import OmxFollower, OmxFollowerConfig

REF = {  # 시연 시작 자세 (mean, std)
    "shoulder_pan": (2.43, 1.24),
    "shoulder_lift": (-63.65, 0.98),
    "elbow_flex": (55.72, 0.29),
    "wrist_flex": (45.04, 1.68),
    "wrist_roll": (1.55, 2.11),
    "gripper": (50.56, 3.73),
}

cfg = OmxFollowerConfig(port="/dev/omx_follower", id="omx_follower_arm")
robot = OmxFollower(cfg)
robot.bus.connect()
print("읽기 전용. 종료: Ctrl+C")
print("기준(시연 시작):", " ".join(f"{n[:6]}={m:.1f}+-{s:.1f}" for n, (m, s) in REF.items()))
print("순서: pan lift elbow wflex wroll grip. 값(기준과의 차이, 표준편차 단위)")

try:
    while True:
        p = robot.bus.sync_read("Present_Position")
        # 한 줄이 터미널 폭(80자)을 넘으면 \r 로 덮어쓰기가 깨지므로 짧게 쓴다
        vals = " ".join(f"{v:6.1f}({(v - REF[k][0]) / REF[k][1]:+.1f})" for k, v in p.items())
        print("\r" + vals + "   ", end="", flush=True)
        time.sleep(0.3)
except KeyboardInterrupt:
    print()
finally:
    robot.bus.disconnect(False)  # False: 토크를 건드리지 않고 연결만 끊는다

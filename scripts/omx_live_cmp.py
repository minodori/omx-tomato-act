#!/home/minodori/Projects/lerobot_lab/lerobot/.venv/bin/python
"""읽기 전용 진단. 팔을 홈 자세에 두고 실행한다. 로봇에 아무 명령도 보내지 않는다.

라이브 입력(카메라 2장 + 현재 관절값)을 학습된 ACT 모델에 넣어서 첫 100스텝 예측을 만들고,
녹화 데이터(에피소드 0, 5의 첫 프레임)를 넣었을 때의 예측과 네 가지 조합으로 비교한다.
  1 녹화 영상 + 녹화 관절값 (기준)   2 라이브 + 라이브   3 라이브 영상 + 녹화 관절값   4 녹화 영상 + 라이브 관절값
2에서만 크게 달라지면 입력 차이가 원인이고, 3이면 영상, 4이면 홈 자세가 원인이다.
출력은 [0/45/99] = 예측 100스텝 중 0, 45, 99번째 스텝의 pan, lift, elbow 값.

실행: ~/Projects/lerobot_lab/scripts/omx_live_cmp.py   (다른 lerobot 프로그램과 동시에 실행하지 않는다)
사진은 ~/Projects/lerobot_lab/outputs/live_cmp/ 에 저장된다.
"""
import os
import time

import cv2
import numpy as np
import torch

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies import make_pre_post_processors
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.utils import prepare_observation_for_inference
from lerobot.robots.omx_follower import OmxFollower, OmxFollowerConfig

BASE = "/home/minodori/Projects/lerobot_lab"
OUT = f"{BASE}/outputs/live_cmp"
CKPT = f"{BASE}/outputs/omx_tomato_act/checkpoints/030000/pretrained_model"
TOP = "/dev/v4l/by-path/pci-0000:65:00.3-usb-0:1:1.0-video-index0"
WRIST = "/dev/v4l/by-path/pci-0000:65:00.3-usb-0:2:1.0-video-index0"
dev = torch.device("cuda")
names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
os.makedirs(OUT, exist_ok=True)

# 현재 관절값 (읽기만, 토크를 건드리지 않는다)
robot = OmxFollower(OmxFollowerConfig(port="/dev/omx_follower", id="omx_follower_arm"))
robot.bus.connect()
rows = []
for _ in range(10):
    p = robot.bus.sync_read("Present_Position")
    rows.append([p[n] for n in names])
    time.sleep(0.05)
robot.bus.disconnect(False)
live_state = np.mean(rows, axis=0).astype(np.float32)
print("live state :", np.round(live_state, 2), " (10회 읽기의 표준편차:", np.round(np.std(rows, axis=0), 2), ")")


def grab(path, tag):
    c = cv2.VideoCapture(path, cv2.CAP_V4L2)
    c.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    c.set(cv2.CAP_PROP_FPS, 30)
    time.sleep(1.5)
    ok, f = False, None
    for _ in range(25):
        ok, f = c.read()
    c.release()
    assert ok and f is not None, f"카메라 {tag} 읽기 실패"
    cv2.imwrite(f"{OUT}/live_{tag}.png", f)
    return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)  # LeRobot 은 RGB 를 쓴다


live_top = grab(TOP, "top")
live_wrist = grab(WRIST, "wrist")


def rec(ep):
    ds = LeRobotDataset("minodori/omx_tomato", root=f"{BASE}/data/omx_tomato", episodes=[ep])
    it = ds[0]
    img = lambda k: (it[k].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
    return img("observation.images.top"), img("observation.images.wrist"), it["observation.state"].numpy().astype(np.float32)


policy = ACTPolicy.from_pretrained(CKPT).to(dev).eval()
pre, post = make_pre_post_processors(
    policy_cfg=policy.config,
    pretrained_path=CKPT,
    preprocessor_overrides={"device_processor": {"device": "cuda"}},
)


def predict(top, wrist, state):
    obs = {"observation.state": state, "observation.images.top": top, "observation.images.wrist": wrist}
    with torch.inference_mode():
        b = prepare_observation_for_inference(obs, dev, None, None)
        b = pre(b)
        c = post(policy.predict_action_chunk(b))
    return c.squeeze(0).cpu().numpy()


def show(label, ch):
    print(f"{label:26s}", " ".join(f"{n[:5]}[0/45/99]={ch[0, i]:6.1f}/{ch[45, i]:6.1f}/{ch[99, i]:6.1f}" for i, n in enumerate(names[:3])))


for ep in (0, 5):
    rt, rw, rs = rec(ep)
    print(f"\n--- 녹화 에피소드 {ep} 시작 관절값:", np.round(rs, 2))
    show("1 rec img + rec state", predict(rt, rw, rs))
    show("2 LIVE img + LIVE state", predict(live_top, live_wrist, live_state))
    show("3 LIVE img + rec state", predict(live_top, live_wrist, rs))
    show("4 rec img + LIVE state", predict(rt, rw, live_state))
print(f"\n사진 저장: {OUT}/live_top.png, live_wrist.png")

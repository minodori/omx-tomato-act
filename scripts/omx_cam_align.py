#!/home/minodori/Projects/lerobot_lab/lerobot/.venv/bin/python
"""top 카메라 위치 맞추기 도우미. 로봇은 건드리지 않고 top 카메라만 연다.

녹화 데이터의 기준 화면(기본: omx_tomato 에피소드 5의 첫 프레임)을 라이브 영상 위에 겹쳐서
창에 보여 준다. 스탠드를 움직이면서 종이, 통, 로봇 받침이 겹치도록 맞춘다.

실행:
  ~/Projects/lerobot_lab/scripts/omx_cam_align.py          기준 화면 = 에피소드 5
  ~/Projects/lerobot_lab/scripts/omx_cam_align.py 12       기준 화면 = 에피소드 12 (새로 만든다)
  ~/Projects/lerobot_lab/scripts/omx_cam_align.py --test   창과 카메라 없이 계산만 시험한다

창에서 키: m 모드 바꾸기 (반투명 / 윤곽선 / 라이브만 / 기준만), s 사진 저장, q 또는 Esc 종료.
  - 반투명: 두 화면을 반반 섞는다. 겹쳐야 할 것이 이중으로 보이면 어긋난 것이다.
  - 윤곽선: 기준 화면의 윤곽(빨강)을 라이브 위에 얹는다. 종이 모서리, 통, 받침에 맞춘다.
  - 숫자: 기준 대비 화면이 얼마나 이동했는지(px). 0에 가까울수록 맞다. 이동 방향만 보는
    값이라 회전이나 확대는 못 본다. 토마토와 팔 자세가 달라도 값이 조금 흔들린다.
다른 lerobot 프로그램(rollout, record, teleoperate)이 카메라를 쓰는 중이면 실행하지 않는다.
기준 화면 파일: ~/Projects/lerobot_lab/outputs/cam_ref/ref_top_ep<번호>.png
"""
import base64
import os
import subprocess
import sys
import tkinter as tk

import cv2
import numpy as np

BASE = "/home/minodori/Projects/lerobot_lab"
REFDIR = f"{BASE}/outputs/cam_ref"
TOP = "/dev/v4l/by-path/pci-0000:65:00.3-usb-0:1:1.0-video-index0"
SCALE = 1.25
MODES = ["반투명", "윤곽선", "라이브만", "기준만"]


def make_ref(ep):
    """녹화 데이터에서 에피소드 ep 의 첫 top 프레임을 PNG 로 저장한다."""
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    os.makedirs(REFDIR, exist_ok=True)
    ds = LeRobotDataset("minodori/omx_tomato", root=f"{BASE}/data/omx_tomato", episodes=[ep])
    img = (ds[0]["observation.images.top"].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8)
    path = f"{REFDIR}/ref_top_ep{ep}.png"
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print("기준 화면 저장:", path)
    return path


def load_ref(ep):
    path = f"{REFDIR}/ref_top_ep{ep}.png"
    if not os.path.exists(path):
        make_ref(ep)
    ref = cv2.imread(path)
    assert ref is not None, f"기준 화면을 못 읽음: {path}"
    return ref


def prepare(ref):
    gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    edges = cv2.dilate(cv2.Canny(gray, 60, 150), np.ones((2, 2), np.uint8))
    win = cv2.createHanningWindow((ref.shape[1], ref.shape[0]), cv2.CV_32F)
    return gray.astype(np.float32), edges, win


def shift_between(ref_gray, live_bgr, win):
    """기준 대비 라이브 화면 내용의 이동 (dx 오른쪽, dy 아래, px)과 신뢰도."""
    g = cv2.cvtColor(live_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    (dx, dy), resp = cv2.phaseCorrelate(ref_gray, g, win)
    return dx, dy, resp


def render(mode, ref, edges, live):
    if mode == 0:
        return cv2.addWeighted(ref, 0.5, live, 0.5, 0)
    if mode == 1:
        out = live.copy()
        out[edges > 0] = (0, 0, 255)
        return out
    if mode == 2:
        return live
    return ref


def run_test():
    ref = load_ref(5)
    ref_gray, edges, win = prepare(ref)
    # 부호 확인: 기준 화면을 오른쪽 10px, 아래 5px 옮긴 가짜 라이브를 넣어 본다
    m = np.float32([[1, 0, 10], [0, 1, 5]])
    fake = cv2.warpAffine(ref, m, (ref.shape[1], ref.shape[0]), borderMode=cv2.BORDER_REFLECT)
    dx, dy, resp = shift_between(ref_gray, fake, win)
    print(f"가짜 이동(오른쪽 10, 아래 5) -> 계산값 dx={dx:+.2f} dy={dy:+.2f} 신뢰도={resp:.2f}")
    live_path = f"{BASE}/outputs/live_cmp/live_top.png"
    live = cv2.imread(live_path)
    if live is not None:
        dx, dy, resp = shift_between(ref_gray, live, win)
        print(f"저장된 라이브 사진({live_path}) 대비: dx={dx:+.2f} dy={dy:+.2f} 신뢰도={resp:.2f}")
        for i, name in enumerate(["blend", "edges"]):
            cv2.imwrite(f"{REFDIR}/test_{name}.png", render(i, ref, edges, live))
        print("시험 이미지 저장:", f"{REFDIR}/test_blend.png, test_edges.png")


def run_gui(ep):
    if subprocess.run(["pgrep", "-f", "lerobot-(rollout|record|teleoperate|replay)"], capture_output=True).returncode == 0:
        print("다른 lerobot 프로그램이 돌고 있다. 카메라를 같이 쓸 수 없어서 끝낸 뒤에 실행한다.")
        sys.exit(1)
    ref = load_ref(ep)
    ref_gray, edges, win = prepare(ref)
    h, w = ref.shape[:2]

    cap = cv2.VideoCapture(TOP, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print("top 카메라를 못 열었다:", TOP)
        sys.exit(1)

    root = tk.Tk()
    root.title(f"top 카메라 맞추기 (기준: 에피소드 {ep})")
    img_label = tk.Label(root)
    img_label.pack()
    txt_label = tk.Label(root, font=("TkDefaultFont", 12), justify="left", anchor="w")
    txt_label.pack(fill="x", padx=8, pady=4)

    state = {"mode": 0, "dx": 0.0, "dy": 0.0, "resp": 0.0, "first": True, "live": None}

    def step():
        ok, live = cap.read()
        if ok and live is not None:
            if live.shape[:2] != (h, w):
                live = cv2.resize(live, (w, h))
            state["live"] = live
            dx, dy, resp = shift_between(ref_gray, live, win)
            if state["first"]:
                state["dx"], state["dy"], state["first"] = dx, dy, False
            else:  # 숫자가 덜 흔들리게 지수 이동 평균
                state["dx"] = 0.7 * state["dx"] + 0.3 * dx
                state["dy"] = 0.7 * state["dy"] + 0.3 * dy
            state["resp"] = resp
            out = render(state["mode"], ref, edges, live)
            out = cv2.resize(out, (int(w * SCALE), int(h * SCALE)))
            png = cv2.imencode(".png", out)[1].tobytes()
            photo = tk.PhotoImage(data=base64.b64encode(png).decode())
            img_label.configure(image=photo)
            img_label.image = photo  # 참조를 잡아 둬야 사라지지 않는다
            rx = "오른쪽" if state["dx"] >= 0 else "왼쪽"
            ry = "아래" if state["dy"] >= 0 else "위"
            txt_label.configure(
                text=f"모드: {MODES[state['mode']]}   (m 모드, s 사진 저장, q 종료)\n"
                f"기준 대비 화면 이동: {rx} {abs(state['dx']):.1f}px, {ry} {abs(state['dy']):.1f}px"
                f"  (신뢰도 {state['resp']:.2f})\n"
                f"0에 가까울수록 맞다. 카메라는 화면이 이동한 반대 방향으로 옮긴다."
            )
        root.after(30, step)

    def on_key(event):
        k = event.keysym.lower()
        if k == "m":
            state["mode"] = (state["mode"] + 1) % len(MODES)
        elif k == "s" and state["live"] is not None:
            os.makedirs(REFDIR, exist_ok=True)
            p = f"{REFDIR}/live_top_snapshot.png"
            cv2.imwrite(p, state["live"])
            print("저장:", p)
        elif k in ("q", "escape"):
            root.destroy()

    root.bind("<Key>", on_key)
    root.focus_force()
    root.after(30, step)
    try:
        root.mainloop()
    finally:
        cap.release()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--test":
        run_test()
    else:
        run_gui(int(args[0]) if args else 5)

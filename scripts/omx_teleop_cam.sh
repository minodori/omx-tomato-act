#!/bin/bash
# OMX 텔레오퍼레이션 (카메라 2대 포함). 가이드 4단계.
# 실행: bash ~/Projects/lerobot_lab/scripts/omx_teleop_cam.sh
# 끝내기: Ctrl+C (팔로워 토크가 꺼져 팔이 처지니 한 손으로 받친다)
source ~/Projects/lerobot_lab/lerobot/.venv/bin/activate

# 카메라는 /dev/video 번호가 부팅마다 바뀌어서 USB 포트 위치(by-path)로 지정한다 (omx_record.sh, omx_rollout.sh 와 같다).
# 포트 1 = top, 포트 2 = wrist(eye on hand) (2026-11-11). 카메라를 다른 포트에 꽂으면 바뀐다.
# 그때는 ls -l /dev/v4l/by-path 와 사진으로 다시 확인한다.
TOP=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:1:1.0-video-index0
WRIST=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:2:1.0-video-index0
# fourcc MJPG: 압축 영상으로 USB 대역폭을 줄인다.
CAMS="{ top: {type: opencv, index_or_path: '$TOP', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5}, wrist: {type: opencv, index_or_path: '$WRIST', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5} }"

lerobot-teleoperate \
  --robot.type=omx_follower \
  --robot.port=/dev/omx_follower \
  --robot.id=omx_follower_arm \
  --robot.max_relative_target=10.0 \
  --robot.cameras="$CAMS" \
  --teleop.type=omx_leader \
  --teleop.port=/dev/omx_leader \
  --teleop.id=omx_leader_arm \
  --display_data=true

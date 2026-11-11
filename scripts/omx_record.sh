#!/bin/bash
# OMX 본 녹화 (토마토를 통에). 처음 녹화와 이어서 녹화를 한 스크립트로 한다.
# 아령 데이터는 DATA=omx_dumbbell TASK="Pick the yellow dumbbell and place it in the bin" 을 앞에 붙인다.
#
# 사용:
#   bash ~/Projects/lerobot_lab/scripts/omx_record.sh 10          처음 녹화 (폴더를 새로 만든다)
#   bash ~/Projects/lerobot_lab/scripts/omx_record.sh 10 resume   이어서 10개 더
#
# 앞의 숫자는 "이번에 더 녹화할 개수"다. 전체 개수나 시작 번호가 아니다.
#   (lerobot_record.py 470~471행: recorded_episodes를 0부터 세어 num_episodes까지)
#   위치 한 곳당 10개씩이면 처음과 이어서 모두 10을 쓴다. 에피소드 번호는 이어서 늘어난다.
#   top 카메라 기준: 1 중앙, 3 7시, 4 11시, 5 1시, 6 5시 (2번은 뺐다). 이 순서로 녹화한다.
#   0~9 위치1, 10~19 위치3, 20~29 위치4, 30~39 위치5, 40~49 위치6.
#
# 멈추는 법:
#   - 좋은 에피소드를 끝내고 리셋 구간에 들어갔을 때 ESC: 그 에피소드가 저장되고 종료.
#   - 녹화 중 ESC: 그 순간까지의 미완성 에피소드가 저장된다. 피한다.
#   - Ctrl+C: 이미 저장된 것은 남고 진행 중(리셋 포함) 에피소드는 사라진다.
#   - 오른쪽 화살표: 지금 구간을 일찍 끝냄. 왼쪽 화살표: 이번 에피소드를 버리고 다시 녹화.
# 종료하면 팔로워 토크가 꺼져 팔이 처진다. 리더를 홈 자세에 두고 팔로워 손목을 받친다.
#
# 이어서 녹화할 때 카메라 위치, fps, 로봇 설정은 처음과 같아야 한다. 과업 문장도 바꾸지 않는다.

source ~/Projects/lerobot_lab/lerobot/.venv/bin/activate

# ---- 설정 (여기만 고친다) ----
DATA=${DATA:-omx_tomato}
TASK=${TASK:-"Pick the tomato and place it in the bin"}
EPISODE_TIME_S=30
RESET_TIME_S=5
# 카메라는 /dev/video 번호가 부팅마다 바뀌어서 USB 포트 위치(by-path)로 지정한다.
#   top   = USB 포트 65:00.3 (2026-11-09 확인)
#   wrist = USB 포트 65:00.4 (11/9 녹화 때). 11/10 부터 65:00.3 의 포트 2 (다른 포트에 꽂음, 사진으로 확인)
TOP=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:1:1.0-video-index0
WRIST=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:2:1.0-video-index0
# ------------------------------

ROOT=/home/minodori/Projects/lerobot_lab/data/$DATA

N=$1
MODE=$2
if ! [[ "$N" =~ ^[0-9]+$ ]] || [ "$N" -lt 1 ]; then
  echo "사용: bash omx_record.sh <이번에 녹화할 개수> [resume]"
  echo "  예) 처음 10개: bash omx_record.sh 10"
  echo "  예) 이어서 10개: bash omx_record.sh 10 resume"
  exit 1
fi

RESUME_OPT=""
if [ "$MODE" = "resume" ]; then
  if [ ! -d "$ROOT" ]; then
    echo "이어서 녹화할 폴더가 없다: $ROOT"
    echo "처음이면 resume을 빼고 실행한다."
    exit 1
  fi
  RESUME_OPT="--resume=true"
  echo "이어서 녹화: $ROOT (이번에 $N개 더)"
elif [ -z "$MODE" ]; then
  if [ -e "$ROOT" ]; then
    echo "폴더가 이미 있다: $ROOT"
    echo "이어서 녹화하려면 마지막에 resume을 붙인다. (지우고 새로 하려면 폴더를 직접 지운다)"
    exit 1
  fi
  echo "처음 녹화: $ROOT ($N개)"
else
  echo "두 번째 인자는 resume 만 쓸 수 있다: $MODE"
  exit 1
fi

# top 카메라에 물체, 통, 그리퍼 작업 영역이 모두 보여야 한다. 녹화 중에 카메라를 건드리지 않는다.
CAMS="{ top: {type: opencv, index_or_path: '$TOP', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5}, wrist: {type: opencv, index_or_path: '$WRIST', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5} }"

lerobot-record \
  --robot.type=omx_follower --robot.port=/dev/omx_follower --robot.id=omx_follower_arm \
  --robot.cameras="$CAMS" \
  --teleop.type=omx_leader --teleop.port=/dev/omx_leader --teleop.id=omx_leader_arm \
  --dataset.repo_id=minodori/$DATA --dataset.root=$ROOT \
  --dataset.single_task="$TASK" \
  --dataset.num_episodes=$N --dataset.episode_time_s=$EPISODE_TIME_S --dataset.reset_time_s=$RESET_TIME_S \
  --dataset.push_to_hub=false --display_data=true \
  $RESUME_OPT

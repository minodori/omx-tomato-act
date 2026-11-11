#!/bin/bash
# 녹화한 에피소드의 동작을 팔로워에 그대로 재생한다 (진단용).
# 모델 없이 데이터의 action 만 보낸다. 같은 위치에서 재생이 되는데 모델이 틀리면 모델 문제,
# 재생도 틀리면 하드웨어(관절 미끄러짐, 캘리브레이션) 문제다.
#
# 사용:
#   bash ~/Projects/lerobot_lab/scripts/omx_replay.sh 0     에피소드 0 (위치 1, 중앙)
#   DATA=omx_dumbbell bash ~/Projects/lerobot_lab/scripts/omx_replay.sh 0   아령 데이터
# 에피소드 번호 (토마토): 0~9 위치1, 10~19 위치3, 20~29 위치4, 30~39 위치5, 40~49 위치6.
#
# 준비: 팔로워를 홈 자세(녹화 시작 자세)에 두고, 토마토를 그 에피소드의 위치에 놓는다.
#       한 손은 팔로워 손목 아래, 다른 손은 Ctrl+C (터미널 포커스 유지).
#       종료하면 토크가 꺼져 팔이 처진다. 리더와 카메라는 쓰지 않는다.
#
# --robot.max_relative_target  한 스텝에 목표가 현재값에서 이 이상 못 멀어지게 자른다 (안전용)
# --play_sounds=false          음성 안내를 끈다
source ~/Projects/lerobot_lab/lerobot/.venv/bin/activate

# ---- 설정 (여기만 고친다) ----
DATA=${DATA:-omx_tomato}
MAX_REL=10.0
# ------------------------------

EP=$1
if ! [[ "$EP" =~ ^[0-9]+$ ]]; then
  echo "사용: bash omx_replay.sh <에피소드 번호>"
  exit 1
fi

ROOT=/home/minodori/Projects/lerobot_lab/data/$DATA
if [ ! -d "$ROOT" ]; then
  echo "데이터셋이 없다: $ROOT"
  exit 1
fi

# 다른 프로그램이 모터 포트를 잡고 있으면 실행하지 않는다.
if pgrep -f 'lerobot-(rollout|record|teleoperate|replay)' > /dev/null; then
  echo "다른 lerobot 프로그램이 돌고 있다. 끝낸 뒤에 실행한다."
  exit 1
fi

echo "재생: $DATA 에피소드 $EP"

lerobot-replay \
  --robot.type=omx_follower \
  --robot.port=/dev/omx_follower \
  --robot.id=omx_follower_arm \
  --robot.max_relative_target=$MAX_REL \
  --dataset.repo_id=minodori/$DATA \
  --dataset.root=$ROOT \
  --dataset.episode=$EP \
  --play_sounds=false

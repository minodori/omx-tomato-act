#!/bin/bash
# OMX 학습 모델(기본 omx_tomato_act)을 실물 팔로워에서 돌린다. 가이드 9단계.
# 아령 모델은 NAME=omx_dumbbell_act 를 앞에 붙인다. 예) NAME=omx_dumbbell_act bash omx_rollout.sh
# 실행:
#   bash ~/Projects/lerobot_lab/scripts/omx_rollout.sh          가장 마지막 체크포인트
#   bash ~/Projects/lerobot_lab/scripts/omx_rollout.sh 10000    10000 스텝 체크포인트
#
# 시험 방법:
#   - 학습한 위치의 표시 위에 물체를 놓고 위치마다 5번씩 한다.
#   - 이어서 각 위치에서 몇 cm 옮기거나 방향을 바꿔서 1~2번씩 한다.
#   - 학습 안 한 위치도 1~2번 해 본다 (안 될 가능성이 크다).
#   - 통, 카메라, 조명은 녹화 때와 같게 둔다. 위치마다 집기와 넣기 성공 횟수를 적는다.
#
# 안전: 한 손은 팔로워 손목 아래를 받치고, 다른 손은 Ctrl+C (터미널 포커스 유지).
#       이상하면 Ctrl+C, 그래도 안 되면 팔로워 전원 어댑터를 뽑는다.
#       종료하면 토크가 꺼져 팔이 처진다.
#
# --strategy.type=base             녹화 없이 정책만 실행
# --policy.path                    학습 결과 pretrained_model 폴더 (가중치, 설정, 정규화값)
# --robot.max_relative_target=5.0  한 스텝에 목표가 현재값에서 5 이상 못 멀어지게 자른다
#                                 (스모크 때 10.0 은 너무 빨랐다. 낮추면 느려지지만 목표를 늦게 따라간다)
# --robot.cameras                  녹화 때와 이름(top, wrist), 해상도, fps, fourcc 가 같아야 한다
# --duration                       이 시간(초) 뒤 끝난다 (기본 0 은 무한)
# 리더(--teleop.*)는 쓰지 않는다. 모델이 팔로워를 직접 움직인다.
source ~/Projects/lerobot_lab/lerobot/.venv/bin/activate

# ---- 설정 (여기만 고친다) ----
NAME=${NAME:-omx_tomato_act}
DURATION=27
MAX_REL=5.0
# 카메라는 /dev/video 번호가 부팅마다 바뀌어서 USB 포트 위치(by-path)로 지정한다 (omx_record.sh 와 같다).
TOP=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:1:1.0-video-index0
# 2026-11-10: wrist 를 다른 USB 포트에 꽂아서 65:00.4 에서 65:00.3 의 포트 2로 바뀌었다 (사진으로 확인).
# 카메라를 다른 포트에 꽂으면 또 바뀐다. 그때는 ls -l /dev/v4l/by-path 와 사진으로 다시 확인한다.
WRIST=/dev/v4l/by-path/pci-0000:65:00.3-usb-0:2:1.0-video-index0
# ------------------------------

# 학습이 GPU 를 쓰는 중이면 실행하지 않는다.
if pgrep -f lerobot-train > /dev/null; then
  echo "lerobot-train 이 돌고 있다. 학습이 끝난 뒤에 실행한다."
  exit 1
fi

CKDIR=/home/minodori/Projects/lerobot_lab/outputs/$NAME/checkpoints
if [ -n "$1" ]; then
  STEP=$(printf "%06d" "$1")
  CKPT=$CKDIR/$STEP/pretrained_model
else
  LAST=$(ls -d "$CKDIR"/[0-9]* 2>/dev/null | sort | tail -1)
  CKPT=$LAST/pretrained_model
fi
if [ ! -d "$CKPT" ]; then
  echo "체크포인트가 없다: $CKPT"
  echo "있는 것:"; ls "$CKDIR" 2>/dev/null
  exit 1
fi
echo "체크포인트: $CKPT"
# TE=1 이면 시간적 앙상블을 켠다 (청크 경계 튐 완화). 매 스텝 추론하고 겹친 계획을 가중 평균한다.
#   n_action_steps 는 1 이어야 한다. 계수 0.01 은 ACT 논문 기본값. 재학습 없이 시험할 수 있다.
POLICY_OPTS=""
if [ "$TE" = "1" ]; then
  POLICY_OPTS="--policy.temporal_ensemble_coeff=0.01 --policy.n_action_steps=1"
fi
echo "정책 옵션: ${POLICY_OPTS:-(없음, 기본 청크 100스텝)}"
# 실행마다 로그를 저장한다. clamped 경고의 시각으로 계획이 튄 순간을 알 수 있다.
LOG=/home/minodori/Projects/lerobot_lab/outputs/${NAME}_rollout_$(date +%m%d_%H%M%S).log
echo "로그: $LOG"

CAMS="{ top: {type: opencv, index_or_path: '$TOP', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5}, wrist: {type: opencv, index_or_path: '$WRIST', width: 640, height: 480, fps: 30, fourcc: MJPG, warmup_s: 5} }"

lerobot-rollout \
  --strategy.type=base \
  --policy.path="$CKPT" \
  --robot.type=omx_follower \
  --robot.port=/dev/omx_follower \
  --robot.id=omx_follower_arm \
  --robot.max_relative_target=$MAX_REL \
  --robot.cameras="$CAMS" \
  --duration=$DURATION $POLICY_OPTS 2>&1 | tee "$LOG"

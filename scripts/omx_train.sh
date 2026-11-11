#!/bin/bash
# OMX 본 학습 (ACT). 처음 시작과 이어서 학습을 한 스크립트로 한다. 가이드 7단계.
# 실행: bash ~/Projects/lerobot_lab/scripts/omx_train.sh
#   - outputs/$NAME/checkpoints 에 체크포인트가 있으면 마지막 것에서 이어서 학습한다.
#   - 없으면 처음부터 학습한다.
#   - 끊겼거나 Ctrl+C 로 멈춘 뒤 같은 명령을 다시 치면 이어진다.
#   - 이어서 할 때 STEPS 는 지금까지 한 스텝보다 커야 한다 (같으면 0스텝으로 끝난다).
#   - 학습 로그는 outputs/${NAME}_train.log 에 덧붙는다.
#
# 옵션 (lerobot-train)
#   --dataset.eval_split   에피소드의 이 비율을 검증용으로 떼어 놓고 학습에 쓰지 않는다 (0 이면 끔)
#   --eval_steps           이 스텝마다 검증 데이터로 loss 를 잰다 (eval_split 이 0 보다 커야 한다)
#   --save_freq            이 스텝마다 체크포인트를 저장한다. 끊겨도 마지막 저장까지는 남는다.
#                          체크포인트 하나가 약 600MB 다.
#   --steps                전체 목표 스텝. 이어서 할 때도 같은 값이거나 더 크게 준다.
#
# 노트북 전원을 꽂고 절전을 끈다. 학습 중에는 GPU 를 쓰는 다른 작업(rollout 등)을 하지 않는다.
source ~/Projects/lerobot_lab/lerobot/.venv/bin/activate

# ---- 설정 (여기만 고친다) ----
# 아령 데이터는 DATA=omx_dumbbell 을 앞에 붙이면 NAME 이 omx_dumbbell_act 가 된다.
DATA=${DATA:-omx_tomato}
NAME=${NAME:-${DATA}_act}
STEPS=${STEPS:-20000}
SAVE_FREQ=2000
# 검증 분할은 끈다(0). 켜면 에피소드 맨 뒤 ceil(n x 비율)개가 검증용으로 빠지는데,
# 위치별로 순서대로 녹화해서 마지막 위치 하나만 빠지고 학습 데이터도 줄어든다.
# 진짜 평가는 rollout 으로 한다. 켜려면 EVAL_SPLIT=0.1, EVAL_STEPS=1000.
EVAL_SPLIT=0
EVAL_STEPS=0
BATCH_SIZE=8
# ------------------------------

BASE=/home/minodori/Projects/lerobot_lab
OUT=$BASE/outputs/$NAME
LOG=$BASE/outputs/${NAME}_train.log

if [ ! -d "$BASE/data/$DATA" ]; then
  echo "데이터셋이 없다: $BASE/data/$DATA"
  exit 1
fi

LAST=$(ls -d "$OUT"/checkpoints/[0-9]* 2>/dev/null | sort | tail -1)

if [ -n "$LAST" ]; then
  echo "이어서 학습: $LAST (목표 $STEPS 스텝)" | tee -a "$LOG"
  lerobot-train \
    --config_path="$LAST/pretrained_model/train_config.json" \
    --resume=true \
    --steps=$STEPS --save_freq=$SAVE_FREQ \
    --output_dir="$OUT" 2>&1 | tee -a "$LOG"
else
  if [ -e "$OUT" ]; then
    echo "출력 폴더가 이미 있는데 체크포인트가 없다: $OUT"
    echo "비어 있는 시도의 흔적이면 폴더를 지우고 다시 실행하거나 NAME 을 바꾼다."
    exit 1
  fi
  echo "처음부터 학습: $OUT ($STEPS 스텝)" | tee -a "$LOG"
  lerobot-train \
    --dataset.repo_id=minodori/$DATA \
    --dataset.root=$BASE/data/$DATA \
    --dataset.eval_split=$EVAL_SPLIT --eval_steps=$EVAL_STEPS \
    --policy.type=act --policy.push_to_hub=false \
    --batch_size=$BATCH_SIZE --steps=$STEPS --save_freq=$SAVE_FREQ \
    --log_freq=100 --wandb.enable=false \
    --job_name=$NAME --output_dir="$OUT" 2>&1 | tee -a "$LOG"
fi

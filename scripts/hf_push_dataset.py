"""omx_tomato 데이터셋을 허브(비공개)에 올린다.

push_to_hub 를 쓰는 이유: 올릴 때 버전 태그(v3.0)를 같이 붙여야
LeRobotDataset("minodori/omx_tomato") 로 허브에서 불러올 수 있다.
allow_patterns 로 data, meta, 카메라별 videos 폴더만 올린다.
videos/.sessions (세션 기록 숨김 폴더)가 올라간 적이 있어서 videos/** 는 쓰지 않는다.

실행: python ~/Projects/lerobot_lab/scripts/hf_push_dataset.py
"""
from lerobot.datasets.lerobot_dataset import LeRobotDataset

BASE = "/home/minodori/Projects/lerobot_lab"
REPO = "minodori/omx_tomato"

ds = LeRobotDataset(REPO, root=f"{BASE}/data/omx_tomato")
print("에피소드", ds.meta.total_episodes, "프레임", ds.meta.total_frames)

ds.push_to_hub(
    private=True,
    tags=["lerobot", "omx"],
    allow_patterns=["data/**", "meta/**", "videos/observation.images.*/**"],
)
print("완료:", f"https://huggingface.co/datasets/{REPO}")

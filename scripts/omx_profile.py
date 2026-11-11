"""OMX 팔로워의 Profile_Acceleration / Profile_Velocity 를 쓰고 다시 읽어 확인한다.

사용: python ~/Projects/lerobot_lab/scripts/omx_profile.py 10 50
      (인자 순서: 가속도 속도. 0 0 이면 제한 없음 = 원래 상태)

- 적용 대상: ID 11~15 (그리퍼 ID 16 은 전류 기반 위치 모드라 건드리지 않는다)
- 단위: 속도 1 = 0.229 rpm, 가속도 1 = 214.577 rev/min^2 (ROBOTIS e-Manual)
- RAM 영역이라 전원을 껐다 켜면 0 으로 돌아간다고 알고 있다 (확인 필요)
- 포트는 한 프로그램만 잡는다. lerobot-* 가 돌고 있으면 먼저 끈다.
"""
import sys
from dynamixel_sdk import PortHandler, PacketHandler

PORT = "/dev/omx_follower"
IDS = {11: "shoulder_pan", 12: "shoulder_lift", 13: "elbow_flex",
       14: "wrist_flex", 15: "wrist_roll"}
ADDR_ACC, ADDR_VEL = 108, 112

if len(sys.argv) != 3:
    sys.exit("사용: python omx_profile.py <가속도> <속도>   (예: 10 50, 원복은 0 0)")
acc, vel = int(sys.argv[1]), int(sys.argv[2])
if not (0 <= acc <= 200 and 0 <= vel <= 265):
    sys.exit("범위 밖: 가속도 0~200, 속도 0~265 (속도는 Velocity_Limit 265 이하)")

ph = PortHandler(PORT)
if not ph.openPort():
    sys.exit("포트 열기 실패: 다른 프로그램이 잡고 있는지 확인")
ph.setBaudRate(1000000)
pk = PacketHandler(2.0)

print(f"쓰기: ProfAcc={acc}, ProfVel={vel}")
ok = True
for i, name in IDS.items():
    r1, e1 = pk.write4ByteTxRx(ph, i, ADDR_ACC, acc)
    r2, e2 = pk.write4ByteTxRx(ph, i, ADDR_VEL, vel)
    a, ra, _ = pk.read4ByteTxRx(ph, i, ADDR_ACC)
    v, rv, _ = pk.read4ByteTxRx(ph, i, ADDR_VEL)
    good = (r1 == r2 == ra == rv == 0) and (e1 == e2 == 0) and a == acc and v == vel
    ok = ok and good
    print(f"  ID {i:2d} {name:14s} 읽은 값 ProfAcc={a} ProfVel={v}  {'OK' if good else '실패'}")
ph.closePort()
print("완료" if ok else "일부 실패: 위 줄을 확인")

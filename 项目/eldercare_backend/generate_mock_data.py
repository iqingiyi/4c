import random
from datetime import datetime, timedelta
from database import SessionLocal
from models import Elder, Caregiver, ServiceTask


def generate_data():
    db = SessionLocal()

    # 1. 每次运行前先清空旧数据（防止你多次运行生成太多重复数据）
    db.query(ServiceTask).delete()
    db.query(Caregiver).delete()
    db.query(Elder).delete()
    db.commit()

    print("🚀 开始为 4C 比赛生成核心模拟数据...")

    # 2. 生成 100 位老人数据
    surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫", "张", "刘"]
    titles = ["爷爷", "奶奶"]
    communities = ["幸福里小区", "阳光小区", "花园社区", "康乐小区"]
    risk_levels = ["高风险", "中风险", "低风险", "正常"]

    elders = []
    for i in range(100):
        surname = random.choice(surnames)
        title = random.choice(titles)
        gender = "男" if title == "爷爷" else "女"

        elder = Elder(
            name=f"{surname}{title}",
            age=random.randint(65, 95),
            gender=gender,
            # 权重：让正常和低风险的人数偏多，符合真实的社区养老分布
            risk_level=random.choices(risk_levels, weights=[10, 20, 30, 40])[0],
            community=random.choice(communities),
            address=f"{random.randint(1, 10)}栋{random.randint(1, 5)}单元{random.randint(101, 604)}室",
            # 模拟一个城市的经纬度微小偏移 (用于你的前端地图)
            latitude=39.9042 + random.uniform(-0.02, 0.02),
            longitude=116.4074 + random.uniform(-0.02, 0.02)
        )
        db.add(elder)
        elders.append(elder)  # 存入列表，等下分配订单用

    db.commit()
    print(f"✅ 成功生成 100 位老人档案！")

    # 3. 生成 20 位护理人员
    specialties = ["急救处置", "慢性病管理", "康复训练", "心理疏导", "基础护理"]
    caregivers = []
    for i in range(20):
        surname = random.choice(surnames)
        job_title = random.choice(["护士", "护工", "康复师"])
        caregiver = Caregiver(
            name=f"{surname}{job_title}",
            specialty=random.choice(specialties),
            status=random.choice(["空闲", "服务中"])
        )
        db.add(caregiver)
        caregivers.append(caregiver)

    db.commit()
    print(f"✅ 成功生成 20 位护理人员！")

    # 4. 生成 50 个服务工单 (用于你的服务调度大屏)
    task_types = ["生活照料", "健康监测", "医疗护理", "康复训练", "心理关怀"]
    priorities = ["高", "中", "低"]
    statuses = ["待分配", "服务中", "已完成"]

    for i in range(50):
        random_elder = random.choice(elders)
        random_caregiver = random.choice(caregivers)

        task = ServiceTask(
            elder_id=random_elder.id,
            # 一半的订单有护工，一半没有
            caregiver_id=random_caregiver.id if random.choice([True, False]) else None,
            task_type=random.choice(task_types),
            priority=random.choice(priorities),
            status=random.choice(statuses),
            create_time=datetime.now() - timedelta(minutes=random.randint(1, 1440))  # 过去24小时内的订单
        )

        # 逻辑修正：如果没有护工，状态必须是"待分配"
        if task.caregiver_id is None:
            task.status = "待分配"

        db.add(task)

    db.commit()
    print(f"✅ 成功生成 50 个调度工单！")

    db.close()
    print("🎉 大功告成！数据库已填充完毕，你的大屏马上就能活过来了！")


if __name__ == "__main__":
    generate_data()
import random
from database import SessionLocal, engine
from models import Elder, Caregiver, ServiceTask, Base


def generate_data():
    # 💡 核心修复：脚本运行时自动建表
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. 清空旧数据
    db.query(ServiceTask).delete()
    db.query(Caregiver).delete()
    db.query(Elder).delete()
    db.commit()

    print("🚀 开始生成 100 条带财务数据的模拟老人档案...")
    surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "张", "刘"]
    communities = ["幸福里小区", "阳光小区", "花园社区"]

    for i in range(100):
        elder = Elder(
            name=f"{random.choice(surnames)}{random.choice(['爷爷', '奶奶'])}",
            age=random.randint(70, 95),
            gender=random.choice(["男", "女"]),
            risk_level=random.choices(["高风险", "中风险", "低风险", "正常"], weights=[1, 2, 3, 4])[0],
            community=random.choice(communities),
            address=f"{random.randint(1, 10)}栋{random.randint(101, 601)}室",
            latitude=39.9042 + random.uniform(-0.02, 0.02),
            longitude=116.4074 + random.uniform(-0.02, 0.02),
            disability="未评估",
            # 💡 填充财务数据
            balance=round(random.uniform(500, 5000), 2),
            subsidy_standard=random.choice([300, 500, 800]),
            total_consumption=round(random.uniform(100, 2000), 2)
        )
        db.add(elder)

    db.commit()
    db.close()
    print("✅ 100 条数据已成功注入数据库！")


if __name__ == "__main__":
    generate_data()
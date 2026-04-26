import random
from database import SessionLocal, engine
from models import Elder, Caregiver, ServiceTask, FamilyMember, ChronicDiseaseRecord, Base


CHRONIC_DATA = [
    {"name": "张爷爷", "age": 73, "gender": "男", "area": "一号康养楼", "disease": "高血压", "level": "high",
     "bp": "176/106", "sugar": "5.8", "medicine": "硝苯地平（规律服药）", "follow": "需回访干预",
     "next": "2025-12-28", "note": "长期高血压，情绪易激动，严格低盐饮食，禁止熬夜"},
    {"name": "王奶奶", "age": 79, "gender": "女", "area": "二号护理楼", "disease": "2型糖尿病", "level": "mid",
     "bp": "136/84", "sugar": "10.2", "medicine": "二甲双胍（规律）", "follow": "已月度随访",
     "next": "2025-12-30", "note": "2型糖尿病，严控碳水，餐后适当活动"},
    {"name": "刘爷爷", "age": 81, "gender": "男", "area": "一号康养楼", "disease": "冠心病", "level": "high",
     "bp": "168/102", "sugar": "6.1", "medicine": "阿司匹林（偶尔漏服）", "follow": "待随访",
     "next": "2025-12-26", "note": "冠心病史5年，禁止劳累、情绪波动，常备急救药品"},
    {"name": "陈奶奶", "age": 75, "gender": "女", "area": "康复中心", "disease": "高血压", "level": "low",
     "bp": "128/79", "sugar": "5.6", "medicine": "氨氯地平（规律）", "follow": "已月度随访",
     "next": "2026-01-05", "note": "血压控制稳定，日常清淡饮食即可"},
    {"name": "周爷爷", "age": 84, "gender": "男", "area": "二号护理楼", "disease": "脑梗死", "level": "mid",
     "bp": "142/92", "sugar": "5.9", "medicine": "氯吡格雷（规律）", "follow": "需回访干预",
     "next": "2025-12-27", "note": "脑卒中后遗症，行动迟缓，专人陪护，防止跌倒"},
    {"name": "吴奶奶", "age": 71, "gender": "女", "area": "康复中心", "disease": "none", "level": "none",
     "bp": "126/78", "sugar": "5.2", "medicine": "无", "follow": "已月度随访",
     "next": "", "note": "身体健康，无基础慢病，每季度常规体检"},
    {"name": "郑爷爷", "age": 76, "gender": "男", "area": "一号康养楼", "disease": "痛风", "level": "low",
     "bp": "135/86", "sugar": "6.1", "medicine": "非布司他（规律）", "follow": "待随访",
     "next": "2026-01-15", "note": "禁止海鲜、动物内脏、浓汤等高嘌呤食物"},
    {"name": "杨奶奶", "age": 80, "gender": "女", "area": "二号护理楼", "disease": "高血脂", "level": "mid",
     "bp": "140/88", "sugar": "5.7", "medicine": "辛伐他汀（偶尔漏服）", "follow": "需回访干预",
     "next": "2026-01-10", "note": "低脂饮食，减少油腻，每日慢走锻炼"},
    {"name": "赵爷爷", "age": 85, "gender": "男", "area": "康复中心", "disease": "多种慢病", "level": "high",
     "bp": "170/100", "sugar": "7.2", "medicine": "氨氯地平+二甲双胍", "follow": "需回访干预",
     "next": "2025-12-29", "note": "高血压+糖尿病+冠心病，多重慢病，重点监护"},
]


def generate_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 清空旧数据 (新增清空家属表)
    db.query(ServiceTask).delete()
    db.query(Caregiver).delete()
    db.query(FamilyMember).delete()  # 💡 清空家属表
    db.query(ChronicDiseaseRecord).delete()
    db.query(Elder).delete()
    db.commit()

    print("🚀 开始生成后台测试数据...")
    surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "张", "刘"]
    communities = ["幸福里小区", "阳光小区", "花园社区"]

    special_tag_pool = ["独居", "空巢", "孤寡", "失能", "残疾", "高龄", "阿尔茨海默症"]
    relations = ["儿子", "女儿", "配偶", "侄子", "侄女"]

    # 生成 100 个老人
    for i in range(1, 101):
        tags = ""
        if random.random() < 0.3:
            tags = ",".join(random.sample(special_tag_pool, random.randint(1, 3)))

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
            balance=round(random.uniform(500, 5000), 2),
            subsidy_standard=random.choice([300, 500, 800]),
            total_consumption=round(random.uniform(100, 2000), 2),
            special_tags=tags
        )
        db.add(elder)
        db.commit()

        if random.random() < 0.8:
            fam = FamilyMember(
                elder_id=elder.id,
                name=f"{elder.name[0]}{random.choice(['强', '伟', '芳', '丽', '明'])}",
                phone=f"13{random.randint(100000000, 999999999)}",
                relation=random.choice(relations),
                is_primary=1
            )
            db.add(fam)

    db.commit()

    # 注意：这一段必须在 for i in range(1, 101) 外面
    disease_pool = [
        ("高血压", "high", "165/98", "5.8", "硝苯地平（规律服药）"),
        ("2型糖尿病", "mid", "136/84", "10.2", "二甲双胍（规律）"),
        ("冠心病", "high", "158/92", "6.1", "阿司匹林（偶尔漏服）"),
        ("脑梗死", "mid", "142/90", "5.9", "氯吡格雷（规律）"),
        ("高血脂", "mid", "138/86", "5.7", "阿托伐他汀（规律）"),
        ("痛风", "low", "132/82", "6.0", "非布司他（规律）"),
        ("多种慢病", "high", "170/100", "7.8", "氨氯地平+二甲双胍"),
        ("none", "none", "126/78", "5.2", "无"),
    ]

    all_elders = db.query(Elder).all()

    for elder in all_elders:
        disease, level, bp, sugar, medicine = random.choices(
            disease_pool,
            weights=[18, 16, 10, 8, 12, 6, 8, 22],
            k=1
        )[0]

        if disease == "none":
            follow = "已月度随访"
            next_date = ""
            note = "身体健康，无基础慢病，每季度常规体检。"
        else:
            follow = random.choice(["已月度随访", "待随访", "需回访干预"])
            next_date = f"2026-05-{random.randint(1, 28):02d}"
            note = f"{disease}长期管理对象，需定期监测血压血糖，按医嘱规律服药。"

        record = ChronicDiseaseRecord(
            name=elder.name,
            age=elder.age,
            gender=elder.gender,
            area=random.choice(["一号康养楼", "二号护理楼", "康复中心"]),
            disease=disease,
            level=level,
            bp=bp,
            sugar=sugar,
            medicine=medicine,
            follow=follow,
            next=next_date,
            note=note
        )
        db.add(record)

    db.commit()
    db.close()
    print("✅ 2.3特殊标签、2.4家属数据 与 3.2慢病档案 生成完毕！")


if __name__ == "__main__":
    generate_data()

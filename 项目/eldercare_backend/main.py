from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import models, database, random, math
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 自动同步数据库表结构
models.Base.metadata.create_all(bind=database.engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FamilyBindData(BaseModel):
    elder_id: int
    name: str
    phone: str
    relation: str
    is_primary: int = 1


class ChronicDiseaseData(BaseModel):
    name: str
    age: int
    gender: str = "男"
    area: str = "一号康养楼"
    disease: str = "none"
    level: str = "none"
    bp: str = ""
    sugar: str = ""
    medicine: str = "无"
    follow: str = "已月度随访"
    next: str = ""
    note: str = ""


CHRONIC_SEED_DATA = [
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


def seed_chronic_records(db: Session):
    if db.query(models.ChronicDiseaseRecord).count() > 0:
        return
    for item in CHRONIC_SEED_DATA:
        db.add(models.ChronicDiseaseRecord(**item))
    db.commit()


def chronic_to_frontend(record: models.ChronicDiseaseRecord):
    return {
        "id": record.id,
        "name": record.name,
        "age": record.age,
        "gender": record.gender,
        "area": record.area,
        "disease": record.disease,
        "level": record.level,
        "bp": record.bp,
        "sugar": record.sugar,
        "medicine": record.medicine,
        "follow": record.follow,
        "next": record.next or "",
        "note": record.note or "",
    }


def build_chronic_stats(records):
    today = datetime.now().date()
    wait_count = 0
    for item in records:
        if not item.next:
            continue
        try:
            next_date = datetime.strptime(item.next, "%Y-%m-%d").date()
        except ValueError:
            continue
        diff = (next_date - today).days
        if 0 <= diff <= 7:
            wait_count += 1

    return {
        "total": sum(1 for item in records if item.disease != "none"),
        "noDisease": sum(1 for item in records if item.disease == "none"),
        "hbp": sum(1 for item in records if item.disease == "高血压"),
        "high": sum(1 for item in records if item.level == "high"),
        "wait": wait_count,
        "totalCount": len(records),
    }


def build_chronic_charts(records):
    main_diseases = ["高血压", "2型糖尿病", "冠心病", "脑梗死", "高血脂"]
    disease_distribution = {
        "高血压": sum(1 for item in records if item.disease == "高血压"),
        "糖尿病": sum(1 for item in records if item.disease == "2型糖尿病"),
        "冠心病": sum(1 for item in records if item.disease == "冠心病"),
        "脑梗死": sum(1 for item in records if item.disease == "脑梗死"),
        "高血脂": sum(1 for item in records if item.disease == "高血脂"),
        "其他慢病": sum(1 for item in records if item.disease not in main_diseases and item.disease != "none"),
    }
    risk_distribution = {
        "high": sum(1 for item in records if item.level == "high"),
        "mid": sum(1 for item in records if item.level == "mid"),
        "low": sum(1 for item in records if item.level == "low"),
        "none": sum(1 for item in records if item.level == "none"),
    }
    return {"diseaseDistribution": disease_distribution, "riskDistribution": risk_distribution}


# --- 1. 大屏统计接口 ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": {
            "total_elders": db.query(models.Elder).count(),
            "high_risk_elders": db.query(models.Elder).filter(models.Elder.risk_level == "高风险").count(),
            "today_tasks": db.query(models.ServiceTask).count() or 50,
            "total_caregivers": db.query(models.Caregiver).count() or 20,
            "completion_rate": 96.8
        }
    }


# --- 2. 地图打点接口 (💡 补回了被我误删的中/低/正常风险统计) ---
@app.get("/api/map/elders")
def get_map_elders(db: Session = Depends(get_db)):
    elders = db.query(models.Elder).all()
    points = [
        {"id": e.id, "name": e.name, "lat": e.latitude, "lng": e.longitude, "risk": e.risk_level, "address": e.address}
        for e in elders]

    stats = {
        "total": len(elders),
        "high": sum(1 for e in elders if e.risk_level == "高风险"),
        "medium": sum(1 for e in elders if e.risk_level == "中风险"),
        "low": sum(1 for e in elders if e.risk_level == "低风险"),
        "normal": sum(1 for e in elders if e.risk_level == "正常")
    }
    return {"code": 200, "data": {"points": points, "stats": stats}}


# --- 3. 老人列表查询 (完美适配 2.1 档案和 2.5 资金台账) ---
@app.get("/api/elders", tags=["老人管理"])
def get_elders(name: str = "", community: str = "", db: Session = Depends(get_db)):
    query = db.query(models.Elder)
    if name: query = query.filter(models.Elder.name.contains(name))
    if community: query = query.filter(models.Elder.community == community)
    elders = query.order_by(models.Elder.id.desc()).all()

    result = []
    for e in elders:
        result.append({
            "id": e.id, "name": e.name, "gender": e.gender or "男", "age": e.age,
            "idCard": f"32050119{50 + (e.id % 40):02d}0101{1000 + e.id}",
            "phone": f"138{80000000 + e.id}",
            "community": e.community or "幸福里小区", "risk": e.risk_level,
            "disability": e.disability or "未评估",
            "balance": getattr(e, 'balance', 0.0),
            "subsidy": getattr(e, 'subsidy_standard', 0),
            "consumption": getattr(e, 'total_consumption', 0.0),
            "createTime": "2024-05-20", "address": e.address
        })
    return {"code": 200, "data": result}


# --- 4. 评估接口 ---
class AssessmentData(BaseModel):
    elder_id: int;
    eating: int;
    bathing: int;
    dressing: int;
    toileting: int;
    mobility: int


@app.post("/api/assess", tags=["健康评估"])
def assess_disability(data: AssessmentData, db: Session = Depends(get_db)):
    total_score = data.eating + data.bathing + data.dressing + data.toileting + data.mobility
    if total_score >= 90:
        level, color = "完全自理", "#10b981"
    elif total_score >= 60:
        level, color = "轻度失能", "#3b82f6"
    elif total_score >= 40:
        level, color = "中度失能", "#f97316"
    else:
        level, color = "重度失能", "#ef4444"

    elder = db.query(models.Elder).filter(models.Elder.id == data.elder_id).first()
    if elder:
        elder.disability = level
        if level == "重度失能": elder.risk_level = "高风险"
        db.commit()
    return {"code": 200, "data": {"total_score": total_score, "level": level, "color": color,
                                  "radar_data": [data.eating, data.bathing, data.dressing, data.toileting,
                                                 data.mobility]}}


# --- 5. 实时预警接口 ---
@app.get("/api/alerts/recent")
def get_recent_alerts(db: Session = Depends(get_db)):
    return {"code": 200, "data": [
        {"title": "跌倒风险预警", "icon": "fa-exclamation-triangle", "icon_color": "red",
         "desc": "张爷爷在卫生间跌倒风险较高", "time": "15:28:45", "tag_class": "urgent", "level": "紧急"},
        {"title": "心率异常预警", "icon": "fa-heartbeat", "icon_color": "orange", "desc": "李奶奶心率异常",
         "time": "15:25:12", "tag_class": "important", "level": "重要"}
    ]}


# --- 6. 智能调度中心接口 (💡 补回了被我误删的接口，解决 404 崩溃核心原因！) ---
@app.get("/api/tasks/recent")
def get_recent_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.ServiceTask).limit(4).all()
    result = []
    for t in tasks:
        elder = db.query(models.Elder).filter(models.Elder.id == t.elder_id).first()
        cg = db.query(models.Caregiver).filter(
            models.Caregiver.id == t.caregiver_id).first() if t.caregiver_id else None
        result.append({
            "elder_name": elder.name if elder else "未知",
            "elder_age": elder.age if elder else 0,
            "task_type": t.task_type,
            "address": elder.address if elder else "未知",
            "priority": t.priority,
            "status": t.status,
            "caregiver_name": cg.name if cg else "待分配",
            "distance": f"{round(random.uniform(0.5, 3.5), 1)}km"
        })
    return {"code": 200, "data": result}


# ==================== 3.1 实时健康数据监测 (IoT 接口) ====================
@app.get("/api/health/realtime", tags=["健康监测"])
def get_realtime_health(
        status: str = "all",  # 下拉框：状态筛选
        area: str = "all",  # 下拉框：区域筛选
        device: str = "all",  # 下拉框：设备筛选
        timeRange: str = "all",  # 下拉框：时间筛选
        tagStatus: str = "all",  # 快捷标签：全部/正常/预警/异常
        db: Session = Depends(get_db)
):
    """
    对接前端 index3.1.html 的实时物联网体征数据接口
    """
    # 1. 从数据库拉取真实老人基础信息
    query = db.query(models.Elder)
    if area != "all":
        query = query.filter(models.Elder.community == area)

    elders = query.limit(24).all()  # 限制返回数量，保证前端渲染不卡顿

    elder_list = []
    device_list = []

    # 获取一个护士名字作为兜底
    nurse = db.query(models.Caregiver).first()
    nurse_name = f"{nurse.name}(在岗)" if nurse else "李护士(在岗)"

    for e in elders:
        # 生成模拟的物联网体征数据
        base_hr = random.randint(65, 85)
        is_warn = random.random() > 0.85  # 15% 概率心率偏高
        is_danger = random.random() > 0.95  # 5% 概率紧急异常

        health_status = "normal"

        # 💡 神级联动逻辑开始！
        if is_danger:
            health_status = "danger"
            base_hr = random.randint(120, 140)

            # 🔥 如果物联网发现老人有危险，且他原本不是高风险
            if getattr(e, 'risk_level', '') != "高风险":
                e.risk_level = "高风险"  # 自动将老人升级为高危
                db.commit()  # 【关键】立刻保存到中央数据库！
                print(f"🚨 IoT系统报警：已将 {e.name} 的状态同步为高风险！")

        elif is_warn:
            health_status = "warn"
            base_hr = random.randint(100, 119)

        # ... 后面的组装数据逻辑保持不变 ...

        # 3. 处理前端传来的状态双重过滤 (下拉框 status 和 按钮 tagStatus)
        active_filter = tagStatus if tagStatus != "all" else status
        if active_filter != "all" and health_status != active_filter:
            continue  # 如果不符合筛选条件，跳过该老人

        # 4. 组装前端需要的长相完全一致的数据结构
        elder_list.append({
            "id": e.id,
            "name": e.name,
            "age": e.age,
            "gender": e.gender or "男",
            "room": f"{e.community} {e.address}",
            "nurse": nurse_name,
            "status": health_status,
            "heart": base_hr,
            "bp": f"{random.randint(110, 135)}/{random.randint(70, 85)}",
            "spo2": random.randint(96, 99) if health_status == "normal" else random.randint(88, 94),
            "temp": round(random.uniform(36.1, 37.2), 1),
            "time": random.choice(["刚刚", "10秒前", "30秒前"])
        })

        # 5. 组装设备列表数据
        device_type = random.choice(["智能手环", "床垫传感器", "电子血压计"])
        if device == "all" or device == device_type:
            device_list.append({
                "name": e.name,
                "device": device_type,
                "code": f"DEV-{1000 + e.id}",
                "status": random.choice(["在线", "在线", "在线", "低电量", "离线"]),
                "signal": random.choice(["强", "强", "中", "弱", "无"]),
                "power": f"{random.randint(5, 100)}%",
                "loc": "室内精准" if device_type != "智能手环" else "社区活动室",
                "runtime": f"{random.randint(1, 30)}天"
            })

    return {
        "code": 200,
        "data": elder_list,
        "devices": device_list
    }


# ==================== 3.2 慢病专项管理接口 ====================
@app.get("/api/chronic/list", tags=["健康监测"])
def get_chronic_list(
        diseaseType: str = "all",
        level: str = "all",
        name: str = "",
        area: str = "all",
        tagType: str = "all",
        db: Session = Depends(get_db)
):
    """对接前端 index3.2.html 的慢病专项管理列表、统计卡片和图表数据。"""
    seed_chronic_records(db)

    query = db.query(models.ChronicDiseaseRecord)
    if name:
        query = query.filter(models.ChronicDiseaseRecord.name.contains(name))
    if area != "all":
        query = query.filter(models.ChronicDiseaseRecord.area == area)
    if diseaseType != "all":
        query = query.filter(models.ChronicDiseaseRecord.disease == diseaseType)
    if level != "all":
        query = query.filter(models.ChronicDiseaseRecord.level == level)

    records = query.all()

    if tagType == "high":
        records = [item for item in records if item.level == "high"]
    elif tagType == "hbp":
        records = [item for item in records if item.disease == "高血压"]
    elif tagType == "diabetes":
        records = [item for item in records if item.disease == "2型糖尿病"]
    elif tagType == "old":
        records = [item for item in records if item.age >= 80 and item.level in ["high", "mid"]]
    elif tagType == "wait":
        today = datetime.now().date()
        wait_records = []
        for item in records:
            if not item.next:
                continue
            try:
                next_date = datetime.strptime(item.next, "%Y-%m-%d").date()
            except ValueError:
                continue
            if 0 <= (next_date - today).days <= 7:
                wait_records.append(item)
        records = wait_records

    level_order = {"high": 0, "mid": 1, "low": 2, "none": 3}
    records.sort(key=lambda item: (level_order.get(item.level, 9), item.id))

    return {
        "code": 200,
        "data": [chronic_to_frontend(item) for item in records],
        "stats": build_chronic_stats(records),
        "charts": build_chronic_charts(records),
    }


@app.get("/api/chronic/stats", tags=["健康监测"])
def get_chronic_stats(db: Session = Depends(get_db)):
    seed_chronic_records(db)
    records = db.query(models.ChronicDiseaseRecord).all()
    return {
        "code": 200,
        "data": build_chronic_stats(records),
        "charts": build_chronic_charts(records),
    }


@app.get("/api/chronic/{record_id}", tags=["健康监测"])
def get_chronic_detail(record_id: int, db: Session = Depends(get_db)):
    seed_chronic_records(db)
    record = db.query(models.ChronicDiseaseRecord).filter(models.ChronicDiseaseRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="未找到慢病档案")
    return {"code": 200, "data": chronic_to_frontend(record)}


@app.post("/api/chronic", tags=["健康监测"])
def create_chronic_record(data: ChronicDiseaseData, db: Session = Depends(get_db)):
    record = models.ChronicDiseaseRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"code": 200, "msg": "慢病档案新增成功", "data": chronic_to_frontend(record)}


@app.put("/api/chronic/{record_id}", tags=["健康监测"])
def update_chronic_record(record_id: int, data: ChronicDiseaseData, db: Session = Depends(get_db)):
    record = db.query(models.ChronicDiseaseRecord).filter(models.ChronicDiseaseRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="未找到慢病档案")

    for key, value in data.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return {"code": 200, "msg": "慢病档案保存成功", "data": chronic_to_frontend(record)}


@app.delete("/api/chronic/{record_id}", tags=["健康监测"])
def delete_chronic_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(models.ChronicDiseaseRecord).filter(models.ChronicDiseaseRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="未找到慢病档案")
    db.delete(record)
    db.commit()
    return {"code": 200, "msg": "慢病档案删除成功"}


# ==================== 2.3 特殊老人管理接口 (完美适配前端字段) ====================

@app.get("/api/elders/special", tags=["老人管理"])
def get_special_elders(db: Session = Depends(get_db)):
    """获取特殊老人列表"""
    elders = db.query(models.Elder).filter(models.Elder.special_tags != "").all()

    result = []
    for e in elders:
        # 提取第一个特殊标签作为前端的 specialType
        first_tag = e.special_tags.split(",")[0] if e.special_tags else "特殊老人"

        result.append({
            "id": e.id,
            "name": e.name,
            "gender": e.gender or "男",
            "age": e.age,
            # 伪造一个身份证号和一些兜底数据满足前端展示需求
            "idCard": f"32050119{50 + (e.id % 40):02d}0101{1000 + e.id}",
            "specialType": first_tag,  # 💡 严格匹配前端驼峰
            "careLevel": "二级照护",  # 兜底数据
            "contact": "社区网格员",  # 兜底数据
            "createTime": "2024-05-20"  # 兜底数据
        })
    return {"code": 200, "data": result}


# ==================== 2.4 家属绑定管理接口 (完美适配前端字段) ====================

# (这里的 bind_family_member 接口保持不变)
@app.post("/api/family/bind", tags=["家属管理"])
def bind_family_member(data: FamilyBindData, db: Session = Depends(get_db)):
    # ... (保持原样) ...
    elder = db.query(models.Elder).filter(models.Elder.id == data.elder_id).first()
    if not elder: return {"code": 404, "msg": "未找到该老人档案"}
    new_member = models.FamilyMember(**data.dict())
    db.add(new_member)
    db.commit()
    return {"code": 200, "msg": "家属绑定成功", "data": {"id": new_member.id}}


@app.get("/api/family/list", tags=["家属管理"])
def get_family_list(elder_name: str = "", db: Session = Depends(get_db)):
    """查询家属绑定列表"""
    query = db.query(models.FamilyMember, models.Elder).join(models.Elder)
    if elder_name:
        query = query.filter(models.Elder.name.contains(elder_name))

    records = query.all()
    result = []
    for fam, elder in records:
        result.append({
            "id": fam.id,
            "elderName": elder.name,  # 💡 严格匹配前端驼峰 elderName
            "familyName": fam.name,  # 💡 严格匹配前端驼峰 familyName
            "relation": fam.relation,
            "phone": fam.phone,
            "bindTime": "2024-05-20",  # 补充前端需要的时间
            "status": "正常"  # 补充前端需要的状态
        })
    return {"code": 200, "data": result}

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import models, database, random, math
from pydantic import BaseModel
import json
from fastapi.responses import Response

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
    seed_chronic_records(db)
    seed_medicine_data(db)
    seed_exam_data(db)
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
class MedicinePlanData(BaseModel):
    elder_name: str
    elder_tag: str = ""
    drug_name: str
    drug_type: str = ""
    dose: str = ""
    freq: str = ""
    time: str = ""
    use_type: str = "long"
    status: str = "wait"
    notify: str = "设备+平台+子女"
    device_status: str = "online"
    start_time: str = ""
    end_time: str = ""
    doctor_advice: str = ""
    remark: str = ""


class MedicineLibraryData(BaseModel):
    drug_name: str
    drug_type: str = ""
    spec: str = ""
    usage: str = ""
    contraindication: str = ""
    remark: str = ""


def medicine_to_frontend(item):
    return {
        "id": item.id,
        "elderName": item.elder_name,
        "elderTag": item.elder_tag,
        "drugName": item.drug_name,
        "drugType": item.drug_type,
        "dose": item.dose,
        "freq": item.freq,
        "time": item.time,
        "useType": item.use_type,
        "status": item.status,
        "notify": item.notify,
        "deviceStatus": item.device_status,
        "startTime": item.start_time,
        "endTime": item.end_time,
        "doctorAdvice": item.doctor_advice,
        "remark": item.remark,
    }


def seed_medicine_data(db: Session):
    if db.query(models.MedicinePlan).count() > 0:
        return

    medicine_pool = [
        {
            "drug_name": "硝苯地平缓释片",
            "drug_type": "降压药",
            "dose": "10mg",
            "freq": "每日2次",
            "time": "08:00,20:00",
            "doctor_advice": "低盐饮食，规律监测血压。",
            "remark": "低血压、严重主动脉瓣狭窄慎用。"
        },
        {
            "drug_name": "二甲双胍片",
            "drug_type": "降糖药",
            "dose": "0.5g",
            "freq": "每日2次",
            "time": "08:30,18:30",
            "doctor_advice": "餐后服用，注意监测血糖。",
            "remark": "严重肾功能不全禁用。"
        },
        {
            "drug_name": "阿司匹林肠溶片",
            "drug_type": "抗血小板药",
            "dose": "100mg",
            "freq": "每日1次",
            "time": "09:00",
            "doctor_advice": "如有黑便、胃痛需及时上报。",
            "remark": "活动性消化道出血禁用。"
        },
        {
            "drug_name": "阿托伐他汀钙片",
            "drug_type": "调脂药",
            "dose": "20mg",
            "freq": "每晚1次",
            "time": "21:00",
            "doctor_advice": "定期复查肝功能和血脂。",
            "remark": "活动性肝病慎用。"
        },
        {
            "drug_name": "氯吡格雷片",
            "drug_type": "抗血小板药",
            "dose": "75mg",
            "freq": "每日1次",
            "time": "09:00",
            "doctor_advice": "注意皮下出血、牙龈出血等情况。",
            "remark": "出血风险人群慎用。"
        },
        {
            "drug_name": "奥美拉唑肠溶胶囊",
            "drug_type": "胃药",
            "dose": "20mg",
            "freq": "每日1次",
            "time": "07:30",
            "doctor_advice": "早餐前服用。",
            "remark": "长期使用需关注胃肠反应。"
        }
    ]

    elders = db.query(models.Elder).all()

    # 如果 Elder 表还没有数据，就兜底生成 3 条
    if not elders:
        fallback_names = [
            ("张爷爷", "高血压"),
            ("王奶奶", "糖尿病"),
            ("刘爷爷", "冠心病"),
        ]
        for name, tag in fallback_names:
            med = random.choice(medicine_pool)
            db.add(models.MedicinePlan(
                elder_name=name,
                elder_tag=tag,
                drug_name=med["drug_name"],
                drug_type=med["drug_type"],
                dose=med["dose"],
                freq=med["freq"],
                time=med["time"],
                use_type="long",
                status=random.choice(["on", "wait", "off", "delay"]),
                notify="智能药盒+平台+子女",
                device_status=random.choice(["online", "online", "offline"]),
                start_time="2026-04-01",
                end_time="长期用药",
                doctor_advice=med["doctor_advice"],
                remark=med["remark"]
            ))
    else:
        # 给大约 80% 老人生成用药计划
        for elder in elders:
            if random.random() > 0.8:
                continue

            med = random.choice(medicine_pool)
            db.add(models.MedicinePlan(
                elder_name=elder.name,
                elder_tag=elder.special_tags or elder.risk_level or "普通老人",
                drug_name=med["drug_name"],
                drug_type=med["drug_type"],
                dose=med["dose"],
                freq=med["freq"],
                time=med["time"],
                use_type=random.choice(["long", "long", "long", "temp"]),
                status=random.choices(
                    ["on", "wait", "off", "delay", "pause"],
                    weights=[45, 25, 10, 12, 8],
                    k=1
                )[0],
                notify=random.choice(["智能药盒+平台+子女", "平台+护理员", "智能药盒+护理员+子女"]),
                device_status=random.choices(
                    ["online", "offline", "error"],
                    weights=[80, 15, 5],
                    k=1
                )[0],
                start_time=f"2026-04-{random.randint(1, 20):02d}",
                end_time=random.choice(["长期用药", "2026-05-30", "2026-06-15"]),
                doctor_advice=med["doctor_advice"],
                remark=med["remark"]
            ))

    library = [
        {
            "drug_name": "硝苯地平缓释片",
            "drug_type": "降压药",
            "spec": "10mg*30片",
            "usage": "口服，每日1-2次",
            "contraindication": "低血压、严重主动脉瓣狭窄慎用",
            "remark": "钙通道阻滞剂"
        },
        {
            "drug_name": "二甲双胍片",
            "drug_type": "降糖药",
            "spec": "0.5g*60片",
            "usage": "餐后口服",
            "contraindication": "严重肾功能不全禁用",
            "remark": "双胍类降糖药"
        },
        {
            "drug_name": "阿司匹林肠溶片",
            "drug_type": "抗血小板药",
            "spec": "100mg*30片",
            "usage": "每日一次",
            "contraindication": "活动性消化道出血禁用",
            "remark": "抗血小板药"
        },
        {
            "drug_name": "阿托伐他汀钙片",
            "drug_type": "调脂药",
            "spec": "20mg*28片",
            "usage": "每晚一次",
            "contraindication": "活动性肝病慎用",
            "remark": "他汀类调脂药"
        },
        {
            "drug_name": "氯吡格雷片",
            "drug_type": "抗血小板药",
            "spec": "75mg*28片",
            "usage": "每日一次",
            "contraindication": "活动性出血禁用",
            "remark": "抗血栓常用药"
        },
        {
            "drug_name": "奥美拉唑肠溶胶囊",
            "drug_type": "胃药",
            "spec": "20mg*14粒",
            "usage": "早餐前口服",
            "contraindication": "对本品过敏者禁用",
            "remark": "质子泵抑制剂"
        }
    ]

    for item in library:
        db.add(models.MedicineLibrary(**item))

    db.commit()
def build_medicine_stats(records):
    total = len(records)
    wait = sum(1 for item in records if item.status == "wait")
    off = sum(1 for item in records if item.status == "off")
    on = sum(1 for item in records if item.status == "on")
    compliance = round((on / total) * 100, 1) if total else 0
    return {
        "total": total,
        "wait": wait,
        "off": off,
        "on": on,
        "compliance": compliance
    }


@app.get("/api/medicine/list", tags=["用药管理"])
def get_medicine_list(
    elderName: str = "",
    drugType: str = "all",
    status: str = "all",
    deviceStatus: str = "all",
    tagType: str = "all",
    db: Session = Depends(get_db)
):
    seed_medicine_data(db)
    query = db.query(models.MedicinePlan)

    if elderName:
        query = query.filter(models.MedicinePlan.elder_name.contains(elderName))
    if drugType != "all":
        query = query.filter(models.MedicinePlan.drug_type == drugType)
    if status != "all":
        query = query.filter(models.MedicinePlan.status == status)
    if deviceStatus != "all":
        query = query.filter(models.MedicinePlan.device_status == deviceStatus)

    records = query.order_by(models.MedicinePlan.id.desc()).all()

    if tagType == "long":
        records = [item for item in records if item.use_type == "long"]
    elif tagType == "temp":
        records = [item for item in records if item.use_type == "temp"]
    elif tagType == "risk":
        records = [item for item in records if item.status in ["off", "delay"]]
    elif tagType == "pause":
        records = [item for item in records if item.status == "pause"]

    return {
        "code": 200,
        "data": [medicine_to_frontend(item) for item in records],
        "stats": build_medicine_stats(records)
    }


@app.get("/api/medicine/stats", tags=["用药管理"])
def get_medicine_stats(db: Session = Depends(get_db)):
    seed_medicine_data(db)
    records = db.query(models.MedicinePlan).all()
    return {"code": 200, "data": build_medicine_stats(records)}


@app.get("/api/medicine/library/list", tags=["用药管理"])
def get_medicine_library_list(keyword: str = "", db: Session = Depends(get_db)):
    seed_medicine_data(db)
    query = db.query(models.MedicineLibrary)
    if keyword:
        query = query.filter(models.MedicineLibrary.drug_name.contains(keyword))
    records = query.order_by(models.MedicineLibrary.id.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": item.id,
                "drugName": item.drug_name,

                # 兼容前端表格字段
                "firstCategory": item.drug_type,
                "secondCategory": item.remark or item.drug_type,
                "spec": item.spec,
                "dose": item.spec,
                "contraindication": item.contraindication,
                "stock": "充足",
                "expireDate": "2027-12-31",
                "status": "正常",

                # 保留原字段
                "drugType": item.drug_type,
                "usage": item.usage,
                "remark": item.remark,
            }
            for item in records
        ]
    }


@app.post("/api/medicine/library", tags=["用药管理"])
def create_medicine_library(data: MedicineLibraryData, db: Session = Depends(get_db)):
    item = models.MedicineLibrary(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "msg": "药品库新增成功", "data": {"id": item.id}}


@app.get("/api/medicine/export", tags=["用药管理"])
def export_medicine_data(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    seed_medicine_data(db)
    records = db.query(models.MedicinePlan).all()

    rows = ["老人姓名,药品名称,药品分类,剂量,频次,时间,状态,设备状态,开始日期,结束日期"]
    for item in records:
        rows.append(
            f"{item.elder_name},{item.drug_name},{item.drug_type},{item.dose},{item.freq},{item.time},{item.status},{item.device_status},{item.start_time},{item.end_time}"
        )

    csv_data = "\ufeff" + "\n".join(rows)
    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=medicine_export.csv"}
    )


@app.get("/api/medicine/ai-summary", tags=["用药管理"])
def get_medicine_ai_summary(db: Session = Depends(get_db)):
    seed_medicine_data(db)
    records = db.query(models.MedicinePlan).all()
    stats = build_medicine_stats(records)
    report = (
        f"全院共有 {stats['total']} 条用药计划，其中待服药 {stats['wait']} 条，"
        f"漏服 {stats['off']} 条，服药依从率约 {stats['compliance']}%。"
        "建议对漏服老人进行智能药盒提醒、护理员复核和家属同步通知。"
    )
    return {"code": 200, "data": {"report": report}}


@app.get("/api/medicine/ai/{plan_id}", tags=["用药管理"])
def get_medicine_ai(plan_id: int, db: Session = Depends(get_db)):
    seed_medicine_data(db)
    item = db.query(models.MedicinePlan).filter(models.MedicinePlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到用药计划")

    report = (
        f"{item.elder_name} 当前用药为 {item.drug_name}，分类为 {item.drug_type}，"
        f"剂量 {item.dose}，频次 {item.freq}。"
        f"当前状态为 {item.status}，设备状态为 {item.device_status}。"
        "建议结合老人慢病档案、血压血糖数据和医嘱进行持续监测。"
    )
    return {"code": 200, "data": {"report": report}}


@app.get("/api/medicine/{plan_id}", tags=["用药管理"])
def get_medicine_detail(plan_id: int, db: Session = Depends(get_db)):
    seed_medicine_data(db)
    item = db.query(models.MedicinePlan).filter(models.MedicinePlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到用药计划")

    logs = [
        {"date": "2026-04-25 08:00", "result": "已按时服药", "status": "on"},
        {"date": "2026-04-25 20:00", "result": "待服药", "status": "wait"},
        {"date": "2026-04-24 08:00", "result": "智能药盒确认已服药", "status": "on"},
    ]

    return {"code": 200, "data": medicine_to_frontend(item), "logs": logs}


@app.post("/api/medicine", tags=["用药管理"])
def create_medicine_plan(data: MedicinePlanData, db: Session = Depends(get_db)):
    item = models.MedicinePlan(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "msg": "用药计划新增成功", "data": medicine_to_frontend(item)}


@app.put("/api/medicine/{plan_id}", tags=["用药管理"])
def update_medicine_plan(plan_id: int, data: MedicinePlanData, db: Session = Depends(get_db)):
    item = db.query(models.MedicinePlan).filter(models.MedicinePlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到用药计划")

    for key, value in data.model_dump().items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return {"code": 200, "msg": "用药计划保存成功", "data": medicine_to_frontend(item)}


@app.patch("/api/medicine/{plan_id}/status", tags=["用药管理"])
def update_medicine_status(plan_id: int, status: str, db: Session = Depends(get_db)):
    item = db.query(models.MedicinePlan).filter(models.MedicinePlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到用药计划")

    item.status = status
    db.commit()
    return {"code": 200, "msg": "状态更新成功"}


@app.delete("/api/medicine/{plan_id}", tags=["用药管理"])
def delete_medicine_plan(plan_id: int, db: Session = Depends(get_db)):
    item = db.query(models.MedicinePlan).filter(models.MedicinePlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到用药计划")

    db.delete(item)
    db.commit()
    return {"code": 200, "msg": "用药计划删除成功"}
@app.put("/api/medicine/library/{library_id}", tags=["用药管理"])
def update_medicine_library(library_id: int, data: MedicineLibraryData, db: Session = Depends(get_db)):
    item = db.query(models.MedicineLibrary).filter(models.MedicineLibrary.id == library_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="未找到药品库记录")

    update_data = data.model_dump()

    for key, value in update_data.items():
        if hasattr(item, key):
            setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return {
        "code": 200,
        "msg": "药品库编辑成功",
        "data": {
            "id": item.id,
            "drugName": item.drug_name,
            "drugType": item.drug_type,
            "spec": item.spec,
            "usage": item.usage,
            "contraindication": item.contraindication,
            "remark": item.remark
        }
    }
class PhysicalExamData(BaseModel):
    elder_name: str
    elder_tag: str = ""
    age: int = 0
    gender: str = ""
    area: str = ""

    exam_date: str = ""
    exam_type: str = "常规体检"
    hospital: str = ""
    doctor: str = ""

    height: str = ""
    weight: str = ""
    bmi: str = ""
    blood_pressure: str = ""
    blood_sugar: str = ""
    blood_lipid: str = ""
    heart_rate: str = ""
    liver_function: str = ""
    kidney_function: str = ""
    ecg: str = ""
    chest_ct: str = ""
    bone_density: str = ""

    conclusion: str = ""
    risk_level: str = "normal"
    follow_advice: str = ""
    next_exam_date: str = ""
    file_status: str = "completed"
    remark: str = ""


def pydantic_to_dict(data):
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data.dict()


def exam_to_frontend(item):
    return {
        "id": item.id,
        "elderName": item.elder_name,
        "elderTag": item.elder_tag,
        "age": item.age,
        "gender": item.gender,
        "area": item.area,

        "examDate": item.exam_date,
        "examType": item.exam_type,
        "hospital": item.hospital,
        "doctor": item.doctor,

        "height": item.height,
        "weight": item.weight,
        "bmi": item.bmi,
        "bloodPressure": item.blood_pressure,
        "bloodSugar": item.blood_sugar,
        "bloodLipid": item.blood_lipid,
        "heartRate": item.heart_rate,
        "liverFunction": item.liver_function,
        "kidneyFunction": item.kidney_function,
        "ecg": item.ecg,
        "chestCt": item.chest_ct,
        "boneDensity": item.bone_density,

        "conclusion": item.conclusion,
        "riskLevel": item.risk_level,
        "followAdvice": item.follow_advice,
        "nextExamDate": item.next_exam_date,
        "fileStatus": item.file_status,
        "remark": item.remark,
    }


def seed_exam_data(db: Session):
    if db.query(models.PhysicalExamRecord).count() > 0:
        return

    elders = db.query(models.Elder).all()

    exam_types = ["常规体检", "慢病复查", "心脑血管专项", "糖尿病专项", "康复评估", "入院评估"]
    hospitals = ["智护颐年健康中心", "社区卫生服务中心", "市人民医院体检中心", "康养联合门诊"]
    doctors = ["李医生", "王医生", "张医生", "陈医生", "刘医生"]
    areas = ["一号康养楼", "二号护理楼", "康复中心"]

    if not elders:
        fallback = [
            {"name": "张爷爷", "age": 73, "gender": "男", "risk_level": "高风险", "special_tags": "高血压"},
            {"name": "王奶奶", "age": 79, "gender": "女", "risk_level": "中风险", "special_tags": "糖尿病"},
            {"name": "刘爷爷", "age": 81, "gender": "男", "risk_level": "高风险", "special_tags": "冠心病"},
        ]
        elders = []
        for x in fallback:
            class TempElder:
                pass
            e = TempElder()
            e.name = x["name"]
            e.age = x["age"]
            e.gender = x["gender"]
            e.risk_level = x["risk_level"]
            e.special_tags = x["special_tags"]
            e.community = random.choice(areas)
            elders.append(e)

    for elder in elders:
        risk = random.choices(
            ["normal", "low", "mid", "high"],
            weights=[35, 30, 25, 10],
            k=1
        )[0]

        systolic = random.randint(118, 178)
        diastolic = random.randint(72, 108)
        sugar = round(random.uniform(4.8, 11.8), 1)
        heart_rate = random.randint(58, 102)
        height = random.randint(150, 178)
        weight = random.randint(48, 82)
        bmi_val = round(weight / ((height / 100) ** 2), 1)

        if risk == "high":
            conclusion = "存在明显健康风险，建议重点随访并进行专科复查。"
            advice = "纳入重点健康监测名单，建议护理员每日巡查，医生每周复核。"
            status = "abnormal"
        elif risk == "mid":
            conclusion = "部分指标异常，需持续观察并进行生活方式干预。"
            advice = "建议两周内复查血压、血糖或相关异常指标。"
            status = "completed"
        elif risk == "low":
            conclusion = "轻度异常，整体情况稳定。"
            advice = "建议保持规律作息和清淡饮食，按月复查。"
            status = "completed"
        else:
            conclusion = "本次体检未见明显异常，身体状况总体良好。"
            advice = "建议继续常规健康管理，每季度体检一次。"
            status = "completed"

        record = models.PhysicalExamRecord(
            elder_name=elder.name,
            elder_tag=getattr(elder, "special_tags", "") or getattr(elder, "risk_level", "") or "普通老人",
            age=elder.age,
            gender=elder.gender,
            area=random.choice(areas),

            exam_date=f"2026-04-{random.randint(1, 27):02d}",
            exam_type=random.choice(exam_types),
            hospital=random.choice(hospitals),
            doctor=random.choice(doctors),

            height=f"{height}cm",
            weight=f"{weight}kg",
            bmi=str(bmi_val),
            blood_pressure=f"{systolic}/{diastolic}",
            blood_sugar=str(sugar),
            blood_lipid=random.choice(["正常", "轻度升高", "偏高", "需复查"]),
            heart_rate=f"{heart_rate}次/分",
            liver_function=random.choice(["正常", "轻度异常", "转氨酶偏高"]),
            kidney_function=random.choice(["正常", "肌酐轻度升高", "需复查"]),
            ecg=random.choice(["正常心电图", "窦性心律", "ST-T改变", "偶发早搏"]),
            chest_ct=random.choice(["未见明显异常", "肺纹理增多", "陈旧性纤维灶", "建议复查"]),
            bone_density=random.choice(["正常", "骨量减少", "骨质疏松风险"]),

            conclusion=conclusion,
            risk_level=risk,
            follow_advice=advice,
            next_exam_date=f"2026-05-{random.randint(1, 28):02d}",
            file_status=status,
            remark="系统自动生成体检档案，可用于比赛演示。"
        )
        db.add(record)

    db.commit()


def build_exam_stats(records):
    total = len(records)
    normal = sum(1 for x in records if x.risk_level == "normal")
    low = sum(1 for x in records if x.risk_level == "low")
    mid = sum(1 for x in records if x.risk_level == "mid")
    high = sum(1 for x in records if x.risk_level == "high")
    abnormal = sum(1 for x in records if x.file_status == "abnormal")
    completed = sum(1 for x in records if x.file_status == "completed")

    return {
        "total": total,
        "normal": normal,
        "low": low,
        "mid": mid,
        "high": high,
        "abnormal": abnormal,
        "completed": completed,
        "abnormalRate": round((abnormal / total) * 100, 1) if total else 0
    }


def build_exam_charts(records):
    type_count = {}
    risk_count = {"normal": 0, "low": 0, "mid": 0, "high": 0}

    for item in records:
        type_count[item.exam_type] = type_count.get(item.exam_type, 0) + 1
        if item.risk_level in risk_count:
            risk_count[item.risk_level] += 1

    return {
        "examTypeDistribution": type_count,
        "riskDistribution": risk_count
    }


@app.get("/api/exam/list", tags=["体检档案记录"])
def get_exam_list(
    elderName: str = "",
    examType: str = "all",
    riskLevel: str = "all",
    fileStatus: str = "all",
    area: str = "all",
    db: Session = Depends(get_db)
):
    seed_exam_data(db)

    query = db.query(models.PhysicalExamRecord)

    if elderName:
        query = query.filter(models.PhysicalExamRecord.elder_name.contains(elderName))
    if examType != "all":
        query = query.filter(models.PhysicalExamRecord.exam_type == examType)
    if riskLevel != "all":
        query = query.filter(models.PhysicalExamRecord.risk_level == riskLevel)
    if fileStatus != "all":
        query = query.filter(models.PhysicalExamRecord.file_status == fileStatus)
    if area != "all":
        query = query.filter(models.PhysicalExamRecord.area == area)

    records = query.order_by(models.PhysicalExamRecord.exam_date.desc()).all()

    return {
        "code": 200,
        "data": [exam_to_frontend(item) for item in records],
        "stats": build_exam_stats(records),
        "charts": build_exam_charts(records)
    }


@app.get("/api/exam/stats", tags=["体检档案记录"])
def get_exam_stats(db: Session = Depends(get_db)):
    seed_exam_data(db)
    records = db.query(models.PhysicalExamRecord).all()
    return {
        "code": 200,
        "data": build_exam_stats(records),
        "charts": build_exam_charts(records)
    }


@app.get("/api/exam/export", tags=["体检档案记录"])
def export_exam_data(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    seed_exam_data(db)
    records = db.query(models.PhysicalExamRecord).order_by(models.PhysicalExamRecord.exam_date.desc()).all()

    rows = [
        "老人姓名,年龄,性别,区域,体检日期,体检类型,体检机构,医生,血压,血糖,BMI,心率,风险等级,档案状态,下次体检日期,结论"
    ]

    for item in records:
        rows.append(
            f"{item.elder_name},{item.age},{item.gender},{item.area},{item.exam_date},{item.exam_type},"
            f"{item.hospital},{item.doctor},{item.blood_pressure},{item.blood_sugar},{item.bmi},"
            f"{item.heart_rate},{item.risk_level},{item.file_status},{item.next_exam_date},{item.conclusion}"
        )

    csv_data = "\ufeff" + "\n".join(rows)

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=physical_exam_export.csv"}
    )


@app.get("/api/exam/ai-summary", tags=["体检档案记录"])
def get_exam_ai_summary(db: Session = Depends(get_db)):
    seed_exam_data(db)
    records = db.query(models.PhysicalExamRecord).all()
    stats = build_exam_stats(records)

    report = (
        f"全院共有 {stats['total']} 份体检档案，其中高风险 {stats['high']} 人，"
        f"中风险 {stats['mid']} 人，异常档案 {stats['abnormal']} 份，"
        f"异常率约 {stats['abnormalRate']}%。建议对高风险老人建立一人一档复查计划，"
        "重点关注血压、血糖、心电图、肾功能和骨密度异常人群。"
    )

    return {
        "code": 200,
        "data": {
            "report": report
        }
    }


@app.get("/api/exam/ai/{exam_id}", tags=["体检档案记录"])
def get_exam_ai(exam_id: int, db: Session = Depends(get_db)):
    seed_exam_data(db)
    item = db.query(models.PhysicalExamRecord).filter(models.PhysicalExamRecord.id == exam_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="未找到体检档案")

    report = (
        f"{item.elder_name} 本次体检类型为 {item.exam_type}，体检日期 {item.exam_date}。"
        f"血压 {item.blood_pressure}，血糖 {item.blood_sugar}，BMI {item.bmi}，"
        f"心率 {item.heart_rate}。综合风险等级为 {item.risk_level}。"
        f"体检结论：{item.conclusion} 建议：{item.follow_advice}"
    )

    return {
        "code": 200,
        "data": {
            "report": report
        }
    }


@app.get("/api/exam/{exam_id}", tags=["体检档案记录"])
def get_exam_detail(exam_id: int, db: Session = Depends(get_db)):
    seed_exam_data(db)
    item = db.query(models.PhysicalExamRecord).filter(models.PhysicalExamRecord.id == exam_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="未找到体检档案")

    return {
        "code": 200,
        "data": exam_to_frontend(item)
    }


@app.post("/api/exam", tags=["体检档案记录"])
def create_exam_record(data: PhysicalExamData, db: Session = Depends(get_db)):
    payload = pydantic_to_dict(data)
    item = models.PhysicalExamRecord(**payload)

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "code": 200,
        "msg": "体检档案新增成功",
        "data": exam_to_frontend(item)
    }


@app.put("/api/exam/{exam_id}", tags=["体检档案记录"])
def update_exam_record(exam_id: int, data: PhysicalExamData, db: Session = Depends(get_db)):
    item = db.query(models.PhysicalExamRecord).filter(models.PhysicalExamRecord.id == exam_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="未找到体检档案")

    payload = pydantic_to_dict(data)

    for key, value in payload.items():
        if hasattr(item, key):
            setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return {
        "code": 200,
        "msg": "体检档案保存成功",
        "data": exam_to_frontend(item)
    }


@app.delete("/api/exam/{exam_id}", tags=["体检档案记录"])
def delete_exam_record(exam_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PhysicalExamRecord).filter(models.PhysicalExamRecord.id == exam_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="未找到体检档案")

    db.delete(item)
    db.commit()

    return {
        "code": 200,
        "msg": "体检档案删除成功"
    }
# =========================
# 3.5 健康趋势分析接口
# =========================

def safe_count(query):
    try:
        return query.count()
    except Exception:
        return 0


def risk_to_score(risk_level: str):
    mapping = {
        "normal": 90,
        "low": 78,
        "mid": 62,
        "high": 42,
        "无风险": 90,
        "低风险": 78,
        "中风险": 62,
        "高风险": 42,
        "正常": 88,
    }
    return mapping.get(risk_level or "", 70)


def parse_systolic(bp: str):
    try:
        return int(str(bp).split("/")[0])
    except Exception:
        return 0


def parse_sugar(value: str):
    try:
        return float(value)
    except Exception:
        return 0.0


def build_health_trend_records(db: Session):
    """
    基于已有老人、慢病、用药、体检数据生成健康趋势分析记录。
    不新增表，实时计算。
    """
    elders = db.query(models.Elder).all()

    exam_map = {}
    try:
        exams = db.query(models.PhysicalExamRecord).all()
        for item in exams:
            exam_map.setdefault(item.elder_name, []).append(item)
    except Exception:
        exams = []

    chronic_map = {}
    try:
        seed_chronic_records(db)
        chronic_records = db.query(models.ChronicDiseaseRecord).all()
        for item in chronic_records:
            chronic_map.setdefault(item.name, []).append(item)
    except Exception as e:
        print("健康趋势慢病数据读取失败：", e)
        chronic_records = []

    medicine_map = {}
    try:
        medicine_records = db.query(models.MedicinePlan).all()
        for item in medicine_records:
            medicine_map.setdefault(item.elder_name, []).append(item)
    except Exception:
        medicine_records = []

    result = []

    for elder in elders:
        elder_exams = exam_map.get(elder.name, [])
        elder_chronics = chronic_map.get(elder.name, [])
        elder_meds = medicine_map.get(elder.name, [])

        latest_exam = None
        if elder_exams:
            latest_exam = sorted(elder_exams, key=lambda x: x.exam_date or "", reverse=True)[0]

        base_score = 88

        if latest_exam:
            base_score = risk_to_score(latest_exam.risk_level)

            systolic = parse_systolic(latest_exam.blood_pressure)
            sugar = parse_sugar(latest_exam.blood_sugar)

            if systolic >= 160:
                base_score -= 12
            elif systolic >= 140:
                base_score -= 6

            if sugar >= 11:
                base_score -= 12
            elif sugar >= 7:
                base_score -= 6

        if elder_chronics:
            base_score -= min(len(elder_chronics) * 2, 10)

        if elder_meds:
            abnormal_meds = [x for x in elder_meds if x.status in ["off", "delay", "pause"]]
            base_score -= min(len(abnormal_meds) * 2, 8)

        base_score = max(30, min(98, base_score))

        if base_score >= 85:
            trend = "持续良好"
            trend_type = "up"
            risk_label = "低风险"
        elif base_score >= 70:
            trend = "基本稳定"
            trend_type = "stable"
            risk_label = "中低风险"
        elif base_score >= 55:
            trend = "波动观察"
            trend_type = "warning"
            risk_label = "中风险"
        else:
            trend = "明显下降"
            trend_type = "down"
            risk_label = "高风险"

        chronic_tags = []
        if getattr(elder, "special_tags", ""):
            chronic_tags.append(elder.special_tags)
        for c in elder_chronics:
            if getattr(c, "disease", "") and c.disease != "none":
                chronic_tags.append(c.disease)

        chronic_text = "、".join(list(dict.fromkeys([x for x in chronic_tags if x]))) or "暂无明显慢病"

        area_value = (
            latest_exam.area if latest_exam and getattr(latest_exam, "area", "")
            else (
                elder_chronics[0].area if elder_chronics and getattr(elder_chronics[0], "area", "")
                else getattr(elder, "community", "") or getattr(elder, "address", "") or "未分区"
            )
        )

        result.append({
            "id": elder.id,
            "elderName": elder.name,
            "age": elder.age,
            "gender": elder.gender,
            "area": area_value,
            "riskLevel": risk_label,
            "healthScore": base_score,
            "trend": trend,
            "trendType": trend_type,
            "chronicTags": chronic_text,
            "examCount": len(elder_exams),
            "medicineCount": len(elder_meds),
            "latestExamDate": latest_exam.exam_date if latest_exam else "-",
            "bloodPressure": latest_exam.blood_pressure if latest_exam else "-",
            "bloodSugar": latest_exam.blood_sugar if latest_exam else "-",
            "bmi": latest_exam.bmi if latest_exam else "-",
            "advice": build_health_advice(base_score, chronic_text, latest_exam)
        })

    return result

def filter_health_trend_records(
    records,
    areaId: str = "all",
    ageRange: str = "全部年龄段",
    healthType: str = "全维度健康"
):
    if areaId and areaId not in ["all", "0", "全域总览", "全部区域"]:
        records = [x for x in records if areaId in str(x.get("area", ""))]

    if ageRange == "70-74岁":
        records = [x for x in records if 70 <= int(x.get("age") or 0) <= 74]
    elif ageRange == "75-79岁":
        records = [x for x in records if 75 <= int(x.get("age") or 0) <= 79]
    elif ageRange == "80岁以上":
        records = [x for x in records if int(x.get("age") or 0) >= 80]

    if healthType == "心脑血管":
        records = [
            x for x in records
            if "冠心病" in x.get("chronicTags", "")
            or "脑梗" in x.get("chronicTags", "")
            or parse_systolic(x.get("bloodPressure", "")) >= 140
        ]
    elif healthType == "代谢慢病":
        records = [
            x for x in records
            if "糖尿病" in x.get("chronicTags", "")
            or "高血脂" in x.get("chronicTags", "")
            or parse_sugar(x.get("bloodSugar", "")) >= 7
        ]
    elif healthType == "肝肾功能":
        records = [
            x for x in records
            if "肾" in x.get("advice", "")
            or "肝" in x.get("advice", "")
        ]

    return records

def build_health_advice(score, chronic_text, exam):
    if score >= 85:
        return "健康状态良好，建议维持现有照护方案，定期体检。"

    advice = []

    if "高血压" in chronic_text:
        advice.append("加强血压监测，建议低盐饮食并规律服药。")
    if "糖尿病" in chronic_text:
        advice.append("加强血糖监测，控制碳水摄入并关注足部护理。")
    if "冠心病" in chronic_text or "心脑血管" in chronic_text:
        advice.append("关注心脑血管风险，建议定期复查心电图和血脂。")

    if exam:
        systolic = parse_systolic(exam.blood_pressure)
        sugar = parse_sugar(exam.blood_sugar)

        if systolic >= 140:
            advice.append("近期血压偏高，建议纳入重点随访。")
        if sugar >= 7:
            advice.append("近期血糖偏高，建议复查空腹血糖或糖化血红蛋白。")

    if not advice:
        advice.append("健康趋势存在波动，建议护理员加强日常观察。")

    return " ".join(advice)


@app.get("/api/health-trend/list", tags=["健康趋势分析"])
def get_health_trend_list(
    elderName: str = "",
    riskLevel: str = "all",
    trendType: str = "all",
    area: str = "all",
    db: Session = Depends(get_db)
):
    records = build_health_trend_records(db)

    if elderName:
        records = [x for x in records if elderName in x["elderName"]]

    if riskLevel != "all":
        records = [x for x in records if x["riskLevel"] == riskLevel]

    if trendType != "all":
        records = [x for x in records if x["trendType"] == trendType]

    if area != "all":
        records = [x for x in records if area in x["area"]]

    records = sorted(records, key=lambda x: x["healthScore"])

    return {
        "code": 200,
        "data": records,
        "total": len(records)
    }


@app.get("/api/health-trend/overview", tags=["健康趋势分析"])
def get_health_trend_overview(
    areaId: str = "all",
    ageRange: str = "全部年龄段",
    healthType: str = "全维度健康",
    timeType: str = "月度趋势",
    db: Session = Depends(get_db)
):
    records = build_health_trend_records(db)
    records = filter_health_trend_records(records, areaId, ageRange, healthType)
    print("【overview筛选】", {
        "areaId": areaId,
        "ageRange": ageRange,
        "healthType": healthType,
        "timeType": timeType,
        "count": len(records),
        "areas": list(set([x.get("area") for x in records]))[:10]
    })

    total = len(records)

    high_risk = len([x for x in records if x["healthScore"] < 55])
    warning = len([x for x in records if 55 <= x["healthScore"] < 70])
    stable = len([x for x in records if 70 <= x["healthScore"] < 85])
    good = len([x for x in records if x["healthScore"] >= 85])

    avg_score = round(sum(x["healthScore"] for x in records) / total, 1) if total else 0

    down_count = len([x for x in records if x["trendType"] == "down"])
    warning_count = len([x for x in records if x["trendType"] == "warning"])

    return {
        "code": 200,
        "data": {
            "total": total,
            "avgScore": avg_score,
            "good": good,
            "stable": stable,
            "warning": warning,
            "highRisk": high_risk,
            "trendWarning": warning_count,
            "trendDown": down_count,
            "attentionRate": round(((warning_count + down_count) / total) * 100, 1) if total else 0
        }
    }
@app.get("/api/health-trend/charts", tags=["健康趋势分析"])
def get_health_trend_charts(
    areaId: str = "all",
    ageRange: str = "全部年龄段",
    healthType: str = "全维度健康",
    timeType: str = "月度趋势",
    db: Session = Depends(get_db)
):
    records = build_health_trend_records(db)
    records = filter_health_trend_records(records, areaId, ageRange, healthType)
    print("【charts筛选】", {
        "areaId": areaId,
        "ageRange": ageRange,
        "healthType": healthType,
        "timeType": timeType,
        "count": len(records),
        "areas": list(set([x.get("area") for x in records]))[:10]
    })
    score_ranges = {
        "优秀 85+": 0,
        "良好 70-84": 0,
        "预警 55-69": 0,
        "高危 <55": 0
    }

    trend_count = {
        "持续良好": 0,
        "基本稳定": 0,
        "波动观察": 0,
        "明显下降": 0
    }

    age_groups = {
        "70-74岁": [],
        "75-79岁": [],
        "80-84岁": [],
        "85岁以上": []
    }

    chronic_count = {}
    area_score = {}

    for item in records:
        score = item["healthScore"]

        if score >= 85:
            score_ranges["优秀 85+"] += 1
        elif score >= 70:
            score_ranges["良好 70-84"] += 1
        elif score >= 55:
            score_ranges["预警 55-69"] += 1
        else:
            score_ranges["高危 <55"] += 1

        trend_count[item["trend"]] = trend_count.get(item["trend"], 0) + 1

        age = item["age"] or 0
        if 70 <= age <= 74:
            age_groups["70-74岁"].append(score)
        elif 75 <= age <= 79:
            age_groups["75-79岁"].append(score)
        elif 80 <= age <= 84:
            age_groups["80-84岁"].append(score)
        elif age >= 85:
            age_groups["85岁以上"].append(score)

        for tag in str(item["chronicTags"]).replace("，", "、").split("、"):
            tag = tag.strip()
            if tag and tag not in ["暂无明显慢病", "正常"]:
                chronic_count[tag] = chronic_count.get(tag, 0) + 1

        area = item["area"] or "未分区"
        area_score.setdefault(area, []).append(score)

    age_score = {
        k: round(sum(v) / len(v), 1) if v else 0
        for k, v in age_groups.items()
    }

    area_avg_score = {
        k: round(sum(v) / len(v), 1) if v else 0
        for k, v in area_score.items()
    }

    top_chronic = dict(sorted(chronic_count.items(), key=lambda x: x[1], reverse=True)[:8])
    top_area = dict(sorted(area_avg_score.items(), key=lambda x: x[1], reverse=True)[:8])

    avg_score = round(sum(x["healthScore"] for x in records) / len(records), 1) if records else 0

    return {
        "code": 200,
        "data": {
            "scoreRanges": score_ranges,
            "trendCount": trend_count,
            "ageScore": age_score,
            "chronicCount": top_chronic,
            "areaAvgScore": top_area,
            "monthlyScore": {
                "1月": max(30, avg_score - 4),
                "2月": max(30, avg_score - 3),
                "3月": max(30, avg_score - 2),
                "4月": avg_score,
                "5月": min(98, avg_score + 1),
                "6月": min(98, avg_score + 2)
            }
        }
    }
@app.get("/api/health-trend/elder/{elder_name}", tags=["健康趋势分析"])
def get_elder_health_trend(elder_name: str, db: Session = Depends(get_db)):
    records = build_health_trend_records(db)
    item = next((x for x in records if x["elderName"] == elder_name), None)

    if not item:
        raise HTTPException(status_code=404, detail="未找到老人健康趋势记录")

    # 用当前分数模拟近六个月趋势，便于前端画趋势图
    score = item["healthScore"]

    trend_line = [
        max(30, min(98, score - 8)),
        max(30, min(98, score - 5)),
        max(30, min(98, score - 2)),
        max(30, min(98, score)),
        max(30, min(98, score + 1)),
        max(30, min(98, score + 2)),
    ]

    return {
        "code": 200,
        "data": {
            **item,
            "trendLine": {
                "labels": ["1月", "2月", "3月", "4月", "5月", "6月"],
                "values": trend_line
            },
            "dimensionScore": {
                "血压管理": max(40, item["healthScore"] - 5),
                "血糖管理": max(40, item["healthScore"] - 3),
                "用药依从": max(40, item["healthScore"] + 2),
                "体检完成": max(40, item["healthScore"] + 4),
                "慢病控制": max(40, item["healthScore"] - 6),
                "生活能力": max(40, item["healthScore"] + 1),
            }
        }
    }


@app.get("/api/health-trend/ai-summary", tags=["健康趋势分析"])
def get_health_trend_ai_summary(
    areaId: str = "all",
    ageRange: str = "全部年龄段",
    healthType: str = "全维度健康",
    timeType: str = "月度趋势",
    db: Session = Depends(get_db)
):
    overview = get_health_trend_overview(areaId, ageRange, healthType, timeType, db)["data"]
    charts = get_health_trend_charts(areaId, ageRange, healthType, timeType, db)["data"]

    report = (
        f"当前筛选条件下共纳入 {overview['total']} 位老人健康趋势分析，"
        f"平均健康评分为 {overview['avgScore']} 分。"
        f"其中健康良好 {overview['good']} 人，状态稳定 {overview['stable']} 人，"
        f"需要预警观察 {overview['warning']} 人，高风险 {overview['highRisk']} 人。"
        f"当前趋势异常关注率为 {overview['attentionRate']}%。"
        "建议对评分低于 70 分的老人建立健康干预清单，重点联动慢病管理、用药管理和体检复查。"
    )

    return {
        "code": 200,
        "data": {
            "report": report,
            "overview": overview,
            "charts": charts
        }
    }
@app.get("/api/health-trend/export", tags=["健康趋势分析"])
def export_health_trend(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    records = build_health_trend_records(db)

    rows = [
        "老人姓名,年龄,性别,所属区域,健康评分,趋势状态,风险等级,慢病标签,体检次数,用药计划数,最近体检日期,血压,血糖,BMI,健康建议"
    ]

    for item in records:
        rows.append(
            f"{item['elderName']},{item['age']},{item['gender']},{item['area']},"
            f"{item['healthScore']},{item['trend']},{item['riskLevel']},{item['chronicTags']},"
            f"{item['examCount']},{item['medicineCount']},{item['latestExamDate']},"
            f"{item['bloodPressure']},{item['bloodSugar']},{item['bmi']},{item['advice']}"
        )

    csv_data = "\ufeff" + "\n".join(rows)

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=health_trend_export.csv"}
    )
def filter_health_records_by_area(records, area: str = "all"):
    if not area or area == "all":
        return records
    return [x for x in records if area in (x.get("area") or "")]


def sync_alarms_from_elders(db: Session):
    """🔥 核心联动引擎：自动去数据库抓高危老人，转换成告警记录！"""
    # 1. 查出所有真实的、被标为高风险的老人
    high_risk_elders = db.query(models.Elder).filter(models.Elder.risk_level == "高风险").all()

    for elder in high_risk_elders:
        # 2. 检查这个老人的告警是不是已经在列表里了（且还没处理完）
        existing_alarm = db.query(models.AlarmRecord).filter(
            models.AlarmRecord.elder_name == elder.name,
            models.AlarmRecord.status.in_(["未处理", "处理中"])
        ).first()

        if not existing_alarm:
            # 3. 如果没有，就根据他的真实档案生成一条告警！
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            device_type = random.choice(["智能手环", "毫米波雷达", "智能床垫"])
            content = "SOS紧急求助" if device_type == "智能手环" else (
                "监测到跌倒" if device_type == "毫米波雷达" else "心率异常超标")

            new_alarm = models.AlarmRecord(
                level=1 if content != "心率异常超标" else 2,
                level_text="紧急" if content != "心率异常超标" else "重要",
                elder_name=elder.name,  # 💡 真实老人姓名
                building=elder.community,  # 💡 真实老人小区
                room=elder.address,  # 💡 真实老人家址
                device_code=f"DEV-{elder.id}-{random.randint(1000, 9999)}",
                device_type=device_type,
                content=content,
                time=now_str,
                duration="刚刚",
                status="未处理",
                nurse="张护理员",
                nurse_phone="13800138000",
                is_timeout=0,
                is_read=0,
                logs=json.dumps([f"{now_str} 系统自动生成告警 (由IoT底层数据触发)"], ensure_ascii=False)
            )
            db.add(new_alarm)
    db.commit()


def alarm_to_frontend(alarm):
    return {
        "id": alarm.id,
        "level": alarm.level,
        "levelText": alarm.level_text,
        "elderName": alarm.elder_name,
        "building": alarm.building,
        "room": alarm.room,
        "deviceCode": alarm.device_code,
        "deviceType": alarm.device_type,
        "content": alarm.content,
        "time": alarm.time,
        "duration": alarm.duration,
        "status": alarm.status,
        "nurse": alarm.nurse,
        "nursePhone": alarm.nurse_phone,
        "isTimeout": bool(alarm.is_timeout),
        "isRead": bool(alarm.is_read),
        "log": json.loads(alarm.logs) if alarm.logs else []
    }


@app.get("/api/alarms/list", tags=["安全风险预警"])
def get_alarm_list(
        name: str = "", building: str = "", status: str = "", type: str = "",
        tab: str = "real", page: int = 1, limit: int = 10,
        db: Session = Depends(get_db)
):
    """获取告警列表（含大屏专供的楼栋与设备实时统计）"""
    sync_alarms_from_elders(db)
    query = db.query(models.AlarmRecord)

    if name: query = query.filter(models.AlarmRecord.elder_name.contains(name))
    if building: query = query.filter(models.AlarmRecord.building == building)
    if type: query = query.filter(models.AlarmRecord.content == type)
    if status:
        query = query.filter(models.AlarmRecord.status == status)
    else:
        if tab == "real":
            query = query.filter(models.AlarmRecord.status.in_(["未处理", "处理中"]))
        elif tab == "history":
            query = query.filter(models.AlarmRecord.status.in_(["已处理", "已忽略", "已撤销", "已派单"]))

    records = query.all()
    total = len(records)
    start, end = (page - 1) * limit, page * limit
    data = [alarm_to_frontend(r) for r in records[start:end]]

    # ==================== 💡 核心：为大屏实时计算侧边栏统计 ====================
    all_records = db.query(models.AlarmRecord).all()

    # 1. 楼栋风险统计
    b_stats = {}
    for r in all_records:
        if r.status in ["未处理", "处理中"]:
            b_stats[r.building] = b_stats.get(r.building, 0) + 1
    building_list = [{"name": k, "count": v} for k, v in b_stats.items()]

    # 2. 设备在线状态
    device_list = [
        {"name": "智能手环", "online": random.randint(120, 135)},
        {"name": "毫米波雷达", "online": random.randint(40, 50)},
        {"name": "智能床垫", "online": random.randint(30, 45)}
    ]

    # 3. 5个顶部卡片数据
    stats = {
        "red": sum(1 for r in all_records if r.level == 1 and r.status in ["未处理", "处理中"]),
        "orange": sum(1 for r in all_records if r.level == 2 and r.status in ["未处理", "处理中"]),
        "yellow": sum(1 for r in all_records if r.level == 3 and r.status in ["未处理", "处理中"]),
        "total": len(all_records),
        "handleRate": round((sum(1 for r in all_records if r.status in ["已处理", "已忽略", "已撤销", "已派单"]) / len(all_records)) * 100, 2) if all_records else 100.0,
        "buildingStats": building_list,
        "deviceStats": device_list
    }

    # 4. 图表数据 (💡 彻底修复：历史折线点固定，当前点随真实数据库数量增加)
    static_history = [1, 2, 3, 4, 5]
    current_total = len(all_records)
    if current_total < 5:
        current_total = 5

    charts = {
        "pie": [sum(1 for r in all_records if t in r.content) for t in ["SOS", "跌倒", "离床", "健康"]],
        "line": static_history + [current_total]
    }

    return {"code": 200, "data": data, "total": total, "stats": stats, "charts": charts}
# ... 下面的 /api/alarms/{alarm_id}/action 等接口保持原样不要动 ...

# 前端传参的数据模型
class AlarmActionData(BaseModel):
    user: str = "管理员"
    remark: str = ""


@app.post("/api/alarms/{alarm_id}/action", tags=["安全风险预警"])
def handle_alarm_action(alarm_id: int, action: str, data: AlarmActionData, db: Session = Depends(get_db)):
    """通用状态扭转引擎：处理、关闭、忽略、撤销、派单"""
    alarm = db.query(models.AlarmRecord).filter(models.AlarmRecord.id == alarm_id).first()
    if not alarm: raise HTTPException(status_code=404, detail="告警不存在")

    alarm.is_read = 1  # 只要操作了，肯定算已读
    logs = json.loads(alarm.logs) if alarm.logs else []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if action == "handle":
        alarm.status = "处理中"
        logs.append(f"{now_str} {data.user} 提交处置记录：{data.remark}")
    elif action == "close":
        alarm.status = "已处理"
        logs.append(f"{now_str} {data.user} 关闭告警")
    elif action == "ignore":
        alarm.status = "已忽略"
        logs.append(f"{now_str} {data.user} 标记为误报忽略")
    elif action == "revoke":
        alarm.status = "已撤销"
        logs.append(f"{now_str} {data.user} 撤销本次告警")
    elif action == "dispatch":
        alarm.status = "已派单"
        logs.append(f"{now_str} {data.user} {data.remark}")
    elif action == "read":
        pass  # 只标已读，不改状态

    alarm.logs = json.dumps(logs, ensure_ascii=False)
    db.commit()
    return {"code": 200, "msg": "操作成功"}


@app.post("/api/alarms/read-all", tags=["安全风险预警"])
def read_all_alarms(db: Session = Depends(get_db)):
    """一键已读"""
    db.query(models.AlarmRecord).update({"is_read": 1})
    db.commit()
    return {"code": 200, "msg": "全部标记为已读成功"}
@app.get("/api/alarms/export", tags=["安全风险预警"])
def export_alarm_data(db: Session = Depends(get_db)):
    """将告警记录导出为 CSV 格式 (带 UTF-8 BOM 兼容 Excel)"""
    # 获取所有的告警记录（按照时间倒序）
    records = db.query(models.AlarmRecord).order_by(models.AlarmRecord.id.desc()).all()

    # 构建 CSV 表头
    rows = [
        "告警等级,老人姓名,所属楼栋,房间位置,设备编号,设备类型,告警内容,告警时长,告警时间,责任护理员,处理状态"
    ]

    # 遍历拼装数据
    for item in records:
        rows.append(
            f"{item.level_text},{item.elder_name},{item.building},{item.room},{item.device_code},"
            f"{item.device_type},{item.content},{item.duration},{item.time},{item.nurse},{item.status}"
        )

    # 加上 \ufeff 也就是 BOM 头，这样用 Windows Excel 打开才不会乱码！
    csv_data = "\ufeff" + "\n".join(rows)

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=alarm_export_data.csv"}
    )


# ==================== 4.2 跌倒/离床预警专项接口 ====================

def generate_bed_data(db: Session):
    """核心物联模拟引擎：根据真实老人档案生成实时床位和设备状态"""
    elders = db.query(models.Elder).all()
    data = []
    stats = {"inBed": 0, "leaveBed": 0, "overTime": 0, "fall": 0, "deviceErr": 0, "unHandleWarn": 0}

    for e in elders:
        # 基于老人风险等级赋予不同的离床/跌倒概率
        base_risk = 0.5 if e.risk_level == "高风险" else 0.1
        rand_val = random.random()

        if rand_val > (0.95 - base_risk * 0.1):
            state = "跌倒预警"
            stats["fall"] += 1
            stats["unHandleWarn"] += 1
        elif rand_val > (0.85 - base_risk * 0.2):
            state = "离床超时"
            stats["overTime"] += 1
            stats["unHandleWarn"] += 1
        elif rand_val > 0.6:
            state = "临时离床"
            stats["leaveBed"] += 1
        else:
            state = "正常在床"
            stats["inBed"] += 1

        # 模拟设备状态
        mattress = "正常" if random.random() < 0.95 else "离线"
        radar = "正常" if random.random() < 0.95 else "故障"
        if mattress != "正常" or radar != "正常":
            stats["deviceErr"] += 1

        data.append({
            "warnNo": f"WARN-{datetime.now().strftime('%m%d')}-{1000 + e.id}",
            "bedCode": f"BED-{e.community[:2] if e.community else '康养'}-{100 + e.id}",
            "elderName": e.name,
            "age": e.age,
            "disableLevel": e.disability or "自理",
            "isHighRisk": e.risk_level == "高风险",
            "areaType": e.community or "康养社区",
            "address": e.address,
            "mattressStatus": mattress,
            "radarStatus": radar,
            "bedState": state,
            "warnHandle": "未处理" if state in ["离床超时", "跌倒预警"] else "正常",
            "leaveTime": f"{random.randint(1, 45)}分钟" if state != "正常在床" else "-",
            "syncTime": "刚刚"
        })
    return data, stats


@app.get("/api/bed/dashboard", tags=["跌倒离床"])
def get_bed_dashboard(db: Session = Depends(get_db)):
    """获取4.2界面的顶部统计、图表和夜间监护名单"""
    bed_list, stats = generate_bed_data(db)

    # 💡 修复：历史数据锁死，只有当前点随真实状态变动
    static_history = [2, 4, 3, 6, 5]
    current_total = stats["leaveBed"] + stats["overTime"]

    charts = {
        "line": static_history + [current_total],
        "pie": [stats["fall"], stats["overTime"], stats["deviceErr"],
                max(1, len(bed_list) - stats["fall"] - stats["overTime"] - stats["deviceErr"])]
    }

    night_list = [x for x in bed_list if x["isHighRisk"]]
    for n in night_list:
        n["riskLevel"] = "高危"
        n["guardReason"] = "有跌倒史/重度失能"
        n["guardUser"] = random.choice(["张护理员", "李护理员", "王站长"])
        n["lastCheckTime"] = f"22:{random.randint(10, 50)}"

    return {"code": 200, "stats": stats, "charts": charts, "nightList": night_list[:15]}

@app.get("/api/bed/list", tags=["跌倒离床"])
def get_bed_list(name: str = "", area: str = "", status: str = "", device: str = "", db: Session = Depends(get_db)):
    """获取床位监控列表，支持复合筛选"""
    bed_list, _ = generate_bed_data(db)

    # 执行筛选
    if name: bed_list = [x for x in bed_list if name in x["elderName"] or name in x["bedCode"]]
    if area: bed_list = [x for x in bed_list if area in x["areaType"]]
    if status:
        if status == "在床":
            bed_list = [x for x in bed_list if "在床" in x["bedState"]]
        elif status == "离床":
            bed_list = [x for x in bed_list if "离床" in x["bedState"] and "超时" not in x["bedState"]]
        elif status == "超时":
            bed_list = [x for x in bed_list if "超时" in x["bedState"]]
        elif status == "跌倒":
            bed_list = [x for x in bed_list if "跌倒" in x["bedState"]]
    if device:
        if device == "在线":
            bed_list = [x for x in bed_list if x["mattressStatus"] == "正常" and x["radarStatus"] == "正常"]
        elif device == "离线":
            bed_list = [x for x in bed_list if x["mattressStatus"] == "离线" or x["radarStatus"] == "离线"]
        elif device == "故障":
            bed_list = [x for x in bed_list if x["mattressStatus"] == "故障" or x["radarStatus"] == "故障"]

    return {"code": 200, "data": bed_list}


@app.post("/api/bed/action", tags=["跌倒离床"])
def bed_action(action: str, db: Session = Depends(get_db)):
    """通用动作处理（消警、重启、救援、同步）"""
    return {"code": 200, "msg": "指令下发成功"}


@app.get("/api/bed/export", tags=["跌倒离床"])
def export_bed_data(db: Session = Depends(get_db)):
    """导出台账"""
    bed_list, _ = generate_bed_data(db)
    rows = [
        "告警编号,床位编码,老人姓名,年龄,失能等级,是否高危,区域类型,详细地址,床垫状态,雷达状态,监测状态,离床时长,最后同步"]
    for x in bed_list:
        rows.append(
            f"{x['warnNo']},{x['bedCode']},{x['elderName']},{x['age']},{x['disableLevel']},{'是' if x['isHighRisk'] else '否'},{x['areaType']},{x['address']},{x['mattressStatus']},{x['radarStatus']},{x['bedState']},{x['leaveTime']},{x['syncTime']}")
    csv_data = "\ufeff" + "\n".join(rows)
    from fastapi.responses import Response
    return Response(content=csv_data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=bed_monitoring_export.csv"})
# ==================== 4.2 扩展模块：历史、设置 ====================

@app.get("/api/bed/history", tags=["跌倒离床"])
def get_bed_history(db: Session = Depends(get_db)):
    """模拟拉取历史预警与处置记录"""
    elders = db.query(models.Elder).limit(8).all()
    history = []
    for e in elders:
        history.append({
            "time": f"2026-04-27 {random.randint(10,23):02d}:{random.randint(10,59):02d}",
            "elderName": e.name,
            "bedCode": f"BED-10{e.id}",
            "type": random.choice(["离床超时", "跌倒告警", "心率异常"]),
            "handler": random.choice(["张护理员", "李护理员", "系统自动闭环"]),
            "result": "已安全处置，老人状态平稳"
        })
    # 按时间倒序排序
    history.sort(key=lambda x: x["time"], reverse=True)
    return {"code": 200, "data": history}

# 模拟一个常驻内存的网关配置参数
SYSTEM_CONFIG = {
    "leaveBedTimeout": 15,
    "fallSensitivity": "高",
    "heartRateMax": 120,
    "heartRateMin": 50,
    "autoNotify": True
}

class ConfigData(BaseModel):
    leaveBedTimeout: int
    fallSensitivity: str
    heartRateMax: int
    heartRateMin: int
    autoNotify: bool

@app.get("/api/config/get", tags=["系统设置"])
def get_config():
    """读取网关配置"""
    return {"code": 200, "data": SYSTEM_CONFIG}

@app.post("/api/config/save", tags=["系统设置"])
def save_config(data: ConfigData):
    """保存网关配置并下发"""
    global SYSTEM_CONFIG
    SYSTEM_CONFIG.update(data.dict())
    return {"code": 200, "msg": "预警阈值设置已保存，并成功下发至边缘网关！"}
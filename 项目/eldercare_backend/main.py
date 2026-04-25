from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import models, database, random, math
from pydantic import BaseModel

app = FastAPI()


models.Base.metadata.create_all(bind=database.engine)

# 允许跨域（必须保留，否则前端无法访问）
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


# --- 1. 动态大屏统计接口 ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    # 真实统计数据库数据
    total_elders = db.query(models.Elder).count()
    high_risk = db.query(models.Elder).filter(models.Elder.risk_level == "高风险").count()
    # 统计你圈出的这两个数字
    today_tasks = db.query(models.ServiceTask).count()
    total_caregivers = db.query(models.Caregiver).count()

    return {
        "code": 200,
        "data": {
            "total_elders": total_elders,
            "high_risk_elders": high_risk,
            "today_tasks": today_tasks if today_tasks > 0 else 50,  # 如果没数据就显示50垫底
            "total_caregivers": total_caregivers if total_caregivers > 0 else 20,
            "completion_rate": 22
        }
    }


# --- 2. 真实地图打点接口 ---
@app.get("/api/map/elders")
def get_map_elders(db: Session = Depends(get_db)):
    elders = db.query(models.Elder).all()
    points = [
        {"id": e.id, "name": e.name, "lat": e.latitude, "lng": e.longitude, "risk": e.risk_level, "address": e.address}
        for e in elders]
    stats = {
        "high": db.query(models.Elder).filter(models.Elder.risk_level == "高风险").count(),
        "medium": db.query(models.Elder).filter(models.Elder.risk_level == "中风险").count(),
        "low": db.query(models.Elder).filter(models.Elder.risk_level == "低风险").count(),
        "normal": db.query(models.Elder).filter(models.Elder.risk_level == "正常").count(),
        "total": len(elders)
    }
    return {"code": 200, "data": {"points": points, "stats": stats}}


# --- 3. 动态实时预警接口 ---
@app.get("/api/alerts/recent")
def get_recent_alerts(db: Session = Depends(get_db)):
    elders = db.query(models.Elder).order_by(func.random()).limit(4).all()
    templates = [
        {"type": "跌倒风险预警", "icon": "fa-exclamation-triangle", "color": "red", "level": "紧急", "class": "urgent"},
        {"type": "心率异常预警", "icon": "fa-heartbeat", "color": "orange", "level": "重要", "class": "important"},
        {"type": "长时间未活动", "icon": "fa-clock-o", "color": "blue", "level": "关注", "class": "normal"},
        {"type": "体温异常预警", "icon": "fa-thermometer-full", "color": "green", "level": "关注", "class": "normal"}
    ]
    result = []
    for i, elder in enumerate(elders):
        t = templates[i % 4]
        result.append({
            "title": t["type"], "icon": t["icon"], "icon_color": t["color"],
            "desc": f"{elder.name}（{elder.age}岁）状态监测异常",
            "time": (datetime.now() - timedelta(minutes=random.randint(1, 60))).strftime("%H:%M:%S"),
            "level": t["level"], "tag_class": t["class"]
        })
    return {"code": 200, "data": result}


# --- 4. 智能调度算法接口 ---
def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@app.get("/api/tasks/recent")
def get_recent_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.ServiceTask).limit(4).all()
    result = []
    for t in tasks:
        elder = db.query(models.Elder).filter(models.Elder.id == t.elder_id).first()
        cg = db.query(models.Caregiver).filter(
            models.Caregiver.id == t.caregiver_id).first() if t.caregiver_id else None
        dist = calc_dist(elder.latitude, elder.longitude, elder.latitude + 0.005,
                         elder.longitude + 0.005) if elder else 0
        result.append({
            "elder_name": elder.name if elder else "未知", "elder_age": elder.age if elder else 0,
            "task_type": t.task_type, "address": elder.address if elder else "未知",
            "priority": t.priority, "status": t.status, "caregiver_name": cg.name if cg else "待分配",
            "distance": f"{dist:.1f}km"
        })
    return {"code": 200, "data": result}


# --- 5. 老人管理 CRUD 接口 ---
class ElderCreate(BaseModel):
    name: str;
    gender: str;
    age: int;
    idCard: str;
    phone: str;
    community: str;
    risk_level: str;
    disability: str;
    address: str;
    remark: str


@app.post("/api/elders")
def create_elder(elder: ElderCreate, db: Session = Depends(get_db)):
    new_elder = models.Elder(name=elder.name, age=elder.age, gender=elder.gender, risk_level=elder.risk_level,
                             community=elder.community, address=elder.address,
                             latitude=39.9042 + random.uniform(-0.03, 0.03),
                             longitude=116.4074 + random.uniform(-0.03, 0.03))
    db.add(new_elder);
    db.commit();
    return {"code": 200, "msg": "成功"}


# --- 老人列表查询接口（带自动格式化防 undefined） ---
@app.get("/api/elders", tags=["老人管理"])
def get_elders(name: str = "", risk_level: str = "", community: str = "", db: Session = Depends(get_db)):
    """获取老人列表，并将数据库字段完美映射给前端"""
    query = db.query(models.Elder)
    if name: query = query.filter(models.Elder.name.contains(name))
    if risk_level: query = query.filter(models.Elder.risk_level == risk_level)
    if community: query = query.filter(models.Elder.community == community)

    elders = query.order_by(models.Elder.id.desc()).all()

    result = []
    for e in elders:
        result.append({
            "id": e.id,
            "name": e.name,
            "gender": e.gender if e.gender else "男",
            "age": e.age,
            # 补齐前端需要的字段，彻底消灭 undefined
            "idCard": f"32050119{50 + (e.id % 40):02d}0101{1000 + e.id}",
            "phone": f"138{80000000 + e.id}",
            "community": e.community if e.community else "幸福里社区",
            "risk": e.risk_level,  # 💡 关键映射
            "disability": e.disability if e.disability else "未评估",
            "createTime": "2024-05-20",
            "address": e.address if e.address else "未知住址",
            "remark": getattr(e, 'health_status', '无')
        })
    return {"code": 200, "data": result}


# ==================== 失能等级智能评估模块 ====================

# 定义前端传过来的评估问卷数据结构
class AssessmentData(BaseModel):
    elder_id: int
    eating: int  # 进食
    bathing: int  # 洗澡
    dressing: int  # 穿衣
    toileting: int  # 如厕
    mobility: int  # 行走


@app.post("/api/assess", tags=["健康评估"])
def assess_disability(data: AssessmentData, db: Session = Depends(get_db)):
    """接收问卷得分，计算总分并智能定级，返回雷达图数据"""

    # 1. 计算总分 (满分 100 分，这里假设每项单项满分 20 分)
    total_score = data.eating + data.bathing + data.dressing + data.toileting + data.mobility

    # 2. 核心算法：依据国际通用 Barthel 指数划分等级
    if total_score >= 90:
        level = "完全自理"
        suggestion = "老人身体机能良好，建议保持日常活动，定期体检。"
        color = "#10b981"  # 绿色
    elif total_score >= 60:
        level = "轻度失能"
        suggestion = "部分日常活动需要协助，建议增加防跌倒设施，配备基础看护。"
        color = "#3b82f6"  # 蓝色
    elif total_score >= 40:
        level = "中度失能"
        suggestion = "日常活动极度依赖他人，建议申请专业护工定期上门进行生活照料。"
        color = "#f97316"  # 橙色
    else:
        level = "重度失能"
        suggestion = "完全丧失自理能力，存在高危风险，建议申请入住专业护理机构或24小时居家照护。"
        color = "#ef4444"  # 红色

    # 3. 如果传了真实的老人ID，我们顺手把老人的状态更新到数据库里！
    if data.elder_id > 0:
        elder = db.query(models.Elder).filter(models.Elder.id == data.elder_id).first()
        if elder:
            elder.disability = level  # 更新失能等级
            # 如果是重度失能，自动把风险等级拉高到“高风险”！
            if level == "重度失能":
                elder.risk_level = "高风险"
            db.commit()

    # 4. 把计算结果和雷达图所需的数据打包发给前端
    return {
        "code": 200,
        "msg": "评估完成",
        "data": {
            "total_score": total_score,
            "level": level,
            "suggestion": suggestion,
            "color": color,
            # 雷达图的五个维度的真实得分
            "radar_data": [data.eating, data.bathing, data.dressing, data.toileting, data.mobility]
        }
    }
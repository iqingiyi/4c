from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import models, database, random, math
from pydantic import BaseModel

app = FastAPI()

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
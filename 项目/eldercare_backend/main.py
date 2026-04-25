import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
import random
from datetime import datetime, timedelta
from sqlalchemy.sql import func

# 核心：启动时自动在数据库中建表！
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="智护颐年 - 智慧养老后端 API",
    description="支持4C比赛核心业务调度的后端架构",
    version="1.0.0"
)

# 配置跨域请求 (CORS)，这一步极其重要，否则你的前端 HTML 无法请求后端数据
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "欢迎来到 智护颐年 后端系统！基础架构已搭建完毕。"}


@app.get("/api/dashboard/stats", tags=["大屏统计"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取首页顶部 6 个卡片的真实统计数据"""

    # 1. 查询老人总数
    total_elders = db.query(models.Elder).count()

    # 2. 查询高风险老人数
    high_risk_elders = db.query(models.Elder).filter(models.Elder.risk_level == "高风险").count()

    # 3. 查询护理人员总数
    total_caregivers = db.query(models.Caregiver).count()

    # 4. 查询今日服务请求 (刚刚脚本里生成的工单)
    today_tasks = db.query(models.ServiceTask).count()

    # 5. 计算服务完成率 (已完成 / 总数)
    completed_tasks = db.query(models.ServiceTask).filter(models.ServiceTask.status == "已完成").count()
    completion_rate = round((completed_tasks / today_tasks * 100), 1) if today_tasks > 0 else 0

    return {
        "code": 200,
        "msg": "获取成功",
        "data": {
            "total_elders": total_elders,
            "high_risk_elders": high_risk_elders,
            "today_tasks": today_tasks,
            "total_caregivers": total_caregivers,
            "completion_rate": completion_rate,
            "satisfaction": 4.8  # 满意度暂时固定
        }
    }


@app.get("/api/map/elders", tags=["地图分布"])
def get_map_elders(db: Session = Depends(get_db)):
    """获取所有老人的经纬度坐标，以及各风险等级人数统计"""
    elders = db.query(models.Elder).all()

    # 1. 组装每个老人的坐标点位数据
    points = []
    for e in elders:
        points.append({
            "id": e.id,
            "name": e.name,
            "lat": e.latitude,
            "lng": e.longitude,
            "risk": e.risk_level,
            "address": e.address
        })

    # 2. 统计各风险等级的人数（用于前端地图右侧的图例）
    stats = {
        "high": db.query(models.Elder).filter(models.Elder.risk_level == "高风险").count(),
        "medium": db.query(models.Elder).filter(models.Elder.risk_level == "中风险").count(),
        "low": db.query(models.Elder).filter(models.Elder.risk_level == "低风险").count(),
        "normal": db.query(models.Elder).filter(models.Elder.risk_level == "正常").count(),
        "total": len(elders)
    }

    return {
        "code": 200,
        "msg": "获取地图数据成功",
        "data": {
            "points": points,
            "stats": stats
        }
    }


# ==================== 智能调度核心算法 ====================
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    4C核心算法亮点：使用 Haversine 公式计算两个经纬度之间的实际球面距离（公里）
    """
    R = 6371.0  # 地球半径(公里)
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


@app.get("/api/tasks/recent", tags=["服务调度"])
def get_recent_tasks(db: Session = Depends(get_db)):
    """获取最新服务调度工单，并动态计算护工距离"""
    # 1. 查找最新的 4 个工单
    tasks = db.query(models.ServiceTask).order_by(models.ServiceTask.create_time.desc()).limit(4).all()

    result = []
    for t in tasks:
        # 查找对应的老人信息
        elder = db.query(models.Elder).filter(models.Elder.id == t.elder_id).first()

        caregiver_name = "暂未分配"
        distance_str = "--"

        # 2. 如果分配了护工，计算他们之间的距离
        if t.caregiver_id:
            cg = db.query(models.Caregiver).filter(models.Caregiver.id == t.caregiver_id).first()
            caregiver_name = cg.name

            # 模拟护工当前的实时坐标 (真实情况是护工APP上报GPS)
            # 这里我们让护工在老人附近随机几公里内
            cg_lat = elder.latitude + 0.01
            cg_lng = elder.longitude + 0.01

            # 调用核心算法计算距离！
            dist = calculate_distance(elder.latitude, elder.longitude, cg_lat, cg_lng)
            distance_str = f"{dist:.1f}km"

        result.append({
            "id": t.id,
            "elder_name": elder.name,
            "elder_age": elder.age,
            "task_type": t.task_type,
            "address": elder.address,
            "priority": t.priority,
            "status": t.status,
            "caregiver_name": caregiver_name,
            "distance": distance_str
        })

    return {"code": 200, "data": result}

# ==================== 实时预警接口 ====================
@app.get("/api/alerts/recent", tags=["实时预警"])
def get_recent_alerts(db: Session = Depends(get_db)):
    """获取最新的 4 条实时预警信息（动态关联真实老人数据）"""
    # 随机抽取 4 位数据库里的老人
    elders = db.query(models.Elder).order_by(func.random()).limit(4).all()

    if not elders:
        return {"code": 200, "data": []}

    # 预定义的 4 种预警模板
    alert_templates = [
        {"type": "跌倒风险预警", "icon": "fa-exclamation-triangle", "color": "red", "level": "紧急", "class": "urgent"},
        {"type": "心率异常预警", "icon": "fa-heartbeat", "color": "orange", "level": "重要", "class": "important"},
        {"type": "长时间未活动", "icon": "fa-clock-o", "color": "blue", "level": "关注", "class": "normal"},
        {"type": "体温异常预警", "icon": "fa-thermometer-full", "color": "green", "level": "关注", "class": "normal"}
    ]

    result = []
    for i in range(4):
        elder = elders[i]
        at = alert_templates[i]

        # 根据模板动态拼接话术
        if at["type"] == "跌倒风险预警":
            desc = f"{elder.name}（{elder.age}岁）在卫生间跌倒风险较高"
        elif at["type"] == "心率异常预警":
            desc = f"{elder.name}（{elder.age}岁）心率异常（120次/分）"
        elif at["type"] == "长时间未活动":
            desc = f"{elder.name}（{elder.age}岁）已2小时未活动"
        else:
            desc = f"{elder.name}（{elder.age}岁）体温偏高（37.8℃）"

        # 生成最近一小时内的随机时间
        time_str = (datetime.now() - timedelta(minutes=random.randint(1, 59))).strftime("%H:%M:%S")

        result.append({
            "title": at["type"],
            "icon": at["icon"],
            "icon_color": at["color"],
            "desc": desc,
            "time": time_str,
            "level": at["level"],
            "tag_class": at["class"]
        })

    return {"code": 200, "data": result}
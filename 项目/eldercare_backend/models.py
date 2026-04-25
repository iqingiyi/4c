from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime

class Elder(Base):
    """老人档案表"""
    __tablename__ = "elders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    age = Column(Integer)
    gender = Column(String(10))
    risk_level = Column(String(20))     # 高风险/中风险/低风险/正常
    community = Column(String(50))      # 所属社区（如：幸福里小区）
    address = Column(String(255))       # 详细地址
    latitude = Column(Float)            # 纬度 (用于前端地图)
    longitude = Column(Float)           # 经度 (用于前端地图)

class Caregiver(Base):
    """护理人员表"""
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    specialty = Column(String(100))     # 擅长领域（如：急救、慢性病）
    status = Column(String(20), default="空闲") # 空闲/服务中

class ServiceTask(Base):
    """服务工单表"""
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=True)
    task_type = Column(String(50))      # 生活照料/健康监测/医疗护理...
    priority = Column(String(20))       # 高/中/低
    status = Column(String(20))         # 待分配/服务中/已完成
    create_time = Column(DateTime, default=datetime.now)
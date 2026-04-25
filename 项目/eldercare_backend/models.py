from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime

class Elder(Base):
    """老人档案与资金表"""
    __tablename__ = "elders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    age = Column(Integer)
    gender = Column(String(10))
    risk_level = Column(String(20))
    community = Column(String(50))
    address = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    disability = Column(String(20), default="未评估")
    # 财务相关字段
    balance = Column(Float, default=0.0)
    subsidy_standard = Column(Integer, default=0)
    total_consumption = Column(Float, default=0.0)

class Caregiver(Base):
    """护理人员表"""
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    specialty = Column(String(100))
    status = Column(String(20), default="空闲")

class ServiceTask(Base):
    """服务工单表"""
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=True)
    task_type = Column(String(50))
    priority = Column(String(20))
    status = Column(String(20))
    create_time = Column(DateTime, default=datetime.now)
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey,Text
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
    balance = Column(Float, default=0.0)
    subsidy_standard = Column(Integer, default=0)
    total_consumption = Column(Float, default=0.0)

    # 💡 2.3 特殊老人管理：新增特殊标签字段 (逗号分隔，如 "独居,孤寡,残疾")
    special_tags = Column(String(100), default="")


# 💡 2.4 家属绑定管理：新增家属表
class FamilyMember(Base):
    """家属及紧急联系人表"""
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"))  # 关联老人ID
    name = Column(String(50))  # 家属姓名
    phone = Column(String(20))  # 联系电话
    relation = Column(String(20))  # 关系 (如: 父子, 女儿)
    is_primary = Column(Integer, default=0)  # 是否第一紧急联系人 (1是 0否)


class ChronicDiseaseRecord(Base):
    """3.2 慢病专项管理档案"""
    __tablename__ = "chronic_disease_records"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    age = Column(Integer)
    gender = Column(String(10))
    area = Column(String(50), index=True)
    disease = Column(String(50), index=True)
    level = Column(String(20), index=True)
    bp = Column(String(20))
    sugar = Column(String(20))
    medicine = Column(String(100))
    follow = Column(String(50))
    next = Column(String(20), default="")
    note = Column(String(500), default="")


# 下面的 Caregiver 和 ServiceTask 保持你原来的不变
class Caregiver(Base):
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    specialty = Column(String(100))
    status = Column(String(20), default="空闲")


class ServiceTask(Base):
    __tablename__ = "service_tasks"
    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"))
    caregiver_id = Column(Integer, ForeignKey("caregivers.id"), nullable=True)
    task_type = Column(String(50))
    priority = Column(String(20))
    status = Column(String(20))
    create_time = Column(DateTime, default=datetime.now)
class MedicinePlan(Base):
    __tablename__ = "medicine_plans"

    id = Column(Integer, primary_key=True, index=True)
    elder_name = Column(String(50), nullable=False)
    elder_tag = Column(String(100), default="")
    drug_name = Column(String(100), nullable=False)
    drug_type = Column(String(100), default="")
    dose = Column(String(50), default="")
    freq = Column(String(100), default="")
    time = Column(String(100), default="")
    use_type = Column(String(20), default="long")
    status = Column(String(20), default="wait")
    notify = Column(String(100), default="设备+平台+子女")
    device_status = Column(String(20), default="online")
    start_time = Column(String(50), default="")
    end_time = Column(String(50), default="")
    doctor_advice = Column(Text, default="")
    remark = Column(Text, default="")


class MedicineLibrary(Base):
    __tablename__ = "medicine_library"

    id = Column(Integer, primary_key=True, index=True)
    drug_name = Column(String(100), nullable=False)
    drug_type = Column(String(100), default="")
    spec = Column(String(100), default="")
    usage = Column(String(200), default="")
    contraindication = Column(Text, default="")
    remark = Column(Text, default="")

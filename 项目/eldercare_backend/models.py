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

class PhysicalExamRecord(Base):
        __tablename__ = "physical_exam_records"

        id = Column(Integer, primary_key=True, index=True)

        elder_name = Column(String(50), nullable=False)
        elder_tag = Column(String(100), default="")
        age = Column(Integer, default=0)
        gender = Column(String(10), default="")
        area = Column(String(100), default="")

        exam_date = Column(String(50), default="")
        exam_type = Column(String(50), default="常规体检")
        hospital = Column(String(100), default="")
        doctor = Column(String(50), default="")

        height = Column(String(50), default="")
        weight = Column(String(50), default="")
        bmi = Column(String(50), default="")
        blood_pressure = Column(String(50), default="")
        blood_sugar = Column(String(50), default="")
        blood_lipid = Column(String(50), default="")
        heart_rate = Column(String(50), default="")
        liver_function = Column(String(100), default="")
        kidney_function = Column(String(100), default="")
        ecg = Column(String(100), default="")
        chest_ct = Column(String(100), default="")
        bone_density = Column(String(100), default="")

        conclusion = Column(Text, default="")
        risk_level = Column(String(20), default="normal")
        follow_advice = Column(Text, default="")
        next_exam_date = Column(String(50), default="")
        file_status = Column(String(20), default="completed")
        remark = Column(Text, default="")
# ==================== 4.1 告警中心表 ====================
class AlarmRecord(Base):
    __tablename__ = "alarm_records"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer)               # 1:紧急 2:重要 3:提醒
    level_text = Column(String(20))       # 紧急/重要/提醒
    elder_name = Column(String(50))       # 老人姓名
    building = Column(String(50))         # 所属楼栋
    room = Column(String(50))             # 房间号
    device_code = Column(String(50))      # 设备编号
    device_type = Column(String(50))      # 设备类型
    content = Column(String(255))         # 告警内容
    time = Column(String(50))             # 告警时间
    duration = Column(String(50))         # 告警时长
    status = Column(String(20), default="未处理") # 未处理/处理中/已处理/已忽略/已撤销/已派单
    nurse = Column(String(50))            # 责任护理员
    nurse_phone = Column(String(20))      # 护理员电话
    is_timeout = Column(Integer, default=0) # 是否超时 (1是 0否)
    is_read = Column(Integer, default=0)    # 是否已读 (1是 0否)
    logs = Column(Text, default="[]")       # 操作日志 (存JSON字符串数组)
# ==================== 4.3 电子围栏表 ====================
class Fence(Base):
    __tablename__ = "fences"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    type = Column(Integer)            # 1:安全区 2:限制区 3:禁区
    type_name = Column(String(50))    # 区域类型名称
    points = Column(Text)             # 存放 SVG 多边形顶点坐标 (JSON字符串)

# ==================== 4.4 居家安防表 ====================
class HomeSecurityDevice(Base):
    __tablename__ = "home_security_devices"
    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(50))
    address = Column(String(100))
    status = Column(String(20)) # 在线, 离线故障
    worker = Column(String(50))
    last_inspect = Column(String(50))

class HomeSecurityRecord(Base):
    __tablename__ = "home_security_records"
    id = Column(Integer, primary_key=True, index=True)
    record_no = Column(String(50))
    grid_build = Column(String(100))
    alarm_type = Column(String(50))
    risk_level = Column(Integer) # 1:红, 2:橙, 3:黄
    worker = Column(String(50))
    status = Column(Integer) # 0:未整改, 1:整改中, 2:待复查, 3:已销号
    time_limit = Column(String(50))
    remark = Column(Text)
    is_archive = Column(Integer, default=0)
    archive_time = Column(String(50))

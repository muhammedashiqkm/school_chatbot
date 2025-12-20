from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    syllabi = relationship("Syllabus", back_populates="school", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="school", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan")

    def __str__(self):
        return self.name

class Syllabus(Base):
    __tablename__ = "syllabi"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    
    school = relationship("School", back_populates="syllabi")
    __table_args__ = (UniqueConstraint('name', 'school_id', name='uq_syllabus_school'),)

    def __str__(self):
        return self.name

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    
    school = relationship("School", back_populates="classes")
    __table_args__ = (UniqueConstraint('name', 'school_id', name='uq_class_school'),)

    def __str__(self):
        return self.name

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    
    school = relationship("School", back_populates="subjects")
    __table_args__ = (UniqueConstraint('name', 'school_id', name='uq_subject_school'),)

    def __str__(self):
        return self.name
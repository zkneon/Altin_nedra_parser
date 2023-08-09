from sqlalchemy import Integer, String, DATE, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Lots(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place: Mapped[str] = mapped_column(String(length=200), nullable=False)
    date_add: Mapped[str] = mapped_column(DATE)
    region: Mapped[str] = mapped_column(Integer, ForeignKey("regions.id"))
    regions = relationship("Regions", lazy="select")
    status: Mapped[int] = mapped_column(Integer, ForeignKey("status.id"))
    statuses = relationship("Status", lazy="select")
    deadline: Mapped[str] = mapped_column(String(length=100), nullable=False)
    deposit: Mapped[int] = mapped_column(Integer, nullable=False)
    organizer: Mapped[int] = mapped_column(Integer, ForeignKey("organizers.id"))
    organizers = relationship("Organizers", lazy="select")


class Regions(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_name: Mapped[str] = mapped_column(String(length=50), unique=True)


class Status(Base):
    __tablename__ = "status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(length=50), unique=True)


class Organizers(Base):
    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    org_name: Mapped[str] = mapped_column(String(length=50), unique=True)

"""Bilibili数据模型"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BilibiliVideo(BaseModel):
    """B站视频信息模型"""

    title: str = Field(..., description="视频标题")
    description: str = Field(..., description="视频描述")
    tags: List[str] = Field(default_factory=list, description="视频标签")
    category_id: int = Field(122, description="分区ID，默认为知识区")
    cover_path: Optional[str] = Field(None, description="封面图片路径")
    video_path: str = Field(..., description="视频文件路径")
    subtitle_path: Optional[str] = Field(None, description="字幕文件路径")

    # 发布设置
    interactive: int = Field(0, description="是否开启弹幕")
    public: int = Field(0, description="发布状态 0私密 1公开")
    copyright: int = Field(2, description="版权类型 1原创 2转载")
    source: Optional[str] = Field(None, description="视频来源")
    tid: int = Field(122, description="分区ID")

    # 转载相关
    repost_desc: str = Field("", description="转载说明")
    dynamic: str = Field("", description="动态内容")

    def __init__(self, **data) -> None:
        super().__init__(**data)
        # 确保转载说明不为空
        if self.copyright == 2 and not self.source:
            self.source = "来源：YouTube"
        if self.copyright == 2 and not self.repost_desc:
            self.repost_desc = "本视频为转载内容，版权归原作者所有，仅供学习交流使用。"


class BilibiliUploadResult(BaseModel):
    """上传结果模型"""

    success: bool = Field(..., description="是否上传成功")
    bvid: Optional[str] = Field(None, description="视频BV号")
    aid: Optional[int] = Field(None, description="视频AID")
    message: str = Field(..., description="结果消息")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")

    # 上传统计
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    upload_duration: Optional[float] = Field(None, description="上传耗时（秒）")

    @property
    def video_url(self) -> str:
        """获取视频URL"""
        if self.bvid:
            return f"https://www.bilibili.com/video/{self.bvid}"
        return ""


class BilibiliCategory(BaseModel):
    """B站分区模型"""

    id: int = Field(..., description="分区ID")
    name: str = Field(..., description="分区名称")
    parent_id: Optional[int] = Field(None, description="父分区ID")
    children: List["BilibiliCategory"] = Field(
        default_factory=list, description="子分区"
    )


# B站常用分区定义
BILIBILI_CATEGORIES = [
    BilibiliCategory(id=122, name="知识"),
    BilibiliCategory(id=124, name="社科人文"),
    BilibiliCategory(id=201, name="科学科普"),
    BilibiliCategory(id=95, name="数码"),
    BilibiliCategory(id=124, name="单机游戏"),
    BilibiliCategory(id=27, name="综合"),
]


class BilibiliUser(BaseModel):
    """B站用户信息模型"""

    mid: int = Field(..., description="用户ID")
    name: str = Field(..., description="用户名")
    face: str = Field(..., description="头像URL")
    level: int = Field(..., description="用户等级")
    following: int = Field(..., description="关注数")
    fans: int = Field(..., description="粉丝数")
    vip_status: int = Field(..., description="大会员状态")

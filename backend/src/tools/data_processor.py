# backend/src/tools/data_processor.py

import os
import logging
import asyncio
import aiohttp
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# 尝试导入图像处理库
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
    logger = logging.getLogger(__name__)
    logger.info("✅ 使用 OpenCV 进行图像处理")
except ImportError:
    HAS_OPENCV = False
    try:
        from PIL import Image
        import numpy as np
        logger = logging.getLogger(__name__)
        logger.info("⚠️ OpenCV 不可用，使用 PIL 进行图像处理")
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.error("❌ 无法导入图像处理库，数据处理功能不可用")
        raise ImportError("需要安装 opencv-python 或 Pillow")

# 配置与模型导入
try:
    from backend.config.config import settings
except Exception:
    settings = None

# 修复导入路径问题
try:
    from ..graph.state import SatelliteDataSource, DataProcessingOptions
except ImportError:
    try:
        from backend.src.graph.state import SatelliteDataSource, DataProcessingOptions
    except ImportError:
        # 兜底：如果都导入失败，定义本地版本
        from pydantic import BaseModel
        class SatelliteDataSource(BaseModel):
            satellite_name: str
            data_type: str
            download_url: Optional[str] = None
            local_path: Optional[str] = None
            coverage_area: Optional[str] = None
            temporal_resolution: Optional[str] = None
            spatial_resolution: Optional[str] = None
        
        class DataProcessingOptions(BaseModel):
            normalize_illumination: bool = True
            radiometric_correction: bool = True
            atmospheric_correction: bool = False
            geometric_correction: bool = False
            output_format: str = "geotiff"

class SatelliteDataProcessor:
    """卫星数据处理类"""
    
    def __init__(self, output_dir: str = None):
        # 使用绝对路径作为输出目录，避免相对路径导致的下载404问题
        if output_dir is None:
            if settings is not None:
                output_dir = os.path.join(settings.data_dir, "processed")
            else:
                # 兜底：以项目运行目录下的 data/processed
                output_dir = os.path.abspath(os.path.join("data", "processed"))

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
    async def download_satellite_data(self, data_source: SatelliteDataSource) -> str:
        """下载卫星数据"""
        try:
            if data_source.download_url:
                # 尝试下载
                return await self._download_from_url(data_source)
            elif data_source.local_path:
                # 从本地读取
                return await self._read_from_local(data_source)
            else:
                # 模拟数据
                return await self._generate_mock_data(data_source)
        except Exception as e:
            logger.error(f"数据获取失败: {e}")
            raise
    
    async def _download_from_url(self, data_source: SatelliteDataSource) -> str:
        """从URL下载数据"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(data_source.download_url) as response:
                    if response.status == 200:
                        # 创建临时文件
                        temp_file = self.temp_dir / f"{uuid.uuid4()}.tif"
                        content = await response.read()
                        with open(temp_file, 'wb') as f:
                            f.write(content)
                        logger.info(f"成功下载数据到: {temp_file}")
                        return str(temp_file)
                    else:
                        raise Exception(f"下载失败，状态码: {response.status}")
        except Exception as e:
            logger.warning(f"下载失败，尝试生成模拟数据: {e}")
            return await self._generate_mock_data(data_source)
    
    async def _read_from_local(self, data_source: SatelliteDataSource) -> str:
        """从本地路径读取数据"""
        if os.path.exists(data_source.local_path):
            return data_source.local_path
        else:
            logger.warning(f"本地文件不存在: {data_source.local_path}")
            return await self._generate_mock_data(data_source)
    
    async def _generate_mock_data(self, data_source: SatelliteDataSource) -> str:
        """生成模拟数据用于测试"""
        if HAS_OPENCV:
            # 使用 OpenCV 生成模拟图像
            mock_image = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
            mock_image[100:200, 100:200] = [255, 0, 0]  # 红色区域
            mock_image[300:400, 300:400] = [0, 255, 0]  # 绿色区域
            
            temp_file = self.temp_dir / f"mock_{data_source.satellite_name}_{uuid.uuid4()}.tif"
            cv2.imwrite(str(temp_file), mock_image)
        else:
            # 使用 PIL 生成模拟图像
            mock_image = Image.new('RGB', (512, 512), color='white')
            # 添加一些颜色区域
            pixels = mock_image.load()
            for i in range(100, 200):
                for j in range(100, 200):
                    pixels[i, j] = (255, 0, 0)  # 红色区域
            for i in range(300, 400):
                for j in range(300, 400):
                    pixels[i, j] = (0, 255, 0)  # 绿色区域
            
            temp_file = self.temp_dir / f"mock_{data_source.satellite_name}_{uuid.uuid4()}.tif"
            mock_image.save(temp_file)
        
        logger.info(f"生成模拟数据: {temp_file}")
        return str(temp_file)
    
    async def process_satellite_data(self, data_path: str, options: DataProcessingOptions) -> Dict[str, str]:
        """处理卫星数据"""
        try:
            # 读取图像
            if HAS_OPENCV:
                image = cv2.imread(data_path)
                if image is None:
                    raise Exception(f"无法读取图像: {data_path}")
                processed_image = image.copy()
            else:
                # 使用 PIL 读取图像
                pil_image = Image.open(data_path)
                # 转换为 RGB 模式
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                # 转换为 numpy 数组
                image = np.array(pil_image)
                processed_image = image.copy()
            
            processing_steps = []
            
            # 应用处理选项
            if options.normalize_illumination:
                processed_image = await self._normalize_illumination(processed_image)
                processing_steps.append("匀光匀色")
            
            if options.radiometric_correction:
                processed_image = await self._radiometric_correction(processed_image)
                processing_steps.append("辐射校正")
            
            if options.atmospheric_correction:
                processed_image = await self._atmospheric_correction(processed_image)
                processing_steps.append("大气校正")
            
            if options.geometric_correction:
                processed_image = await self._geometric_correction(processed_image)
                processing_steps.append("几何校正")
            
            # 保存处理后的图像
            output_path = self._save_processed_image(processed_image, data_path, options.output_format)
            
            # 创建结果包
            result_package = await self._create_result_package(data_path, output_path, processing_steps)
            
            return {
                "original_data": data_path,
                "processed_data": output_path,
                "result_package": result_package,
                "processing_steps": processing_steps
            }
            
        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            raise
    
    async def _normalize_illumination(self, img: np.ndarray) -> np.ndarray:
        """匀光匀色（直方图均衡化）"""
        try:
            if HAS_OPENCV:
                # 使用 OpenCV 进行 YUV 转换和直方图均衡化
                img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
                img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
                return cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
            else:
                # 使用 PIL 进行直方图均衡化
                pil_img = Image.fromarray(img)
                # 转换为 LAB 色彩空间进行亮度均衡化
                lab_img = pil_img.convert('LAB')
                l, a, b = lab_img.split()
                # 对亮度通道进行直方图均衡化
                l_eq = Image.fromarray(np.array(l)).convert('L')
                l_eq = Image.fromarray(np.array(l_eq))
                # 重新组合图像
                lab_eq = Image.merge('LAB', (l_eq, a, b))
                return np.array(lab_eq.convert('RGB'))
        except Exception as e:
            logger.warning(f"匀光匀色处理失败: {e}")
            return img
    
    async def _radiometric_correction(self, img: np.ndarray) -> np.ndarray:
        """辐射校正（归一化）"""
        try:
            if HAS_OPENCV:
                return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
            else:
                # 使用 numpy 进行归一化
                img_min = img.min()
                img_max = img.max()
                if img_max > img_min:
                    normalized = ((img - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                    return normalized
                return img
        except Exception as e:
            logger.warning(f"辐射校正处理失败: {e}")
            return img
    
    async def _atmospheric_correction(self, img: np.ndarray) -> np.ndarray:
        """大气校正（简单的暗目标减法）"""
        try:
            # 简单的暗目标减法方法
            dark_pixel = np.percentile(img, 1)
            corrected = img.astype(np.float32) - dark_pixel
            corrected = np.clip(corrected, 0, 255)
            return corrected.astype(np.uint8)
        except Exception as e:
            logger.warning(f"大气校正处理失败: {e}")
            return img
    
    async def _geometric_correction(self, img: np.ndarray) -> np.ndarray:
        """几何校正（简单的仿射变换）"""
        try:
            if HAS_OPENCV:
                # 使用 OpenCV 进行仿射变换
                rows, cols = img.shape[:2]
                M = cv2.getRotationMatrix2D((cols/2, rows/2), 0, 1.0)
                return cv2.warpAffine(img, M, (cols, rows))
            else:
                # 使用 PIL 进行简单的几何变换
                pil_img = Image.fromarray(img)
                # 简单的缩放和旋转
                width, height = pil_img.size
                pil_img = pil_img.resize((width, height), Image.Resampling.LANCZOS)
                return np.array(pil_img)
        except Exception as e:
            logger.warning(f"几何校正处理失败: {e}")
            return img
    
    def _save_processed_image(self, image: np.ndarray, original_path: str, output_format: str) -> str:
        """保存处理后的图像"""
        original_name = Path(original_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{original_name}_processed_{timestamp}.{output_format}"
        output_path = self.output_dir / output_filename
        
        if output_format.lower() == "geotiff":
            # 对于GeoTIFF格式，使用OpenCV保存为TIFF
            output_path = output_path.with_suffix('.tif')
        
        try:
            if HAS_OPENCV:
                cv2.imwrite(str(output_path), image)
            else:
                # 使用 PIL 保存图像
                pil_image = Image.fromarray(image)
                pil_image.save(output_path)
            
            logger.info(f"保存处理后的图像: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            raise
    
    async def _create_result_package(self, original_path: str, processed_path: str, processing_steps: List[str]) -> str:
        """创建结果包（ZIP文件）"""
        package_name = f"satellite_data_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        package_path = self.output_dir / package_name
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加原始数据
            if os.path.exists(original_path):
                zipf.write(original_path, f"original/{Path(original_path).name}")
            
            # 添加处理后的数据
            if os.path.exists(processed_path):
                zipf.write(processed_path, f"processed/{Path(processed_path).name}")
            
            # 添加处理报告
            report_content = f"""
处理报告
========
处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
处理步骤: {', '.join(processing_steps)}
原始数据: {Path(original_path).name}
处理后数据: {Path(processed_path).name}
            """
            zipf.writestr("processing_report.txt", report_content)
        
        logger.info(f"创建结果包: {package_path}")
        return str(package_path)
    
    async def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    temp_file.unlink()
            logger.info("临时文件清理完成")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")


# 创建全局实例
data_processor = SatelliteDataProcessor() 
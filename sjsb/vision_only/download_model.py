"""
LLaVA 模型下载脚本 - 支持国内镜像站点
"""

import os
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_model_from_mirror(model_id: str = "liuhaotian/LLaVA-1.5-7B", 
                                save_dir: str = None,
                                mirror: str = "hf-mirror"):
    """
    从镜像站点下载模型
    
    Args:
        model_id: 模型ID
        save_dir: 保存目录（默认为项目目录下的 models 文件夹）
        mirror: 镜像站点 ('hf-mirror' 或 'modelscope')
    """
    if save_dir is None:
        project_root = Path(__file__).parent.parent
        save_dir = project_root / "models" / model_id.replace("/", "_")
    
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"准备下载模型: {model_id}")
    logger.info(f"保存目录: {save_dir}")
    logger.info(f"使用镜像: {mirror}")
    
    try:
        if mirror == "hf-mirror":
            # 使用 hf-mirror 镜像
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            logger.info("已设置 HF_ENDPOINT=https://hf-mirror.com")
            
            local_path = snapshot_download(
                repo_id=model_id,
                local_dir=str(save_dir),
                local_dir_use_symlinks=False,
                resume_download=True
            )
            
        elif mirror == "modelscope":
            # 使用 ModelScope 镜像
            try:
                from modelscope import snapshot_download as ms_snapshot_download
            except ImportError:
                logger.error("请安装 modelscope: pip install modelscope")
                return None
            
            # ModelScope 的模型ID映射
            ms_model_id = f"AI-ModelScope/{model_id}"
            logger.info(f"ModelScope 模型ID: {ms_model_id}")
            
            local_path = ms_snapshot_download(
                ms_model_id,
                cache_dir=str(save_dir.parent),
                revision='master'
            )
        else:
            logger.error(f"不支持的镜像: {mirror}")
            return None
        
        logger.info(f"模型下载完成: {local_path}")
        total_size = sum(f.stat().st_size for f in Path(local_path).rglob('*') if f.is_file())
        logger.info(f"模型大小: {total_size / 1024 / 1024 / 1024:.2f} GB")
        
        return local_path
        
    except Exception as e:
        logger.error(f"下载失败: {e}")
        logger.info("\n请尝试以下方案：")
        logger.info("1. 检查网络连接")
        logger.info("2. 使用 VPN 或代理")
        logger.info("3. 手动下载模型文件")
        logger.info(f"   下载地址: https://huggingface.co/{model_id}")
        logger.info(f"   镜像地址: https://hf-mirror.com/{model_id}")
        return None


def main():
    parser = argparse.ArgumentParser(description="LLaVA 模型下载工具")
    parser.add_argument("--mirror", default="hf-mirror", choices=["hf-mirror", "modelscope", "official"],
                        help="选择下载镜像站点")
    parser.add_argument("--model", default="liuhaotian/LLaVA-1.5-7B", help="模型ID")
    parser.add_argument("--save-dir", default=None, help="保存目录")
    args = parser.parse_args()
    
    print("=" * 60)
    print("LLaVA 模型下载工具")
    print("=" * 60)
    
    print(f"\n模型: {args.model}")
    print(f"镜像: {args.mirror}")
    print("模型大小约 10GB，请耐心等待...")
    
    local_path = download_model_from_mirror(
        model_id=args.model,
        save_dir=args.save_dir,
        mirror=args.mirror
    )
    
    if local_path:
        print("\n" + "=" * 60)
        print("下载成功！")
        print("=" * 60)
        print(f"模型路径: {local_path}")
        print("\n请修改配置文件 vision_only/config/config.json:")
        print(f'  "USE_LOCAL_MODEL": true')
        print(f'  "LOCAL_MODEL_NAME": "{local_path}"')
        print("\n然后重新运行程序即可使用本地模型。")
    else:
        print("\n下载失败，请检查错误信息后重试。")


if __name__ == "__main__":
    main()
# backend/src/rag/knowledge_base.py

import os
import shutil
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 知识库配置
class KnowledgeBaseConfig:
    """知识库配置"""
    # 数据目录
    data_dir = os.path.join(ROOT_DIR, "backend/data")
    print(f"数据目录: {data_dir}")
    # 知识库文本文件路径
    knowledge_file = os.path.join(data_dir, "knowledge", "knowledge.txt")
    # 索引目录路径
    index_dir = os.path.join(data_dir, "faiss_indexes")
    # 嵌入模型名称
    embedding_model = "/root/autodl-tmp/virtual star/virtual_constellation_assistant/backend/src/llm/gte-base-zh"


class KnowledgeBase:
    """
    使用LangChain和FAISS实现的知识库，用于存储和检索卫星和遥感领域的知识
    """

    def __init__(self, config=None):
        """初始化知识库"""
        self.config = config or KnowledgeBaseConfig()
        self.embedding_model_name = self.config.embedding_model
        self.index_dir = self.config.index_dir
        self.knowledge_file = self.config.knowledge_file

        # 确保数据目录和索引目录存在
        os.makedirs(os.path.dirname(self.knowledge_file), exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)

        # 初始化嵌入模型和向量存储
        self.embedding_model = None
        self.vector_store = None

        # 加载嵌入模型
        self._init_embedding_model()

        # 加载向量存储
        self._load_vector_store()

    def _init_embedding_model(self):
        """初始化嵌入模型"""
        try:
            logger.info(f"正在加载嵌入模型: {self.embedding_model_name}")
            start_time = time.time()
            self.embedding_model = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            elapsed = time.time() - start_time
            logger.info(f"嵌入模型已加载，耗时 {elapsed:.2f} 秒")
        except Exception as e:
            logger.error(f"加载嵌入模型时出错: {str(e)}")
            raise

    def _load_vector_store(self):
        """加载向量存储"""
        index_file = os.path.join(self.index_dir, "index.faiss")
        pkl_file = os.path.join(self.index_dir, "index.pkl")

        if os.path.exists(index_file) and os.path.exists(pkl_file):
            try:
                logger.info(f"正在从 {self.index_dir} 加载FAISS索引")
                start_time = time.time()
                # 添加允许反序列化参数
                self.vector_store = FAISS.load_local(
                    self.index_dir,
                    self.embedding_model,
                    allow_dangerous_deserialization=True  # 允许反序列化
                )
                elapsed = time.time() - start_time
                logger.info(f"FAISS索引加载完成，耗时 {elapsed:.2f} 秒")
                return True
            except Exception as e:
                logger.error(f"加载FAISS索引时出错: {str(e)}")
                logger.warning("将尝试重新构建索引")
                return False
        else:
            logger.warning(f"FAISS索引文件不存在: {index_file}")
            return False

    def _load_documents(self):
        """加载文档"""
        # 检查文件是否存在
        if not os.path.exists(self.knowledge_file):
            error_msg = f"错误：文件 {self.knowledge_file} 不存在！请先创建该文件。"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info("正在加载文档...")
        # 读取文件内容
        with open(self.knowledge_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 分割文档
        docs = content.strip().split("\n\n")
        logger.info(f"已加载 {len(docs)} 条知识描述")
        return docs

    def build_index(self, force_rebuild=False):
        """构建FAISS索引"""
        # 如果索引已存在且不强制重建，则跳过
        if not force_rebuild and self.vector_store is not None:
            logger.info("索引已存在，跳过构建")
            return True

        try:
            # 如果需要重建，先删除旧索引
            if force_rebuild and os.path.exists(self.index_dir):
                shutil.rmtree(self.index_dir)
                logger.info(f"已删除旧的索引目录: {self.index_dir}")
                os.makedirs(self.index_dir, exist_ok=True)
                logger.info(f"已创建新的索引目录: {self.index_dir}")

            # 第一步：加载文档
            logger.info("第1步/3：加载文档")
            docs = self._load_documents()

            # 第二步：创建嵌入向量和构建索引
            logger.info("第2步/3：创建文档嵌入向量和构建索引")
            logger.info(f"开始处理 {len(docs)} 条文档...")

            start_time = time.time()
            # 使用tqdm显示文档总数的进度
            documents_with_progress = tqdm(docs, desc="处理文档")

            # 构建向量存储
            self.vector_store = FAISS.from_texts(documents_with_progress, self.embedding_model)

            elapsed = time.time() - start_time
            logger.info(f"向量索引构建完成，耗时 {elapsed:.2f} 秒")

            # 第三步：保存索引
            logger.info("第3步/3：保存索引到磁盘")
            start_time = time.time()
            # 保存索引 - 不使用不支持的参数
            self.vector_store.save_local(self.index_dir)
            elapsed = time.time() - start_time

            # 验证文件是否存在
            index_exists = os.path.exists(os.path.join(self.index_dir, "index.faiss"))
            pkl_exists = os.path.exists(os.path.join(self.index_dir, "index.pkl"))

            if index_exists and pkl_exists:
                logger.info(f"索引已成功保存至：{self.index_dir}，耗时 {elapsed:.2f} 秒")
                return True
            else:
                logger.error(f"索引保存失败，index.faiss存在: {index_exists}, index.pkl存在: {pkl_exists}")
                return False

        except Exception as e:
            logger.error(f"构建索引时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回的最相关结果数量

        Returns:
            包含文档内容和相似度的结果列表
        """
        if self.vector_store is None:
            logger.warning("向量存储未初始化，无法执行搜索")
            return []

        try:
            # 执行相似度搜索
            results = self.vector_store.similarity_search_with_score(query, k=top_k)

            # 格式化结果
            formatted_results = []
            for doc, score in results:
                # LangChain FAISS返回的分数实际上是距离，越小越相似
                # 转换为相似度分数 (0-1范围，越大越相似)
                similarity = 1.0 / (1.0 + score)

                formatted_results.append({
                    "document": doc.page_content,
                    "score": similarity
                })

            return formatted_results

        except Exception as e:
            logger.error(f"搜索时出错: {str(e)}")
            return []

    def add_texts(self, texts: List[str]) -> bool:
        """
        向知识库添加新文本

        Args:
            texts: 文本列表

        Returns:
            添加是否成功
        """
        if not texts:
            return False

        if self.vector_store is None:
            logger.warning("向量存储未初始化，无法添加文本")
            return False

        try:
            # 添加文本到向量存储
            self.vector_store.add_texts(texts)

            # 保存更新后的索引
            self.vector_store.save_local(self.index_dir)

            logger.info(f"成功添加 {len(texts)} 条文本到知识库")
            return True

        except Exception as e:
            logger.error(f"添加文本时出错: {str(e)}")
            return False


# 创建知识库单例
_knowledge_base_instance = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库实例（单例模式）"""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance


if __name__ == "__main__":
    """
    这段代码仅在直接运行此文件时执行，用于一次性构建知识库索引
    构建完成后，应用程序将直接加载已构建的索引
    """
    print("=" * 50)
    print("开始构建知识库索引")
    print("=" * 50)

    # 确保相关目录存在
    kb_config = KnowledgeBaseConfig()

    # 检查知识库文件是否存在
    if not os.path.exists(kb_config.knowledge_file):
        print(f"错误: 知识库文件不存在: {kb_config.knowledge_file}")
        print("请确保在以下位置创建知识库文件:")
        print(kb_config.knowledge_file)
        print("\n文件格式应为文本文件，每段知识之间用空行分隔。例如：")
        print("\n---示例格式---")
        print("这是第一段卫星知识。这里可以包含多个句子。")
        print("")
        print("这是第二段卫星知识。每段之间用空行分隔。")
        print("---------------")
        exit(1)

    try:
        start_total = time.time()

        # 创建知识库实例
        kb = KnowledgeBase()

        # 重新构建索引
        print("正在构建索引...")
        success = kb.build_index(force_rebuild=True)

        if success:
            elapsed_total = time.time() - start_total
            print("-" * 50)
            print(f"知识库索引构建成功! 总耗时：{elapsed_total:.2f} 秒")
            print("-" * 50)

            # 验证索引目录和文件
            print("\n📊 最终结果验证：")
            index_dir_exists = os.path.exists(kb_config.index_dir)
            if index_dir_exists:
                print(f"✅ 索引目录已创建：{kb_config.index_dir}")
                index_files = os.listdir(kb_config.index_dir)
                print(f"   目录内容：{', '.join(index_files)}")

                # 检查文件大小
                index_size = os.path.getsize(os.path.join(kb_config.index_dir, "index.faiss")) / (1024 * 1024)
                pkl_size = os.path.getsize(os.path.join(kb_config.index_dir, "index.pkl")) / (1024 * 1024)
                print(f"   index.faiss 大小：{index_size:.2f} MB")
                print(f"   index.pkl 大小：{pkl_size:.2f} MB")

            # 测试搜索功能
            print("\n测试搜索功能:")
            test_query = "卫星遥感技术"
            print(f"查询: '{test_query}'")
            results = kb.search(test_query, top_k=3)

            print(f"找到 {len(results)} 个相关结果:")
            for i, result in enumerate(results):
                print(f"\n结果 {i + 1} (相似度: {result['score']:.4f}):")
                print("-" * 40)
                print(result['document'][:200] + "..." if len(result['document']) > 200 else result['document'])
                print("-" * 40)
        else:
            print("索引构建失败，请检查日志了解详情")

    except Exception as e:
        print(f"构建索引时出错: {str(e)}")
        import traceback

        traceback.print_exc()
        exit(1)

    print("\n索引已构建完成并保存到磁盘")
    print("下次应用程序启动时将直接加载此索引")
    print("如需重新构建索引，请再次运行此文件")
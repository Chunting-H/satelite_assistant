// location.js 修改版 - 使用DeepSeek API
import axios from 'axios';

// 提取地点关键词
export const extractLocation = async (text) => {
  try {
    console.log("开始提取地点，文本内容:", text);

    // 本地备用实现：常见地名列表
    const commonLocations = [
      '北京', '上海', '广州', '深圳', '武汉', '杭州', '南京', '成都', '重庆', '西安',
      '青海湖', '海南', '黄河', '长江', '台湾', '香港', '澳门', '日本', '美国', '欧洲'
    ];

    // 使用DeepSeek API进行地点提取
    try {
      // 替换以下URL和headers为DeepSeek的API端点和您的认证信息
      const response = await axios.post("https://api.deepseek.com/v1/chat/completions", {  // 请替换为实际的DeepSeek API URL
        model: "deepseek-chat",  // 请替换为正确的DeepSeek模型名称
        messages: [{
          role: "user",
          content: `请从这句话中提取出一个地名（大洲、国家、省份、城市、区县）关键词，只返回地名（大洲、国家、省份、城市、区县），不要回答其他内容。如果输入的是单独的地名则完整返回该地名，如果没有明确的地名则回复"无地点"：${text}`
        }],
        temperature: 0.1  // 低温度使输出更确定性
      }, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer sk-40059d9b6b6943319120ad243c2dd0e4"  // 请替换为您的DeepSeek API密钥
        },
        timeout: 10000 // 设置超时
      });

      // 根据DeepSeek API的响应格式调整此处
      const extractedLocation = response.data.choices?.[0]?.message?.content?.trim();
      if (extractedLocation && extractedLocation !== "无地点") {
        console.log("DeepSeek API成功提取到地点:", extractedLocation);
        return extractedLocation;
      }
    } catch (apiError) {
      console.log("DeepSeek API提取地点失败，使用本地方法:", apiError);
      // API调用失败时回退到本地提取
    }

    // 本地提取逻辑，当API失败时使用
    for (const loc of commonLocations) {
      if (text.includes(loc)) {
        console.log("本地提取到地点:", loc);
        return loc;
      }
    }

    return null;
  } catch (error) {
    console.error('地点提取过程出错:', error);
    return null;
  }
};
// components/Chat/FixedThinkingProcess.jsx - 支持独立思考过程显示
import React, { useState, useEffect, useRef } from 'react';

const FixedThinkingProcess = ({
  steps = [],
  visible = false,
  isProcessing = false,
  title = "思考过程" // 🔧 新增：支持自定义标题
}) => {
  const [displayedSteps, setDisplayedSteps] = useState([]);
  const scrollRef = useRef(null);

  // 🔧 修改：直接使用传入的steps，不需要复杂的去重逻辑
  useEffect(() => {
    if (steps && steps.length > 0) {
      console.log('ThinkingProcess更新步骤:', steps.length);
      setDisplayedSteps(steps);
    } else if (!isProcessing) {
      // 只有在不处理时才清空，避免闪烁
      setDisplayedSteps([]);
    }
  }, [steps, isProcessing]);

  // 自动滚动到最新步骤
  useEffect(() => {
    if (scrollRef.current && displayedSteps.length > 0) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayedSteps]);

  // 阶段配置
  const stageConfig = {
    "初始化": { icon: "🚀", color: "text-blue-600", bgColor: "bg-blue-50" },
    "意图分析": { icon: "🧠", color: "text-purple-600", bgColor: "bg-purple-50" },
    "意图识别": { icon: "✨", color: "text-indigo-600", bgColor: "bg-indigo-50" },
    "知识检索": { icon: "📚", color: "text-green-600", bgColor: "bg-green-50" },
    "知识检索完成": { icon: "✅", color: "text-green-700", bgColor: "bg-green-100" },
    "方案生成": { icon: "⭐", color: "text-orange-600", bgColor: "bg-orange-50" },
    "AI生成": { icon: "🤖", color: "text-cyan-600", bgColor: "bg-cyan-50" },
    "方案生成完成": { icon: "🎯", color: "text-orange-700", bgColor: "bg-orange-100" },
    "响应生成": { icon: "📝", color: "text-cyan-600", bgColor: "bg-cyan-50" },
    "处理完成": { icon: "🎉", color: "text-emerald-600", bgColor: "bg-emerald-50" },
    "方案优化": { icon: "🔧", color: "text-yellow-600", bgColor: "bg-yellow-50" },
    "方案优化完成": { icon: "✨", color: "text-yellow-700", bgColor: "bg-yellow-100" },
    "处理错误": { icon: "❌", color: "text-red-600", bgColor: "bg-red-50" },
    "默认": { icon: "🔄", color: "text-gray-600", bgColor: "bg-gray-50" }
  };

  const getStepConfig = (stepName) => {
    return stageConfig[stepName] || stageConfig["默认"];
  };

  if (!visible && !isProcessing && displayedSteps.length === 0) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-gray-50 to-blue-50 p-4 rounded-lg mb-4 border border-gray-200 shadow-sm">
      {/* 🔧 修改：头部支持自定义标题 */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center justify-center w-8 h-8 rounded-full">
          {isProcessing ? (
            <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <div className="w-5 h-5 bg-green-500 rounded-full"></div>
          )}
        </div>

        <div className="flex-1">
          <h3 className="text-sm font-medium text-gray-800">
            {title}
          </h3>
          {displayedSteps.length > 0 && (
            <p className="text-xs text-gray-500">
              {isProcessing ? `进行中 (${displayedSteps.length} 步骤)` : `已完成 ${displayedSteps.length} 个步骤`}
            </p>
          )}
        </div>

        {/* 🔧 修改：实时处理指示器 */}
        {isProcessing && (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100"></div>
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200"></div>
          </div>
        )}
      </div>

      {/* 思考步骤列表 */}
      {displayedSteps.length > 0 && (
        <div
          ref={scrollRef}
          className="space-y-2 max-h-60 overflow-y-auto"
        >
          {displayedSteps.map((step, index) => {
            const config = getStepConfig(step.step);
            const isLatest = index === displayedSteps.length - 1;
            const isError = step.isError || step.step.includes('错误');

            return (
              <div
                key={step.id || `step_${index}`}
                className={`flex items-start gap-3 p-3 rounded-md border transition-all duration-300 ${
                  isError ? 'bg-red-50 border-red-200' : config.bgColor
                } border-gray-200 ${
                  isLatest && isProcessing ? 'ring-2 ring-blue-200 shadow-md' : ''
                }`}
              >
                {/* 步骤图标 */}
                <div className="flex-shrink-0 mt-0.5">
                  <span className="text-lg">{config.icon}</span>
                </div>

                {/* 步骤内容 */}
                <div className="flex-1 min-w-0">
                  <div className={`font-medium text-sm ${isError ? 'text-red-600' : config.color}`}>
                    {step.step}
                  </div>
                  <div className="text-xs text-gray-600 mt-1 break-words">
                    {step.message}
                  </div>
                  {/* 时间戳 */}
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </div>
                </div>

                {/* 最新步骤的动画指示器 */}
                {isLatest && isProcessing && !isError && (
                  <div className="flex-shrink-0">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping"></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 当没有步骤但正在处理时的占位内容 */}
      {displayedSteps.length === 0 && isProcessing && (
        <div className="flex items-center justify-center py-6 text-gray-500">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mx-auto mb-2"></div>
            <p className="text-sm">正在初始化处理流程...</p>
          </div>
        </div>
      )}

      {/* 完成指示器 */}
      {!isProcessing && displayedSteps.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-center">
          <div className="flex items-center gap-2 text-green-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium">思考完成</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FixedThinkingProcess;
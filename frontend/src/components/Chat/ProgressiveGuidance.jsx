// frontend/src/components/Chat/ProgressiveGuidance.jsx

import React, { useState, useEffect } from 'react';
import CaseShowcase from './CaseShowcase';
import { motion } from 'framer-motion';

const ProgressiveGuidance = ({
  stage,
  options,
  cases = [],
  questionData = {},
  onSelect,
  onCustomInput,
  context = {}
}) => {
  const [selectedOption, setSelectedOption] = useState(null);
  const [customInput, setCustomInput] = useState('');
  const [showCustom, setShowCustom] = useState(false);
  const [showCases, setShowCases] = useState(false);

  // 阶段信息（保持原有）
  const stageInfo = {
    purpose: {
      title: '选择监测目标',
      subtitle: '请选择您最关心的监测内容',
      icon: '🎯'
    },
    location: {
      title: '确定监测位置',
      subtitle: '请选择或描述您的监测区域',
      icon: '📍'
    },
    time: {
      title: '设置监测时间',
      subtitle: '请选择合适的监测频率和周期',
      icon: '⏰'
    }
  };

  const currentStageInfo = stageInfo[stage] || {};

  const handleOptionSelect = (option) => {
    setSelectedOption(option);
    if (onSelect) {
      onSelect(option);
    }
  };

  const handleCustomSubmit = () => {
    if (customInput.trim() && onCustomInput) {
      onCustomInput(customInput);
      setCustomInput('');
      setShowCustom(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-4 border border-blue-200">
      {/* 阶段标题 - 使用AI生成的介绍 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{currentStageInfo.icon}</span>
          <h3 className="text-xl font-semibold text-gray-800">
            {currentStageInfo.title}
          </h3>
        </div>
        <p className="text-gray-600">
          {questionData.introduction || currentStageInfo.subtitle}
        </p>
      </div>

      {/* 进度指示器（保持原有） */}
      <div className="flex items-center justify-between mb-6">
        {/* ... 进度条代码保持不变 ... */}
      </div>

      {/* 选项卡片 - 增强版 */}
      {options && options.length > 0 && (
        <div className="space-y-3 mb-4">
          {options.map((option, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => handleOptionSelect(option)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                selectedOption === option
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start">
                <span className="text-2xl mr-3">{option.icon}</span>
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-800 mb-1">
                    {option.name}
                  </h4>
                  <p className="text-sm text-gray-600 mb-2">
                    {option.purpose}
                  </p>

                  {/* 指标标签 */}
                  {option.indicators && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {option.indicators.map((indicator, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
                        >
                          {indicator}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* 案例预览 */}
                  {option.case && (
                    <div className="mt-3 p-3 bg-green-50 rounded-lg">
                      <p className="text-sm text-green-800">
                        <span className="font-medium">💡 案例：</span>
                        {option.case}
                      </p>
                      {option.benefit && (
                        <p className="text-xs text-green-700 mt-1">
                          <span className="font-medium">效果：</span>
                          {option.benefit}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* 查看更多案例按钮 */}
      {cases && cases.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowCases(!showCases)}
            className="w-full py-3 bg-white border-2 border-blue-300 rounded-lg text-blue-600 font-medium hover:bg-blue-50 transition-colors flex items-center justify-center gap-2"
          >
            <span>📊</span>
            <span>{showCases ? '收起案例展示' : `查看 ${cases.length} 个相关案例`}</span>
            <svg
              className={`w-4 h-4 transition-transform ${showCases ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* 案例展示区域 */}
          {showCases && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4"
            >
              <CaseShowcase
                cases={cases}
                stage={stage}
                onCaseClick={(caseData) => {
                  // 使用案例数据填充选项
                  handleOptionSelect({
                    name: caseData.solutionType,
                    ...caseData
                  });
                }}
              />
            </motion.div>
          )}
        </div>
      )}

      {/* 自定义输入（保持原有） */}
      <div className="mt-4">
        {!showCustom ? (
          <button
            onClick={() => setShowCustom(true)}
            className="text-sm text-blue-600 hover:text-blue-700 underline"
          >
            没有找到合适的选项？自定义输入
          </button>
        ) : (
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <p className="text-sm text-gray-600 mb-2">请描述您的具体需求：</p>
            <textarea
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="例如：我想监测鱼塘的水质变化..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="3"
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => {
                  setShowCustom(false);
                  setCustomInput('');
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                取消
              </button>
              <button
                onClick={handleCustomSubmit}
                disabled={!customInput.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                确认
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 智能提示 - 使用AI生成的提示 */}
      {questionData.tips && (
        <div className="mt-6 p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-700">
            💡 <strong>提示：</strong>{questionData.tips}
          </p>
        </div>
      )}

      {/* 数据来源标记 */}
      {questionData.has_real_cases && (
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500">
            📊 以上案例来自真实应用数据
          </p>
        </div>
      )}
    </div>
  );
};

export default ProgressiveGuidance;
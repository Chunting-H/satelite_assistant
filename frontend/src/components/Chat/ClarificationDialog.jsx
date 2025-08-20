// src/components/Chat/ClarificationDialog.jsx
import React, { useState, useEffect } from 'react';

const ClarificationDialog = ({
  questions = [],
  onSubmit,
  onSkip,
  isVisible = false,
  existingParams = {},
  parametersUncertainty = {},
  currentStage = null,
  stageName = '',
  retryCount = 0
}) => {
  const [answers, setAnswers] = useState({});
  const [validationErrors, setValidationErrors] = useState({});
  const [inputModes, setInputModes] = useState({}); // 新增：记录每个参数的输入模式

  // 初始化输入模式
  useEffect(() => {
    const modes = {};
    questions.forEach(q => {
      // 默认有选项的使用选项模式，否则使用自定义输入
      modes[q.parameter_key] = q.options && q.options.length > 0 ? 'options' : 'custom';
    });
    setInputModes(modes);
  }, [questions]);

  // 阶段进度组件（保持不变）
  const StageProgress = () => {
    const stages = [
      { key: 'purpose', name: '监测目标', icon: '🎯' },
      { key: 'time', name: '时间参数', icon: '⏰' },
      { key: 'location_area', name: '观测区域', icon: '📍' },
      { key: 'location_range', name: '覆盖范围', icon: '🗺️' },
      { key: 'technical', name: '技术参数', icon: '⚙️' }
    ];

    const currentIndex = stages.findIndex(s => s.key === currentStage);

    return (
      <div className="mb-6">
        <div className="flex items-center justify-between">
          {stages.map((stage, index) => (
            <div key={stage.key} className="flex-1 flex items-center">
              <div className={`
                flex items-center justify-center w-8 h-8 md:w-10 md:h-10 rounded-full transition-all duration-300
                ${index < currentIndex ? 'bg-green-500 text-white' : 
                  index === currentIndex ? 'bg-blue-500 text-white animate-pulse' : 
                  'bg-gray-200 text-gray-500'}
              `}>
                <span className="text-xs md:text-sm">{stage.icon}</span>
              </div>
              {index < stages.length - 1 && (
                <div className={`flex-1 h-1 mx-0.5 md:mx-1 transition-all duration-300
                  ${index < currentIndex ? 'bg-green-500' : 'bg-gray-200'}`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2">
          {stages.map(stage => (
            <div key={stage.key} className="text-[10px] md:text-xs text-center flex-1 px-0.5 md:px-1">
              <span className="hidden md:inline">{stage.name}</span>
              <span className="md:hidden">{stage.name.slice(0, 4)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 不确定性反馈组件（保持不变）
  const UncertaintyFeedback = ({ uncertainty }) => {
    if (!uncertainty || !uncertainty.needs_clarification) return null;

    const score = uncertainty.uncertainty_score || 0;
    const details = uncertainty.details || {};

    return (
      <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-center gap-2 text-yellow-800">
          <span>⚠️</span>
          <span className="font-medium">
            需要更明确的信息（不确定性：{Math.round(score * 100)}%）
          </span>
        </div>
        {details.missing_info && (
          <p className="mt-1 text-sm text-yellow-700">{details.missing_info}</p>
        )}
      </div>
    );
  };

  // 切换输入模式
  const toggleInputMode = (paramKey) => {
    setInputModes(prev => ({
      ...prev,
      [paramKey]: prev[paramKey] === 'options' ? 'custom' : 'options'
    }));
  };

  // 渲染问题
  const renderQuestion = (question) => {
    const uncertainty = question.uncertainty_info;
    const currentMode = inputModes[question.parameter_key] || 'custom';
    const hasOptions = question.options && question.options.length > 0;

    return (
      <div key={question.parameter_key} className="mb-6">
        {uncertainty && <UncertaintyFeedback uncertainty={uncertainty} />}

        <div className="flex items-center justify-between mb-3">
          <label className="block text-gray-700 font-medium">
            {question.question}
            {question.required && <span className="text-red-500 ml-1">*</span>}
          </label>

          {/* 切换按钮 */}
          {hasOptions && (
            <button
              type="button"
              onClick={() => toggleInputMode(question.parameter_key)}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              {currentMode === 'options' ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>自定义输入</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                  <span>选择选项</span>
                </>
              )}
            </button>
          )}
        </div>

        {/* 根据模式渲染不同的输入方式 */}
        {currentMode === 'options' && hasOptions ? (
          <div className="space-y-2">
            {/* 🔧 修改：智能调整选项显示 */}
            {question.options.map((opt, idx) => {
              // 如果选项超过5个，使用更紧凑的显示方式
              if (question.options.length > 5) {
                return (
                  <label
                    key={idx}
                    className={`block p-2 rounded-lg border cursor-pointer transition-all text-sm
                      ${answers[question.parameter_key] === (opt.value || opt) 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:bg-gray-50'}`}
                  >
                    <input
                      type="radio"
                      name={`param_${question.parameter_key}`}
                      value={opt.value || opt}
                      checked={answers[question.parameter_key] === (opt.value || opt)}
                      onChange={(e) => handleInputChange(question.parameter_key, e.target.value)}
                      className="mr-2"
                    />
                    <span className="font-medium">{opt.label || opt}</span>
                    {/* 超过5个选项时，描述显示为tooltip */}
                    {opt.description && (
                      <span className="text-xs text-gray-500 ml-1" title={opt.description}>
                        ⓘ
                      </span>
                    )}
                  </label>
                );
              } else {
                // 5个或更少选项时，保持原有的详细显示
                return (
                  <label
                    key={idx}
                    className={`block p-3 rounded-lg border cursor-pointer transition-all
                      ${answers[question.parameter_key] === (opt.value || opt) 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:bg-gray-50'}`}
                  >
                    <input
                      type="radio"
                      name={`param_${question.parameter_key}`}
                      value={opt.value || opt}
                      checked={answers[question.parameter_key] === (opt.value || opt)}
                      onChange={(e) => handleInputChange(question.parameter_key, e.target.value)}
                      className="mr-2"
                    />
                    <span className="font-medium">{opt.label || opt}</span>
                    {opt.description && (
                      <p className="text-sm text-gray-600 mt-1 ml-6">{opt.description}</p>
                    )}
                  </label>
                );
              }
            })}
          </div>
        ) : (
          // 自定义输入模式
          <div className="space-y-2">
            <textarea
              value={answers[question.parameter_key] || ''}
              onChange={(e) => handleInputChange(question.parameter_key, e.target.value)}
              placeholder={
                question.examples
                  ? `例如：${question.examples.slice(0, 2).join('、')}`
                  : '请输入您的具体需求...'
              }
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[80px] resize-y"
              rows={3}
            />

            {/* 如果有选项，显示参考选项 */}
            {hasOptions && (
              <div className="mt-2">
                <p className="text-sm text-gray-600 mb-1">参考选项：</p>
                <div className="flex flex-wrap gap-2">
                  {question.options.slice(0, 5).map((opt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleInputChange(question.parameter_key, opt.value || opt)}
                      className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
                    >
                      {opt.label || opt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 提示信息 */}
        {question.hint && (
          <p className="text-sm text-gray-500 mt-2">{question.hint}</p>
        )}

        {/* 验证错误 */}
        {validationErrors[question.parameter_key] && (
          <p className="text-sm text-red-500 mt-1">{validationErrors[question.parameter_key]}</p>
        )}
      </div>
    );
  };

  const handleInputChange = (key, value) => {
    setAnswers(prev => ({ ...prev, [key]: value }));
    // 清除验证错误
    if (validationErrors[key]) {
      setValidationErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    }
  };

  const validateAnswers = () => {
    const errors = {};
    questions.forEach(q => {
      if (q.required && !answers[q.parameter_key]) {
        errors[q.parameter_key] = '此项为必填项';
      }
    });
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const formatAnswerValue = (paramKey, value, question) => {
    // 处理特殊的英文值转换
    const valueMapping = {
      // 观测频率
      'daily': '每天1次',
      'weekly': '每周1次',
      'twice_weekly': '每周2次',
      'monthly': '每月1次',
      'realtime': '实时监测',

      // 监测周期
      '1_month': '1个月',
      '3_months': '3个月',
      '6_months': '6个月',
      '1_year': '1年',
      'long_term': '长期监测',

      // 空间分辨率
      'very_high': '超高分辨率(<1米)',
      'high': '高分辨率(1-5米)',
      'medium': '中分辨率(5-30米)',
      'low': '低分辨率(>30米)'
    };

    // 如果有映射，使用映射值
    if (valueMapping[value]) {
      return valueMapping[value];
    }

    // 否则尝试从选项中获取label
    if (question.options && question.options.length > 0) {
      const selectedOption = question.options.find(opt =>
        (opt.value || opt) === value
      );

      if (selectedOption && selectedOption.label) {
        return selectedOption.label;
      }
    }

    // 返回原值
    return value;
  };

  const handleSubmit = () => {
    if (!validateAnswers()) {
      return;
    }

    // 参数中文名称映射
    const paramDisplayNames = {
      monitoring_target: "监测目标",
      observation_area: "观测区域",
      coverage_range: "覆盖范围",
      observation_frequency: "观测频率",
      monitoring_period: "监测周期",
      spatial_resolution: "空间分辨率",
      spectral_bands: "光谱波段",
      analysis_requirements: "分析需求",
      accuracy_requirements: "精度要求",
      output_format: "输出格式"
    };

    // 构建更友好的回复文本
    const responseTexts = [];

    // 按照问题顺序处理答案
    questions.forEach(question => {
      const paramKey = question.parameter_key;
      const answer = answers[paramKey];

      if (answer) {
        const paramName = paramDisplayNames[paramKey] || question.parameter_name;

        // 获取选中选项的完整信息（包括label）
        let displayValue = answer;

        if (question.options && question.options.length > 0) {
          const selectedOption = question.options.find(opt =>
            (opt.value || opt) === answer
          );

          if (selectedOption && selectedOption.label) {
            displayValue = selectedOption.label;
          }
        }

        // 格式化输出
        responseTexts.push(`${paramName}是${displayValue}`);
      }
    });

    // 使用中文逗号连接
    const responseText = responseTexts.join('，');

    // 如果没有有效回答，使用原来的逻辑
    if (responseTexts.length === 0) {
      const fallbackText = Object.entries(answers)
        .map(([key, value]) => value)
        .filter(v => v)
        .join(' | ');
      onSubmit(fallbackText);
    } else {
      onSubmit(responseText);
    }
  };

  // 🔧 修改：简化跳过技术参数的处理
  const handleSkipTechnicalParams = () => {
    onSubmit('跳过技术参数');
  };

  if (!isVisible) return null;

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 mb-4 border border-blue-200">
      <StageProgress />

      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          {stageName || '参数收集'}
          {currentStage === 'technical' && (
            <span className="text-sm text-gray-600 ml-2">（可选，但建议设置）</span>
          )}
          {retryCount > 0 && <span className="text-sm text-gray-600 ml-2">（第{retryCount + 1}次）</span>}
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          您可以选择推荐选项，也可以切换到自定义输入模式填写具体需求
        </p>
      </div>

      <div className="space-y-4">
        {questions.map(renderQuestion)}
      </div>

      {/* 🔧 修改：底部按钮区域 - 只在技术参数阶段显示跳过按钮 */}
      <div className="mt-6 flex justify-between">
        {/* 🔧 修改：只在技术参数阶段显示跳过按钮 */}
        {currentStage === 'technical' ? (
          <button
            onClick={handleSkipTechnicalParams}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
            <span>跳过技术参数</span>
          </button>
        ) : (
          // 🔧 新增：其他阶段显示空占位符，保持布局对齐
          <div></div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => onSkip()}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={questions.some(q => q.required && !answers[q.parameter_key])}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            确认并继续
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClarificationDialog;
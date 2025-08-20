// config/features.js

// 特性开关配置
export const FEATURE_FLAGS = {
  // 是否启用迭代式澄清
  enableIterativeClarification: true,

  // 是否启用分层澄清（新增）
  enableLayeredClarification: true,

  // 是否启用案例展示（新增）
  enableCaseDisplay: true,

  // 是否启用智能推荐（新增）
  enableSmartRecommendations: true,

  // 是否显示不确定性评分
  showUncertaintyScore: true,

  // 是否启用动画效果
  enableAnimations: true,

  // 最大迭代次数（与后端保持一致）
  maxClarificationIterations: 3,

  // 分层澄清配置（新增）
  layeredClarificationConfig: {
    layers: ['purpose', 'location', 'time', 'technical'],
    showProgressIndicator: true,
    allowSkipLayer: false,
    showLayerSummary: true
  }
};

// 从环境变量读取配置（如果需要）
if (import.meta.env.VITE_ENABLE_ITERATIVE_CLARIFICATION !== undefined) {
  FEATURE_FLAGS.enableIterativeClarification =
    import.meta.env.VITE_ENABLE_ITERATIVE_CLARIFICATION === 'true';
}

if (import.meta.env.VITE_ENABLE_LAYERED_CLARIFICATION !== undefined) {
  FEATURE_FLAGS.enableLayeredClarification =
    import.meta.env.VITE_ENABLE_LAYERED_CLARIFICATION === 'true';
}
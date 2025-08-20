// components/Chat/MessageActions.jsx - 消息复制和导出功能
import React, { useState } from 'react';

const MessageActions = ({ 
  message, 
  messageId, 
  isAssistant = false, 
  timestamp,
  className = ""
}) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // 复制图标SVG
  const CopyIcon = ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  );

  // 成功图标SVG
  const CheckIcon = ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );

  // PDF图标SVG
  const FileTextIcon = ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );

  // 下载图标SVG
  const DownloadIcon = ({ className }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );

  // 提取纯文本内容
  const extractTextContent = (content) => {
    if (typeof content === 'string') {
      // 移除HTML标签和Markdown格式
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = content
        .replace(/#{1,6}\s/g, '') // 移除Markdown标题
        .replace(/\*\*(.*?)\*\*/g, '$1') // 移除粗体
        .replace(/\*(.*?)\*/g, '$1') // 移除斜体
        .replace(/`(.*?)`/g, '$1') // 移除行内代码
        .replace(/```[\s\S]*?```/g, '') // 移除代码块
        .replace(/\[(.*?)\]\(.*?\)/g, '$1') // 移除链接，保留文本
        .replace(/!\[.*?\]\(.*?\)/g, '') // 移除图片
        .replace(/\|.*?\|/g, ''); // 移除表格分隔符
      
      return tempDiv.textContent || tempDiv.innerText || content;
    }
    return JSON.stringify(content, null, 2);
  };

  // 复制消息内容
  const handleCopy = async () => {
    try {
      const textContent = extractTextContent(message);
      
      // 优先使用现代Clipboard API
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(textContent);
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
        return;
      }
      
      // 降级方案：使用传统的复制方法
      fallbackCopyToClipboard(textContent);
    } catch (err) {
      console.error('复制失败:', err);
      // 降级方案：使用传统的复制方法
      fallbackCopyToClipboard(extractTextContent(message));
    }
  };

  // 改进的降级复制方案
  const fallbackCopyToClipboard = (text) => {
    try {
      // 创建临时文本区域
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.top = '0';
      textArea.style.left = '0';
      textArea.style.width = '2em';
      textArea.style.height = '2em';
      textArea.style.padding = '0';
      textArea.style.border = 'none';
      textArea.style.outline = 'none';
      textArea.style.boxShadow = 'none';
      textArea.style.background = 'transparent';
      textArea.style.opacity = '0';
      textArea.style.pointerEvents = 'none';
      textArea.setAttribute('readonly', '');
      
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      // 尝试使用execCommand
      const successful = document.execCommand('copy');
      
      if (successful) {
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2000);
      } else {
        // 如果execCommand失败，提示用户手动复制
        showCopyFallbackMessage(text);
      }
      
      document.body.removeChild(textArea);
    } catch (err) {
      console.error('降级复制失败:', err);
      showCopyFallbackMessage(text);
    }
  };

  // 显示手动复制提示
  const showCopyFallbackMessage = (text) => {
    // 创建友好的提示消息
    const message = `复制失败，请手动选择以下文本并复制：\n\n${text}`;
    
    // 使用更友好的提示方式
    if (window.confirm('复制功能需要您的帮助。是否打开包含文本的新窗口供您手动复制？')) {
      const newWindow = window.open('', '_blank');
      if (newWindow) {
        newWindow.document.write(`
          <html>
            <head>
              <title>请复制以下内容</title>
              <style>
                body { font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }
                .copy-text { background: #f5f5f5; padding: 15px; border: 1px solid #ddd; border-radius: 5px; white-space: pre-wrap; }
                .instructions { color: #666; margin-bottom: 15px; }
              </style>
            </head>
            <body>
              <div class="instructions">
                <h3>请按以下步骤操作：</h3>
                <ol>
                  <li>选择下面的文本内容</li>
                  <li>按 Ctrl+C (Windows) 或 Cmd+C (Mac) 复制</li>
                  <li>关闭此窗口</li>
                </ol>
              </div>
              <div class="copy-text">${text}</div>
            </body>
          </html>
        `);
        newWindow.document.close();
      }
    }
  };

  // 简化的PDF导出功能
  const handleExportPDF = async () => {
    setIsExporting(true);
    
    try {
      console.log('开始PDF导出...');
      
      // 创建新窗口用于打印
      const printWindow = window.open('', '_blank');
      
      if (!printWindow) {
        alert('请允许弹窗，然后重试PDF导出功能。');
        return;
      }

      // 简化的内容提取
      const { cleanText, tablesHTML } = extractContentForPDF(message);
      const currentTime = new Date().toLocaleString('zh-CN');
      const messageTime = timestamp ? new Date(timestamp).toLocaleString('zh-CN') : '未知';
      
      // 创建简化的HTML文档
      const htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>虚拟星座助手消息 - ${messageId}</title>
    <style>
        @page {
            margin: 15mm;
            size: A4;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', SimSun, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 15px;
            background: white;
            font-size: 13px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #3b82f6;
        }
        
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 22px;
            color: #1f2937;
            font-weight: bold;
        }
        
        .header p {
            margin: 3px 0;
            color: #6b7280;
            font-size: 11px;
        }
        
        .message-info {
            background: ${isAssistant ? '#f8fafc' : '#ffffff'};
            border: 2px solid ${isAssistant ? '#3b82f6' : '#6b7280'};
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 20px;
        }
        
        .message-type {
            font-weight: bold;
            color: ${isAssistant ? '#059669' : '#1d4ed8'};
            margin-bottom: 12px;
            font-size: 15px;
            padding: 6px 10px;
            background: ${isAssistant ? '#ecfdf5' : '#eff6ff'};
            border-radius: 6px;
        }
        
        .message-content {
            line-height: 1.7;
            color: #374151;
        }
        
        .message-content h1, .message-content h2, .message-content h3 {
            color: #1f2937;
            margin: 15px 0 8px 0;
            page-break-after: avoid;
        }
        
        .message-content h1 { font-size: 18px; }
        .message-content h2 { font-size: 16px; }
        .message-content h3 { font-size: 14px; }
        
        .message-content p {
            margin: 8px 0;
        }
        
        .message-content ul, .message-content ol {
            margin: 8px 0;
            padding-left: 20px;
        }
        
        .message-content li {
            margin: 4px 0;
        }
        
        /* 简化的表格样式 */
        .pdf-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10px;
            background: white;
            page-break-inside: avoid;
        }
        
        .pdf-table th {
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            padding: 6px 4px;
            text-align: center;
            font-weight: bold;
            color: #374151;
            vertical-align: middle;
            word-wrap: break-word;
        }
        
        .pdf-table td {
            border: 1px solid #d1d5db;
            padding: 6px 4px;
            text-align: center;
            vertical-align: middle;
            word-wrap: break-word;
            max-width: 80px;
            overflow: hidden;
        }
        
        .pdf-table tr:nth-child(even) {
            background: #f9fafb;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 11px;
        }
        
        .footer strong {
            color: #374151;
        }
        
        @media print {
            body {
                padding: 0;
            }
            
            .pdf-table {
                page-break-inside: avoid;
            }
            
            .pdf-table thead {
                display: table-header-group;
            }
            
            .pdf-table tbody {
                display: table-row-group;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ 虚拟星座助手消息</h1>
        <p>导出时间: ${currentTime}</p>
        <p>消息ID: ${messageId || '未知'}</p>
        <p>消息时间: ${messageTime}</p>
    </div>

    <div class="message-info">
        <div class="message-type">
            ${isAssistant ? '🤖 智慧虚拟星座助手' : '👤 用户消息'}
        </div>
        
        <div class="message-content">
            ${cleanText}
        </div>
    </div>

    ${tablesHTML ? `
    <div style="margin: 20px 0;">
        <h2 style="color: #1f2937; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; font-size: 16px;">📋 包含的数据表格</h2>
        ${tablesHTML}
    </div>
    ` : ''}

    <div class="footer">
        <div style="margin-bottom: 8px;">
            <strong>虚拟星座智能助手</strong>
        </div>
        <div>专业的卫星星座设计与分析平台</div>
        <div style="margin-top: 8px; font-size: 10px;">
            此文档由系统自动生成 • ${currentTime}
        </div>
    </div>

    <script>
        // 页面加载完成后自动打印
        window.onload = function() {
            setTimeout(() => window.print(), 500);
        };
        
        // 监听打印事件
        window.onafterprint = function() {
            setTimeout(() => window.close(), 1000);
        };
    </script>
</body>
</html>`;

      // 写入内容到新窗口
      printWindow.document.write(htmlContent);
      printWindow.document.close();
      
    } catch (error) {
      console.error('PDF导出失败:', error);
      // 使用更友好的错误提示
      if (window.confirm('PDF导出失败。是否尝试下载为文本文件？')) {
        handleDownloadTXT();
      }
    } finally {
      setIsExporting(false);
    }
  };

  // 改进的内容提取函数 - 分离文本和表格
  const extractContentForPDF = (content) => {
    if (typeof content !== 'string') {
      return { 
        cleanText: JSON.stringify(content, null, 2),
        tablesHTML: ''
      };
    }

    // 创建临时DOM元素来处理HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;

    let tablesHTML = '';
    
    // 提取并处理表格
    const tables = tempDiv.querySelectorAll('table');
    tables.forEach((table, index) => {
      // 为表格添加PDF专用的样式类
      table.className = 'pdf-table';
      
      // 处理表头
      const thead = table.querySelector('thead');
      if (thead) {
        const thElements = thead.querySelectorAll('th');
        thElements.forEach(th => {
          th.style.cssText = '';
          // 处理长文本
          if (th.textContent.length > 8) {
            th.style.fontSize = '9px';
          }
        });
      }
      
      // 处理表格内容
      const tbody = table.querySelector('tbody');
      if (tbody) {
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
          const cells = row.querySelectorAll('td');
          cells.forEach(cell => {
            cell.style.cssText = '';
            // 处理长文本
            if (cell.textContent.length > 15) {
              cell.style.fontSize = '9px';
            }
          });
        });
      }
      
      tablesHTML += `<div class="table-wrapper">${table.outerHTML}</div>`;
      
      // 从原内容中移除表格
      table.remove();
    });

    // 处理剩余的文本内容
    let cleanText = tempDiv.innerHTML;
    
    // 处理Markdown和HTML格式
    cleanText = cleanText
      .replace(/#{1,6}\s*(.*?)$/gm, '<h3>$1</h3>') // 标题
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // 粗体
      .replace(/\*(.*?)\*/g, '<em>$1</em>') // 斜体
      .replace(/`(.*?)`/g, '<code style="background:#f1f5f9;padding:2px 4px;border-radius:3px;">$1</code>') // 行内代码
      .replace(/```[\s\S]*?```/g, '<pre style="background:#f8fafc;padding:10px;border-radius:6px;border:1px solid #e2e8f0;">$&</pre>') // 代码块
      .replace(/\[(.*?)\]\(.*?\)/g, '$1') // 移除链接，保留文本
      .replace(/!\[.*?\]\(.*?\)/g, '') // 移除图片
      .replace(/\n\n/g, '</p><p>') // 段落
      .replace(/\n/g, '<br>'); // 换行

    // 包装段落
    if (cleanText && !cleanText.includes('<p>')) {
      cleanText = '<p>' + cleanText + '</p>';
    }

    return { cleanText, tablesHTML };
  };

  // 下载为TXT文件
  const handleDownloadTXT = () => {
    try {
      const textContent = extractTextContent(message);
      const fullContent = `虚拟星座助手消息导出
${'='.repeat(50)}

消息类型: ${isAssistant ? '智能助手回复' : '用户消息'}
导出时间: ${new Date().toLocaleString('zh-CN')}
消息ID: ${messageId || '未知'}
${timestamp ? `消息时间: ${new Date(timestamp).toLocaleString('zh-CN')}` : ''}

${'='.repeat(50)}

${textContent}

${'='.repeat(50)}
由虚拟星座智能助手生成
导出时间: ${new Date().toLocaleString('zh-CN')}`;

      const blob = new Blob([fullContent], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `constellation_message_${messageId || 'unknown'}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('TXT下载失败:', error);
      alert('文件下载失败，请稍后重试');
    }
  };

  // 新增：下载为Markdown文件
  const handleDownloadMarkdown = () => {
    try {
      const markdownContent = convertToMarkdown(message);
      const fullContent = `# 虚拟星座助手消息导出

**消息类型**: ${isAssistant ? '智能助手回复' : '用户消息'}  
**导出时间**: ${new Date().toLocaleString('zh-CN')}  
**消息ID**: ${messageId || '未知'}  
${timestamp ? `**消息时间**: ${new Date(timestamp).toLocaleString('zh-CN')}` : ''}

---

${markdownContent}

---

*由虚拟星座智能助手生成*  
*导出时间: ${new Date().toLocaleString('zh-CN')}*`;

      const blob = new Blob([fullContent], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `constellation_message_${messageId || 'unknown'}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Markdown下载失败:', error);
      alert('文件下载失败，请稍后重试');
    }
  };

  // 新增：转换为Markdown格式
  const convertToMarkdown = (content) => {
    if (typeof content !== 'string') {
      return '```json\n' + JSON.stringify(content, null, 2) + '\n```';
    }

    // 创建临时DOM元素来处理HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;

    // 处理表格
    const tables = tempDiv.querySelectorAll('table');
    tables.forEach((table) => {
      const markdownTable = convertTableToMarkdown(table);
      table.outerHTML = markdownTable;
    });

    // 处理剩余的文本内容
    let markdownText = tempDiv.innerHTML;
    
    // 转换HTML标签为Markdown
    markdownText = markdownText
      .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1')
      .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1')
      .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1')
      .replace(/<h4[^>]*>(.*?)<\/h4>/gi, '#### $1')
      .replace(/<h5[^>]*>(.*?)<\/h5>/gi, '##### $1')
      .replace(/<h6[^>]*>(.*?)<\/h6>/gi, '###### $1')
      .replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
      .replace(/<b[^>]*>(.*?)<\/b>/gi, '**$1**')
      .replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
      .replace(/<i[^>]*>(.*?)<\/i>/gi, '*$1*')
      .replace(/<code[^>]*>(.*?)<\/code>/gi, '`$1`')
      .replace(/<pre[^>]*>(.*?)<\/pre>/gi, '```\n$1\n```')
      .replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1')
      .replace(/<ul[^>]*>(.*?)<\/ul>/gi, '$1\n')
      .replace(/<ol[^>]*>(.*?)<\/ol>/gi, '$1\n')
      .replace(/<div[^>]*>(.*?)<\/div>/gi, '$1')
      .replace(/<span[^>]*>(.*?)<\/span>/gi, '$1')
      .replace(/&nbsp;/g, ' ')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"');

    // 清理多余的空行
    markdownText = markdownText
      .replace(/\n\s*\n\s*\n/g, '\n\n')
      .trim();

    return markdownText;
  };

  // 新增：转换表格为Markdown格式
  const convertTableToMarkdown = (table) => {
    const rows = table.querySelectorAll('tr');
    if (rows.length === 0) return '';

    let markdown = '\n';
    
    rows.forEach((row, index) => {
      const cells = row.querySelectorAll('td, th');
      const cellTexts = Array.from(cells).map(cell => {
        return cell.textContent.trim().replace(/\|/g, '\\|');
      });
      
      markdown += '| ' + cellTexts.join(' | ') + ' |\n';
      
      // 添加表头分隔符
      if (index === 0) {
        markdown += '| ' + cellTexts.map(() => '---').join(' | ') + ' |\n';
      }
    });
    
    return markdown;
  };

  return (
    <div className={`flex items-center gap-1 mt-2 transition-all duration-300 ${className}`}>
      {/* 复制按钮 */}
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-all duration-200 group"
        title="复制消息内容"
      >
        {copySuccess ? (
          <>
            <CheckIcon className="w-3 h-3 text-green-500" />
            <span className="text-green-500 font-medium">已复制</span>
          </>
        ) : (
          <>
            <CopyIcon className="w-3 h-3 group-hover:scale-110 transition-transform" />
            <span>复制</span>
          </>
        )}
      </button>

      {/* PDF导出按钮 */}
      <button
        onClick={handleExportPDF}
        disabled={isExporting}
        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
        title="导出为PDF文档"
      >
        {isExporting ? (
          <>
            <div className="w-3 h-3 border border-gray-400 border-t-blue-500 rounded-full animate-spin"></div>
            <span>导出中...</span>
          </>
        ) : (
          <>
            <FileTextIcon className="w-3 h-3 group-hover:scale-110 transition-transform" />
            <span>PDF</span>
          </>
        )}
      </button>

      {/* TXT下载按钮 */}
      <button
        onClick={handleDownloadTXT}
        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-all duration-200 group"
        title="下载为文本文件"
      >
        <DownloadIcon className="w-3 h-3 group-hover:scale-110 transition-transform" />
        <span>TXT</span>
      </button>

      {/* Markdown下载按钮 */}
      <button
        onClick={handleDownloadMarkdown}
        className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-all duration-200 group"
        title="下载为Markdown文件"
      >
        <svg className="w-3 h-3 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2" />
        </svg>
        <span>Markdown</span>
      </button>
    </div>
  );
};

export default MessageActions;
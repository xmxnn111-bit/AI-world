
import React from 'react';

interface MarkdownRendererProps {
  content: string;
}

/**
 * 这是一个简易的 Markdown 渲染器实现。
 * 在实际生产中，我们会使用 react-markdown。
 * 这里使用结构化展示，并对换行和基础代码块进行处理。
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  // 简单的格式化逻辑，处理换行和简单的 `代码`
  const lines = content.split('\n');
  
  return (
    <div className="prose prose-invert max-w-none text-zinc-200 leading-relaxed">
      {lines.map((line, idx) => {
        // 处理代码块标志（假设简单处理）
        if (line.startsWith('```')) return null;
        
        return (
          <p key={idx} className="mb-2 min-h-[1em]">
            {line.split(/(`[^`]+`)/).map((part, i) => {
              if (part.startsWith('`') && part.endsWith('`')) {
                return (
                  <code key={i} className="bg-zinc-800 px-1.5 py-0.5 rounded text-sm text-blue-300 font-mono">
                    {part.slice(1, -1)}
                  </code>
                );
              }
              return part;
            })}
          </p>
        );
      })}
    </div>
  );
};

export default MarkdownRenderer;

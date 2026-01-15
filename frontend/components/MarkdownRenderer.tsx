import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import 'katex/dist/katex.min.css';

interface MarkdownRendererProps {
    content: string;
}

// --- 子组件：增强型代码块 ---
const CodeBlock = ({ inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : 'text';
    const codeString = String(children).replace(/\n$/, '');

    const [isCopied, setIsCopied] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);

    const lineCount = codeString.split('\n').length;
    const isLongCode = lineCount > 50;
    const heightClass = isLongCode && !isExpanded ? 'max-h-[400px] overflow-hidden' : '';

    const handleCopy = () => {
        navigator.clipboard.writeText(codeString);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    if (inline) {
        return (
            <code className="bg-gray-100 text-red-500 px-1.5 py-0.5 rounded font-mono text-sm" {...props}>
                {children}
            </code>
        );
    }

    return (
        <div className="my-6 rounded-xl overflow-hidden border border-gray-200 shadow-sm bg-[#1e1e1e]">
            <div className="flex items-center justify-between px-4 py-3 bg-[#2d2d2d] border-b border-gray-700">
                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                        <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                        <div className="w-3 h-3 rounded-full bg-[#27c93f]" />
                    </div>
                    <span className="ml-3 text-xs text-gray-400 font-mono lowercase select-none">
            {language}
          </span>
                </div>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                >
                    {isCopied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{isCopied ? 'Copied!' : 'Copy'}</span>
                </button>
            </div>

            <div className={`relative ${heightClass} transition-all duration-300`}>
                <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    customStyle={{
                        margin: 0,
                        padding: '1.5rem',
                        background: 'transparent',
                        fontSize: '0.9rem',
                        lineHeight: '1.6',
                    }}
                    {...props}
                >
                    {codeString}
                </SyntaxHighlighter>

                {isLongCode && !isExpanded && (
                    <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#1e1e1e] to-transparent pointer-events-none" />
                )}
            </div>

            {isLongCode && (
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full py-2 bg-[#2d2d2d] hover:bg-[#363636] text-gray-400 text-xs flex items-center justify-center gap-1 transition-colors border-t border-gray-700"
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp className="w-3 h-3" /> 收起代码
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-3 h-3" /> 展开全部 ({lineCount} 行)
                        </>
                    )}
                </button>
            )}
        </div>
    );
};

// --- 主组件 ---
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
    return (
        <div className="markdown-body text-gray-800 leading-relaxed">
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw]}
                components={{
                    code: CodeBlock,
                    table: ({ children }) => (
                        <div className="overflow-x-auto my-6 border border-gray-200 rounded-lg shadow-sm">
                            <table className="min-w-full divide-y divide-gray-200 text-sm">{children}</table>
                        </div>
                    ),
                    thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
                    th: ({ children }) => (
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider font-semibold">
                            {children}
                        </th>
                    ),
                    td: ({ children }) => <td className="px-4 py-3 whitespace-nowrap text-gray-600 border-t border-gray-100">{children}</td>,
                    ul: ({ children }) => <ul className="list-disc list-outside ml-5 space-y-1 my-4 text-gray-700">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-outside ml-5 space-y-1 my-4 text-gray-700">{children}</ol>,
                    p: ({ children }) => <p className="mb-4 last:mb-0 leading-7">{children}</p>,
                    a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline decoration-blue-300 underline-offset-2">
                            {children}
                        </a>
                    ),
                    blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-blue-200 bg-blue-50/50 pl-4 py-1 my-4 italic text-gray-600 rounded-r">
                            {children}
                        </blockquote>
                    ),
                    div: ({node, ...props}) => <div {...props} />,
                    span: ({node, ...props}) => <span {...props} />,
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

// === 关键修改：使用 React.memo 包裹导出 ===
// 只有当 content 属性发生变化时（即正在生成的最后一条消息），组件才会重新渲染。
// 之前的历史消息将保持静态，极大释放主线程压力。
export default React.memo(MarkdownRenderer);
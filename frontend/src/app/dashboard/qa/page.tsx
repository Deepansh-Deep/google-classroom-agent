'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import {
    Send, Sparkles, User, Copy, Check, AlertCircle, ExternalLink
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL

interface Source {
    type: string
    title: string
    excerpt: string
    relevance_score: number
}

interface Message {
    role: 'user' | 'assistant'
    content: string
    confidence?: number
    sources?: Source[]
    explanation?: string
    timestamp: Date
}

export default function QAPage() {
    const { token } = useAuth()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [copiedId, setCopiedId] = useState<number | null>(null)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const askMutation = useMutation({
        mutationFn: async (question: string) => {
            const res = await fetch(`${API_URL}/qa`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question }),
            })
            return res.json()
        },
        onSuccess: (data) => {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                confidence: data.confidence,
                sources: data.sources,
                explanation: data.explanation,
                timestamp: new Date(),
            }])
        },
    })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || askMutation.isPending) return

        setMessages(prev => [...prev, {
            role: 'user',
            content: input,
            timestamp: new Date(),
        }])
        askMutation.mutate(input)
        setInput('')
    }

    const copyToClipboard = (text: string, id: number) => {
        navigator.clipboard.writeText(text)
        setCopiedId(id)
        setTimeout(() => setCopiedId(null), 2000)
    }

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const confidenceColor = (conf: number) => {
        if (conf >= 0.75) return 'text-green-400'
        if (conf >= 0.5) return 'text-yellow-400'
        return 'text-red-400'
    }

    return (
        <div className="max-w-4xl mx-auto h-[calc(100vh-8rem)] flex flex-col">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white mb-2">AI Q&A Assistant</h1>
                <p className="text-surface-400">
                    Ask questions about your courses and get source-backed answers
                </p>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto rounded-2xl bg-surface-900 border border-surface-800 p-6 space-y-6">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center">
                        <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                            <Sparkles className="w-8 h-8 text-white" />
                        </div>
                        <h2 className="text-xl font-semibold text-white mb-2">Ask me anything</h2>
                        <p className="text-surface-400 max-w-md mb-6">
                            I can answer questions about your course materials, assignments, and announcements
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                            {[
                                'What assignments are due this week?',
                                'Summarize the latest announcements',
                                'Explain the course requirements',
                            ].map((q) => (
                                <button
                                    key={q}
                                    onClick={() => setInput(q)}
                                    className="px-4 py-2 rounded-full bg-surface-800 text-sm text-surface-300 hover:bg-surface-700 hover:text-white transition-colors"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <AnimatePresence>
                        {messages.map((msg, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}
                            >
                                {msg.role === 'assistant' && (
                                    <div className="w-8 h-8 rounded-lg gradient-primary flex-shrink-0 flex items-center justify-center">
                                        <Sparkles className="w-4 h-4 text-white" />
                                    </div>
                                )}
                                <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                                    <div
                                        className={`p-4 rounded-2xl ${msg.role === 'user'
                                                ? 'bg-primary-500 text-white ml-auto'
                                                : 'bg-surface-800 text-surface-100'
                                            }`}
                                    >
                                        <p className="whitespace-pre-wrap">{msg.content}</p>
                                    </div>

                                    {msg.role === 'assistant' && (
                                        <div className="mt-3 space-y-3">
                                            {/* Confidence & Actions */}
                                            <div className="flex items-center gap-4 text-sm">
                                                <span className={`flex items-center gap-1 ${confidenceColor(msg.confidence || 0)}`}>
                                                    <AlertCircle className="w-3 h-3" />
                                                    {((msg.confidence || 0) * 100).toFixed(0)}% confidence
                                                </span>
                                                <button
                                                    onClick={() => copyToClipboard(msg.content, i)}
                                                    className="text-surface-500 hover:text-white transition-colors"
                                                >
                                                    {copiedId === i ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                                </button>
                                            </div>

                                            {/* Sources */}
                                            {msg.sources && msg.sources.length > 0 && (
                                                <div className="space-y-2">
                                                    <p className="text-xs text-surface-500 uppercase tracking-wide">Sources</p>
                                                    {msg.sources.map((source, j) => (
                                                        <div
                                                            key={j}
                                                            className="p-3 rounded-lg bg-surface-800/50 border border-surface-700"
                                                        >
                                                            <div className="flex items-center justify-between mb-1">
                                                                <span className="text-sm font-medium text-white">{source.title}</span>
                                                                <span className="text-xs text-surface-500 px-2 py-0.5 rounded-full bg-surface-700">
                                                                    {source.type}
                                                                </span>
                                                            </div>
                                                            <p className="text-sm text-surface-400 line-clamp-2">{source.excerpt}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Explanation */}
                                            {msg.explanation && (
                                                <p className="text-xs text-surface-500 italic">{msg.explanation}</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {msg.role === 'user' && (
                                    <div className="w-8 h-8 rounded-lg bg-surface-700 flex-shrink-0 flex items-center justify-center">
                                        <User className="w-4 h-4 text-surface-400" />
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>
                )}

                {askMutation.isPending && (
                    <div className="flex gap-4">
                        <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                            <Sparkles className="w-4 h-4 text-white animate-pulse" />
                        </div>
                        <div className="p-4 rounded-2xl bg-surface-800">
                            <div className="flex gap-1">
                                <span className="w-2 h-2 bg-surface-500 rounded-full animate-bounce" />
                                <span className="w-2 h-2 bg-surface-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                <span className="w-2 h-2 bg-surface-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="mt-4">
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask a question..."
                        className="flex-1 px-6 py-4 rounded-xl bg-surface-900 border border-surface-800 text-white placeholder-surface-500 focus:outline-none focus:border-primary-500 transition-colors"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || askMutation.isPending}
                        className="px-6 py-4 rounded-xl gradient-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
            </form>
        </div>
    )
}

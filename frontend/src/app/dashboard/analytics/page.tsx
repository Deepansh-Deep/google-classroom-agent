'use client'

import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import { BarChart3, TrendingUp, TrendingDown, Users, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function AnalyticsPage() {
    const { token, user } = useAuth()

    const { data: performance } = useQuery({
        queryKey: ['my-performance'],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/analytics/my-performance`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token && (user?.role === 'student')
    })

    const categoryColors: Record<string, string> = {
        good: '#22c55e',
        medium: '#f59e0b',
        at_risk: '#ef4444',
    }

    const pieData = performance ? [
        { name: 'Timeliness', value: performance[0]?.factors?.timeliness || 0 },
        { name: 'Consistency', value: performance[0]?.factors?.consistency || 0 },
        { name: 'Completion', value: performance[0]?.factors?.completion || 0 },
    ] : []

    return (
        <div className="max-w-7xl mx-auto">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-white mb-2">Performance Analytics</h1>
                <p className="text-surface-400">Track your academic performance with explainable insights</p>
            </div>

            {performance && performance.length > 0 ? (
                <div className="space-y-6">
                    {/* Overall Score Card */}
                    <div className="grid md:grid-cols-3 gap-6">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="md:col-span-2 p-6 rounded-2xl bg-surface-900 border border-surface-800"
                        >
                            <h2 className="text-lg font-semibold text-white mb-4">Performance Breakdown</h2>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={pieData}>
                                        <XAxis dataKey="name" tick={{ fill: '#94a3b8' }} />
                                        <YAxis tick={{ fill: '#94a3b8' }} />
                                        <Tooltip
                                            contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px' }}
                                            labelStyle={{ color: '#f8fafc' }}
                                        />
                                        <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
                            className="p-6 rounded-2xl bg-surface-900 border border-surface-800"
                        >
                            <h2 className="text-lg font-semibold text-white mb-4">Overall Score</h2>
                            <div className="text-center">
                                <div className="relative inline-flex items-center justify-center">
                                    <svg className="w-32 h-32">
                                        <circle
                                            cx="64"
                                            cy="64"
                                            r="56"
                                            fill="none"
                                            stroke="#1e293b"
                                            strokeWidth="12"
                                        />
                                        <circle
                                            cx="64"
                                            cy="64"
                                            r="56"
                                            fill="none"
                                            stroke={categoryColors[performance[0]?.category || 'medium']}
                                            strokeWidth="12"
                                            strokeLinecap="round"
                                            strokeDasharray={`${(performance[0]?.score || 0) * 3.52} 352`}
                                            transform="rotate(-90 64 64)"
                                        />
                                    </svg>
                                    <span className="absolute text-3xl font-bold text-white">
                                        {Math.round(performance[0]?.score || 0)}
                                    </span>
                                </div>
                                <p className={`mt-4 text-lg font-medium capitalize`} style={{ color: categoryColors[performance[0]?.category || 'medium'] }}>
                                    {performance[0]?.category?.replace('_', ' ') || 'Unknown'}
                                </p>
                            </div>
                        </motion.div>
                    </div>

                    {/* Factor Cards */}
                    <div className="grid md:grid-cols-3 gap-6">
                        {[
                            { label: 'Timeliness', value: performance[0]?.factors?.timeliness, icon: Clock, desc: 'On-time submission rate' },
                            { label: 'Consistency', value: performance[0]?.factors?.consistency, icon: TrendingUp, desc: 'Regular submission pattern' },
                            { label: 'Completion', value: performance[0]?.factors?.completion, icon: CheckCircle, desc: 'Assignments completed' },
                        ].map((factor, i) => (
                            <motion.div
                                key={factor.label}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 + i * 0.1 }}
                                className="p-6 rounded-2xl bg-surface-900 border border-surface-800"
                            >
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center">
                                        <factor.icon className="w-5 h-5 text-primary-400" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white">{factor.label}</h3>
                                        <p className="text-xs text-surface-500">{factor.desc}</p>
                                    </div>
                                </div>
                                <div className="flex items-end gap-2">
                                    <span className="text-3xl font-bold text-white">{Math.round(factor.value || 0)}%</span>
                                </div>
                                <div className="mt-4 h-2 bg-surface-800 rounded-full overflow-hidden">
                                    <div
                                        className="h-full gradient-primary transition-all duration-1000"
                                        style={{ width: `${factor.value || 0}%` }}
                                    />
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Explanation */}
                    {performance[0]?.explanation && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 }}
                            className="p-6 rounded-2xl bg-surface-900 border border-surface-800"
                        >
                            <h2 className="text-lg font-semibold text-white mb-4">Analysis & Recommendations</h2>
                            <p className="text-surface-300 mb-4">{performance[0].explanation.summary}</p>
                            {performance[0].explanation.recommendations?.length > 0 && (
                                <div className="space-y-2">
                                    {performance[0].explanation.recommendations.map((rec: string, i: number) => (
                                        <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface-800/50">
                                            <TrendingUp className="w-4 h-4 text-primary-400" />
                                            <span className="text-surface-300">{rec}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    )}
                </div>
            ) : (
                <div className="text-center py-20">
                    <BarChart3 className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                    <h2 className="text-xl font-semibold text-white mb-2">No analytics data</h2>
                    <p className="text-surface-400">
                        Complete some assignments to see your performance analytics
                    </p>
                </div>
            )}
        </div>
    )
}

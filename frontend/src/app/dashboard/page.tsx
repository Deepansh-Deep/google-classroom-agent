'use client'

import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../providers'
import {
    BookOpen, FileText, AlertTriangle, CheckCircle,
    Clock, TrendingUp, ArrowRight, Sparkles
} from 'lucide-react'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function DashboardPage() {
    const { user, token } = useAuth()

    const { data: courses } = useQuery({
        queryKey: ['courses'],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/courses`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token
    })

    const { data: upcoming } = useQuery({
        queryKey: ['upcoming-deadlines'],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/assignments/upcoming?days=7`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token
    })

    const stats = [
        { label: 'Active Courses', value: courses?.total || 0, icon: BookOpen, color: 'primary' },
        { label: 'Upcoming Deadlines', value: upcoming?.length || 0, icon: Clock, color: 'warning' },
        { label: 'Completed', value: 12, icon: CheckCircle, color: 'success' },
        { label: 'At Risk', value: 2, icon: AlertTriangle, color: 'danger' },
    ]

    const colors: Record<string, string> = {
        primary: 'gradient-primary',
        warning: 'gradient-warning',
        success: 'gradient-success',
        danger: 'gradient-danger',
    }

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            {/* Welcome Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Welcome back, {user?.name?.split(' ')[0] || 'there'}! 👋
                    </h1>
                    <p className="text-surface-400">
                        Here's what's happening in your classroom today
                    </p>
                </div>
                <Link
                    href="/dashboard/courses/sync"
                    className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl gradient-primary text-white font-medium hover:opacity-90 transition-opacity"
                >
                    <TrendingUp className="w-4 h-4" />
                    Sync Courses
                </Link>
            </motion.div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat, i) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="p-6 rounded-2xl bg-surface-900 border border-surface-800"
                    >
                        <div className={`w-12 h-12 rounded-xl ${colors[stat.color]} flex items-center justify-center mb-4`}>
                            <stat.icon className="w-6 h-6 text-white" />
                        </div>
                        <p className="text-3xl font-bold text-white mb-1">{stat.value}</p>
                        <p className="text-surface-400 text-sm">{stat.label}</p>
                    </motion.div>
                ))}
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Upcoming Deadlines */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-surface-900 border border-surface-800 rounded-2xl p-6"
                >
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-semibold text-white">Upcoming Deadlines</h2>
                        <Link href="/dashboard/assignments" className="text-primary-400 text-sm hover:text-primary-300">
                            View all
                        </Link>
                    </div>

                    <div className="space-y-4">
                        {upcoming?.slice(0, 4).map((item: any) => (
                            <div
                                key={item.assignment.id}
                                className="flex items-center gap-4 p-4 rounded-xl bg-surface-800/50 hover:bg-surface-800 transition-colors"
                            >
                                <div className={`w-2 h-2 rounded-full ${item.urgency === 'urgent' ? 'bg-red-500' :
                                        item.urgency === 'soon' ? 'bg-yellow-500' : 'bg-green-500'
                                    }`} />
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-white truncate">{item.assignment.title}</p>
                                    <p className="text-sm text-surface-400">{item.time_remaining}</p>
                                </div>
                                <ArrowRight className="w-4 h-4 text-surface-500" />
                            </div>
                        )) || (
                                <p className="text-surface-500 text-center py-8">No upcoming deadlines</p>
                            )}
                    </div>
                </motion.div>

                {/* Quick AI Q&A */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-surface-900 border border-surface-800 rounded-2xl p-6"
                >
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-white">Ask AI Assistant</h2>
                            <p className="text-sm text-surface-400">Get instant answers from your course content</p>
                        </div>
                    </div>

                    <Link
                        href="/dashboard/qa"
                        className="block p-4 rounded-xl bg-surface-800/50 border border-surface-700 hover:border-primary-500/50 transition-colors group"
                    >
                        <div className="flex items-center gap-3 text-surface-400 group-hover:text-primary-400 transition-colors">
                            <FileText className="w-5 h-5" />
                            <span>Ask a question about your courses...</span>
                        </div>
                    </Link>

                    <div className="mt-4 flex flex-wrap gap-2">
                        {['What are my pending assignments?', 'Explain last lecture', 'Exam schedule'].map((q) => (
                            <button
                                key={q}
                                className="px-3 py-1.5 rounded-full bg-surface-800 text-sm text-surface-400 hover:text-white hover:bg-surface-700 transition-colors"
                            >
                                {q}
                            </button>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* Courses */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-semibold text-white">Your Courses</h2>
                    <Link href="/dashboard/courses" className="text-primary-400 text-sm hover:text-primary-300">
                        View all
                    </Link>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {courses?.courses?.slice(0, 6).map((course: any) => (
                        <Link
                            key={course.id}
                            href={`/dashboard/courses/${course.id}`}
                            className="block p-6 rounded-2xl bg-surface-900 border border-surface-800 hover:border-primary-500/50 transition-all group"
                        >
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <BookOpen className="w-6 h-6 text-primary-400" />
                            </div>
                            <h3 className="font-semibold text-white mb-1 truncate">{course.name}</h3>
                            <p className="text-sm text-surface-400 truncate">{course.section || 'No section'}</p>
                        </Link>
                    )) || (
                            <div className="col-span-full text-center py-12 text-surface-500">
                                <BookOpen className="w-12 h-12 mx-auto mb-4 text-surface-600" />
                                <p>No courses synced yet. Click "Sync Courses" to get started.</p>
                            </div>
                        )}
                </div>
            </motion.div>
        </div>
    )
}

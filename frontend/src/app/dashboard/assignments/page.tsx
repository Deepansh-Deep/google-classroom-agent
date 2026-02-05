'use client'

import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import { FileText, Clock, CheckCircle, AlertTriangle, Calendar, Filter } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import { format } from 'date-fns'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function AssignmentsPage() {
    const { token } = useAuth()
    const [filter, setFilter] = useState<'all' | 'upcoming'>('all')

    const { data, isLoading } = useQuery({
        queryKey: ['assignments', filter],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/assignments?upcoming_only=${filter === 'upcoming'}`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token
    })

    const getUrgency = (dueDate: string | null) => {
        if (!dueDate) return 'none'
        const diff = new Date(dueDate).getTime() - Date.now()
        if (diff < 0) return 'overdue'
        if (diff < 24 * 60 * 60 * 1000) return 'urgent'
        if (diff < 3 * 24 * 60 * 60 * 1000) return 'soon'
        return 'upcoming'
    }

    const urgencyStyles: Record<string, string> = {
        overdue: 'bg-red-500/10 text-red-400 border-red-500/20',
        urgent: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
        soon: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        upcoming: 'bg-green-500/10 text-green-400 border-green-500/20',
        none: 'bg-surface-700 text-surface-400 border-surface-600',
    }

    return (
        <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Assignments</h1>
                    <p className="text-surface-400">Track all your assignments and deadlines</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setFilter('all')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'all'
                                ? 'bg-primary-500 text-white'
                                : 'bg-surface-800 text-surface-400 hover:text-white'
                            }`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setFilter('upcoming')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'upcoming'
                                ? 'bg-primary-500 text-white'
                                : 'bg-surface-800 text-surface-400 hover:text-white'
                            }`}
                    >
                        Upcoming
                    </button>
                </div>
            </div>

            {isLoading ? (
                <div className="space-y-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="p-6 rounded-2xl bg-surface-900 border border-surface-800 animate-pulse">
                            <div className="flex gap-4">
                                <div className="w-12 h-12 rounded-xl bg-surface-800" />
                                <div className="flex-1">
                                    <div className="h-5 bg-surface-800 rounded mb-2 w-1/3" />
                                    <div className="h-4 bg-surface-800 rounded w-1/4" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : data?.assignments?.length > 0 ? (
                <div className="space-y-4">
                    {data.assignments.map((assignment: any, i: number) => {
                        const urgency = getUrgency(assignment.due_date)
                        return (
                            <motion.div
                                key={assignment.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.03 }}
                            >
                                <Link
                                    href={`/dashboard/assignments/${assignment.id}`}
                                    className="block p-6 rounded-2xl bg-surface-900 border border-surface-800 hover:border-primary-500/50 transition-all group"
                                >
                                    <div className="flex items-start gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                                            <FileText className="w-6 h-6 text-primary-400" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4">
                                                <h3 className="text-lg font-semibold text-white truncate group-hover:text-primary-400 transition-colors">
                                                    {assignment.title}
                                                </h3>
                                                <span className={`px-3 py-1 rounded-full text-xs border whitespace-nowrap ${urgencyStyles[urgency]}`}>
                                                    {urgency === 'none' ? 'No deadline' : urgency.charAt(0).toUpperCase() + urgency.slice(1)}
                                                </span>
                                            </div>

                                            <div className="flex items-center gap-4 mt-2 text-sm text-surface-400">
                                                {assignment.due_date && (
                                                    <span className="flex items-center gap-1">
                                                        <Calendar className="w-4 h-4" />
                                                        {format(new Date(assignment.due_date), 'MMM d, yyyy h:mm a')}
                                                    </span>
                                                )}
                                                {assignment.max_points && (
                                                    <span className="flex items-center gap-1">
                                                        <CheckCircle className="w-4 h-4" />
                                                        {assignment.max_points} pts
                                                    </span>
                                                )}
                                            </div>

                                            {assignment.description && (
                                                <p className="mt-3 text-sm text-surface-500 line-clamp-2">
                                                    {assignment.description}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </Link>
                            </motion.div>
                        )
                    })}
                </div>
            ) : (
                <div className="text-center py-20">
                    <FileText className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                    <h2 className="text-xl font-semibold text-white mb-2">No assignments</h2>
                    <p className="text-surface-400">
                        {filter === 'upcoming'
                            ? 'No upcoming assignments. Nice job!'
                            : 'Sync your courses to see assignments here'}
                    </p>
                </div>
            )}
        </div>
    )
}

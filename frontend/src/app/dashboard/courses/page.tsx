'use client'

import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import { BookOpen, RefreshCw, Users, FileText, Clock, ArrowRight } from 'lucide-react'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function CoursesPage() {
    const { token } = useAuth()
    const queryClient = useQueryClient()

    const { data: courses, isLoading } = useQuery({
        queryKey: ['courses'],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/courses`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token
    })

    const syncMutation = useMutation({
        mutationFn: async () => {
            const res = await fetch(`${API_URL}/courses/sync`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
        }
    })

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Your Courses</h1>
                    <p className="text-surface-400">Manage and view your synced courses</p>
                </div>
                <button
                    onClick={() => syncMutation.mutate()}
                    disabled={syncMutation.isPending}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-primary text-white font-medium disabled:opacity-50"
                >
                    <RefreshCw className={`w-4 h-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
                    {syncMutation.isPending ? 'Syncing...' : 'Sync Courses'}
                </button>
            </div>

            {syncMutation.isSuccess && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400"
                >
                    Sync completed! Courses: {syncMutation.data.courses_synced},
                    Assignments: {syncMutation.data.assignments_synced}
                </motion.div>
            )}

            {isLoading ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <div key={i} className="p-6 rounded-2xl bg-surface-900 border border-surface-800 animate-pulse">
                            <div className="w-12 h-12 rounded-xl bg-surface-800 mb-4" />
                            <div className="h-5 bg-surface-800 rounded mb-2 w-2/3" />
                            <div className="h-4 bg-surface-800 rounded w-1/2" />
                        </div>
                    ))}
                </div>
            ) : courses?.courses?.length > 0 ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {courses.courses.map((course: any, i: number) => (
                        <motion.div
                            key={course.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                        >
                            <Link
                                href={`/dashboard/courses/${course.id}`}
                                className="block p-6 rounded-2xl bg-surface-900 border border-surface-800 hover:border-primary-500/50 transition-all group"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                                        <BookOpen className="w-6 h-6 text-primary-400" />
                                    </div>
                                    <span className={`px-2 py-1 rounded-full text-xs ${course.state === 'ACTIVE'
                                            ? 'bg-green-500/10 text-green-400'
                                            : 'bg-surface-700 text-surface-400'
                                        }`}>
                                        {course.state}
                                    </span>
                                </div>

                                <h3 className="text-lg font-semibold text-white mb-1 truncate group-hover:text-primary-400 transition-colors">
                                    {course.name}
                                </h3>
                                <p className="text-sm text-surface-400 mb-4 truncate">
                                    {course.section || 'No section'}
                                </p>

                                <div className="flex items-center gap-4 text-sm text-surface-500">
                                    <span className="flex items-center gap-1">
                                        <Clock className="w-4 h-4" />
                                        {course.synced_at ? new Date(course.synced_at).toLocaleDateString() : 'Not synced'}
                                    </span>
                                    <ArrowRight className="w-4 h-4 ml-auto group-hover:translate-x-1 transition-transform" />
                                </div>
                            </Link>
                        </motion.div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-20">
                    <BookOpen className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                    <h2 className="text-xl font-semibold text-white mb-2">No courses yet</h2>
                    <p className="text-surface-400 mb-6">
                        Sync your Google Classroom to see your courses here
                    </p>
                    <button
                        onClick={() => syncMutation.mutate()}
                        className="px-6 py-3 rounded-xl gradient-primary text-white font-medium"
                    >
                        Sync Now
                    </button>
                </div>
            )}
        </div>
    )
}

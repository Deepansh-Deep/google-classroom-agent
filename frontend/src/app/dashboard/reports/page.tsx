'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import { FileDown, Calendar, Download, Users, TrendingUp, TrendingDown } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function ReportsPage() {
    const { token, user } = useAuth()
    const [selectedCourse, setSelectedCourse] = useState<string>('')
    const [reportType, setReportType] = useState<'weekly' | 'monthly'>('weekly')

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

    const { data: report, isLoading, refetch } = useQuery({
        queryKey: ['report', selectedCourse, reportType],
        queryFn: async () => {
            const res = await fetch(
                `${API_URL}/reports/${selectedCourse}?report_type=${reportType}`,
                { method: 'POST', headers: { Authorization: `Bearer ${token}` } }
            )
            return res.json()
        },
        enabled: !!token && !!selectedCourse
    })

    const downloadCSV = async () => {
        const res = await fetch(
            `${API_URL}/reports/${selectedCourse}/csv?report_type=${reportType}`,
            { headers: { Authorization: `Bearer ${token}` } }
        )
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `report_${reportType}.csv`
        a.click()
    }

    const categoryColors: Record<string, string> = {
        good: 'text-green-400',
        medium: 'text-yellow-400',
        at_risk: 'text-red-400',
    }

    if (user?.role !== 'teacher' && user?.role !== 'admin') {
        return (
            <div className="text-center py-20">
                <FileDown className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                <h2 className="text-xl font-semibold text-white mb-2">Teacher Access Required</h2>
                <p className="text-surface-400">Reports are available for teachers and admins only.</p>
            </div>
        )
    }

    return (
        <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Reports</h1>
                    <p className="text-surface-400">Generate and export performance reports</p>
                </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap gap-4 mb-8">
                <select
                    value={selectedCourse}
                    onChange={(e) => setSelectedCourse(e.target.value)}
                    className="px-4 py-2.5 rounded-xl bg-surface-900 border border-surface-800 text-white focus:outline-none focus:border-primary-500"
                >
                    <option value="">Select a course</option>
                    {courses?.courses?.map((c: any) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                </select>

                <div className="flex gap-2">
                    <button
                        onClick={() => setReportType('weekly')}
                        className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${reportType === 'weekly' ? 'bg-primary-500 text-white' : 'bg-surface-900 border border-surface-800 text-surface-400'
                            }`}
                    >
                        Weekly
                    </button>
                    <button
                        onClick={() => setReportType('monthly')}
                        className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${reportType === 'monthly' ? 'bg-primary-500 text-white' : 'bg-surface-900 border border-surface-800 text-surface-400'
                            }`}
                    >
                        Monthly
                    </button>
                </div>

                {selectedCourse && report && (
                    <button
                        onClick={downloadCSV}
                        className="ml-auto flex items-center gap-2 px-4 py-2.5 rounded-xl bg-surface-900 border border-surface-800 text-white hover:border-primary-500"
                    >
                        <Download className="w-4 h-4" />
                        Export CSV
                    </button>
                )}
            </div>

            {/* Report Content */}
            {!selectedCourse ? (
                <div className="text-center py-20 bg-surface-900 border border-surface-800 rounded-2xl">
                    <Calendar className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                    <h2 className="text-xl font-semibold text-white mb-2">Select a Course</h2>
                    <p className="text-surface-400">Choose a course to generate a performance report</p>
                </div>
            ) : isLoading ? (
                <div className="p-8 bg-surface-900 border border-surface-800 rounded-2xl animate-pulse">
                    <div className="h-8 bg-surface-800 rounded w-1/3 mb-6" />
                    <div className="grid md:grid-cols-4 gap-4 mb-8">
                        {[1, 2, 3, 4].map((i) => (
                            <div key={i} className="h-24 bg-surface-800 rounded-xl" />
                        ))}
                    </div>
                    <div className="space-y-4">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-16 bg-surface-800 rounded-xl" />
                        ))}
                    </div>
                </div>
            ) : report ? (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6"
                >
                    {/* Summary Cards */}
                    <div className="grid md:grid-cols-4 gap-4">
                        {[
                            { label: 'Students', value: report.summary.student_count, icon: Users },
                            { label: 'Assignments', value: report.summary.total_assignments, icon: FileDown },
                            { label: 'Submissions', value: report.summary.total_submissions, icon: TrendingUp },
                            { label: 'On-Time Rate', value: `${Math.round(report.summary.on_time_rate)}%`, icon: Calendar },
                        ].map((stat) => (
                            <div key={stat.label} className="p-4 rounded-xl bg-surface-900 border border-surface-800">
                                <stat.icon className="w-5 h-5 text-primary-400 mb-2" />
                                <p className="text-2xl font-bold text-white">{stat.value}</p>
                                <p className="text-sm text-surface-400">{stat.label}</p>
                            </div>
                        ))}
                    </div>

                    {/* Student Table */}
                    <div className="bg-surface-900 border border-surface-800 rounded-2xl overflow-hidden">
                        <div className="p-4 border-b border-surface-800">
                            <h2 className="text-lg font-semibold text-white">Student Performance</h2>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-surface-800/50">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm text-surface-400 font-medium">Student</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">Completed</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">On Time</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">Late</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">Missing</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">Avg Grade</th>
                                        <th className="px-4 py-3 text-center text-sm text-surface-400 font-medium">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-surface-800">
                                    {report.students.map((entry: any, i: number) => (
                                        <tr key={i} className="hover:bg-surface-800/30">
                                            <td className="px-4 py-3">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
                                                        <span className="text-xs font-medium text-primary-400">
                                                            {entry.student.name?.charAt(0) || entry.student.email.charAt(0)}
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-white">{entry.student.name || 'Unknown'}</p>
                                                        <p className="text-xs text-surface-500">{entry.student.email}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-center text-sm text-white">{entry.assignments_completed}/{entry.assignments_total}</td>
                                            <td className="px-4 py-3 text-center text-sm text-green-400">{entry.on_time_submissions}</td>
                                            <td className="px-4 py-3 text-center text-sm text-yellow-400">{entry.late_submissions}</td>
                                            <td className="px-4 py-3 text-center text-sm text-red-400">{entry.missing_assignments}</td>
                                            <td className="px-4 py-3 text-center text-sm text-white">
                                                {entry.average_grade ? `${entry.average_grade.toFixed(1)}%` : 'N/A'}
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${categoryColors[entry.performance_category]}`}>
                                                    {entry.performance_category.replace('_', ' ')}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </motion.div>
            ) : null}
        </div>
    )
}

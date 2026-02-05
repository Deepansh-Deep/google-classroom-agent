'use client'

import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../providers'
import { Bell, Calendar, Clock, Plus, FileText } from 'lucide-react'
import { format } from 'date-fns'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function RemindersPage() {
    const { token } = useAuth()
    const queryClient = useQueryClient()

    const { data: reminders, isLoading } = useQuery({
        queryKey: ['reminders'],
        queryFn: async () => {
            const res = await fetch(`${API_URL}/reminders/upcoming`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        enabled: !!token
    })

    const scheduleMutation = useMutation({
        mutationFn: async () => {
            const res = await fetch(`${API_URL}/reminders/schedule`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` }
            })
            return res.json()
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['reminders'] })
        }
    })

    const typeStyles: Record<string, { bg: string; text: string; label: string }> = {
        upcoming: { bg: 'bg-blue-500/10', text: 'text-blue-400', label: '3 days before' },
        deadline: { bg: 'bg-orange-500/10', text: 'text-orange-400', label: '24h before' },
        overdue: { bg: 'bg-red-500/10', text: 'text-red-400', label: 'Past due' },
    }

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-2">Reminders</h1>
                    <p className="text-surface-400">Never miss a deadline with smart notifications</p>
                </div>
                <button
                    onClick={() => scheduleMutation.mutate()}
                    disabled={scheduleMutation.isPending}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl gradient-primary text-white font-medium disabled:opacity-50"
                >
                    <Plus className="w-4 h-4" />
                    {scheduleMutation.isPending ? 'Scheduling...' : 'Schedule Reminders'}
                </button>
            </div>

            {scheduleMutation.isSuccess && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400"
                >
                    {scheduleMutation.data.scheduled} new reminders scheduled!
                </motion.div>
            )}

            {isLoading ? (
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="p-6 rounded-2xl bg-surface-900 border border-surface-800 animate-pulse">
                            <div className="h-5 bg-surface-800 rounded w-1/2 mb-3" />
                            <div className="h-4 bg-surface-800 rounded w-1/3" />
                        </div>
                    ))}
                </div>
            ) : reminders?.length > 0 ? (
                <div className="space-y-4">
                    {reminders.map((reminder: any, i: number) => {
                        const style = typeStyles[reminder.reminder_type] || typeStyles.upcoming
                        return (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="p-6 rounded-2xl bg-surface-900 border border-surface-800"
                            >
                                <div className="flex items-start gap-4">
                                    <div className={`w-12 h-12 rounded-xl ${style.bg} flex items-center justify-center flex-shrink-0`}>
                                        <Bell className={`w-6 h-6 ${style.text}`} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-3 mb-2">
                                            <h3 className="font-semibold text-white truncate">
                                                {reminder.assignment.title}
                                            </h3>
                                            <span className={`px-2 py-1 rounded-full text-xs ${style.bg} ${style.text}`}>
                                                {style.label}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-surface-400">
                                            <span className="flex items-center gap-1">
                                                <Calendar className="w-4 h-4" />
                                                Scheduled: {format(new Date(reminder.scheduled_for), 'MMM d, h:mm a')}
                                            </span>
                                            {reminder.assignment.due_date && (
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-4 h-4" />
                                                    Due: {format(new Date(reminder.assignment.due_date), 'MMM d, h:mm a')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )
                    })}
                </div>
            ) : (
                <div className="text-center py-20">
                    <Bell className="w-16 h-16 mx-auto text-surface-600 mb-4" />
                    <h2 className="text-xl font-semibold text-white mb-2">No reminders</h2>
                    <p className="text-surface-400 mb-6">
                        Click "Schedule Reminders" to set up notifications for upcoming deadlines
                    </p>
                    <button
                        onClick={() => scheduleMutation.mutate()}
                        className="px-6 py-3 rounded-xl gradient-primary text-white font-medium"
                    >
                        Schedule Now
                    </button>
                </div>
            )}
        </div>
    )
}

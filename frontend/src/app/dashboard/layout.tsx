'use client'

import { useState, ReactNode } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { useAuth, useTheme } from '../../providers'
import {
    LayoutDashboard,
    BookOpen,
    FileText,
    HelpCircle,
    BarChart3,
    Bell,
    FileDown,
    Settings,
    LogOut,
    Menu,
    X,
    Moon,
    Sun,
    Sparkles,
    ChevronDown,
} from 'lucide-react'

const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/dashboard/courses', icon: BookOpen, label: 'Courses' },
    { href: '/dashboard/assignments', icon: FileText, label: 'Assignments' },
    { href: '/dashboard/qa', icon: HelpCircle, label: 'Ask AI' },
    { href: '/dashboard/analytics', icon: BarChart3, label: 'Analytics' },
    { href: '/dashboard/reminders', icon: Bell, label: 'Reminders' },
    { href: '/dashboard/reports', icon: FileDown, label: 'Reports' },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
    const pathname = usePathname()
    const router = useRouter()
    const { user, logout } = useAuth()
    const { theme, toggleTheme } = useTheme()
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [userMenuOpen, setUserMenuOpen] = useState(false)

    const handleLogout = () => {
        logout()
        router.push('/login')
    }

    return (
        <div className="min-h-screen bg-surface-950 flex">
            {/* Sidebar - Desktop */}
            <aside className="hidden lg:flex flex-col w-64 bg-surface-900 border-r border-surface-800">
                <div className="p-6">
                    <Link href="/dashboard" className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-semibold text-white">Classroom</span>
                    </Link>
                </div>

                <nav className="flex-1 px-4 space-y-1">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${isActive
                                        ? 'bg-primary-500/10 text-primary-400 border border-primary-500/20'
                                        : 'text-surface-400 hover:bg-surface-800 hover:text-white'
                                    }`}
                            >
                                <item.icon className="w-5 h-5" />
                                <span className="font-medium">{item.label}</span>
                            </Link>
                        )
                    })}
                </nav>

                <div className="p-4 border-t border-surface-800">
                    <button
                        onClick={toggleTheme}
                        className="flex items-center gap-3 w-full px-4 py-3 rounded-xl text-surface-400 hover:bg-surface-800 hover:text-white transition-all"
                    >
                        {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                        <span className="font-medium">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
                    </button>
                </div>
            </aside>

            {/* Mobile Sidebar */}
            {sidebarOpen && (
                <>
                    <div
                        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                    <motion.aside
                        initial={{ x: -280 }}
                        animate={{ x: 0 }}
                        className="fixed inset-y-0 left-0 w-72 bg-surface-900 z-50 lg:hidden"
                    >
                        <div className="flex items-center justify-between p-6">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                                    <Sparkles className="w-5 h-5 text-white" />
                                </div>
                                <span className="text-lg font-semibold text-white">Classroom</span>
                            </div>
                            <button onClick={() => setSidebarOpen(false)}>
                                <X className="w-6 h-6 text-surface-400" />
                            </button>
                        </div>
                        <nav className="px-4 space-y-1">
                            {navItems.map((item) => (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    onClick={() => setSidebarOpen(false)}
                                    className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${pathname === item.href
                                            ? 'bg-primary-500/10 text-primary-400'
                                            : 'text-surface-400 hover:bg-surface-800'
                                        }`}
                                >
                                    <item.icon className="w-5 h-5" />
                                    <span>{item.label}</span>
                                </Link>
                            ))}
                        </nav>
                    </motion.aside>
                </>
            )}

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <header className="h-16 border-b border-surface-800 flex items-center justify-between px-6">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="lg:hidden text-surface-400 hover:text-white"
                    >
                        <Menu className="w-6 h-6" />
                    </button>

                    <div className="flex-1 lg:flex-none" />

                    <div className="relative">
                        <button
                            onClick={() => setUserMenuOpen(!userMenuOpen)}
                            className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-surface-800 transition-colors"
                        >
                            <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
                                <span className="text-sm font-medium text-primary-400">
                                    {user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                                </span>
                            </div>
                            <span className="hidden sm:block text-white font-medium">
                                {user?.name || user?.email}
                            </span>
                            <ChevronDown className="w-4 h-4 text-surface-400" />
                        </button>

                        {userMenuOpen && (
                            <motion.div
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute right-0 mt-2 w-48 bg-surface-800 border border-surface-700 rounded-xl shadow-xl py-2"
                            >
                                <Link
                                    href="/dashboard/settings"
                                    className="flex items-center gap-3 px-4 py-2 text-surface-300 hover:bg-surface-700"
                                    onClick={() => setUserMenuOpen(false)}
                                >
                                    <Settings className="w-4 h-4" />
                                    Settings
                                </Link>
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center gap-3 px-4 py-2 text-red-400 hover:bg-surface-700"
                                >
                                    <LogOut className="w-4 h-4" />
                                    Sign Out
                                </button>
                            </motion.div>
                        )}
                    </div>
                </header>

                {/* Page Content */}
                <main className="flex-1 p-6 overflow-auto">{children}</main>
            </div>
        </div>
    )
}

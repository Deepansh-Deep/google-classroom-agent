'use client'

import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL

export default function LoginPage() {
    const handleGoogleLogin = async () => {
        try {
            const response = await fetch(`${API_URL}/auth/google`)
            const data = await response.json()
            window.location.href = data.auth_url
        } catch (error) {
            console.error('Failed to get auth URL:', error)
        }
    }

    return (
        <div className="min-h-screen bg-surface-950 flex items-center justify-center p-8">
            {/* Background effects */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary-900/30 via-surface-950 to-surface-950" />
            <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-primary-500/5 rounded-full blur-3xl" />
            <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-secondary-500/5 rounded-full blur-3xl" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative z-10 w-full max-w-md"
            >
                {/* Logo */}
                <div className="flex items-center justify-center gap-3 mb-8">
                    <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
                        <Sparkles className="w-7 h-7 text-white" />
                    </div>
                    <span className="text-2xl font-bold text-white">Classroom Assistant</span>
                </div>

                {/* Login Card */}
                <div className="bg-surface-900/50 backdrop-blur-xl border border-surface-800 rounded-2xl p-8">
                    <h1 className="text-2xl font-bold text-white text-center mb-2">
                        Welcome Back
                    </h1>
                    <p className="text-surface-400 text-center mb-8">
                        Sign in to access your classroom dashboard
                    </p>

                    <button
                        onClick={handleGoogleLogin}
                        className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl bg-white hover:bg-surface-100 transition-colors text-surface-900 font-semibold"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path
                                fill="currentColor"
                                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            />
                            <path
                                fill="#34A853"
                                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            />
                            <path
                                fill="#FBBC05"
                                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                            />
                            <path
                                fill="#EA4335"
                                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            />
                        </svg>
                        Continue with Google
                    </button>

                    <div className="mt-6 text-center text-sm text-surface-500">
                        By signing in, you agree to our Terms of Service and Privacy Policy
                    </div>
                </div>

                {/* Features reminder */}
                <div className="mt-8 grid grid-cols-2 gap-4">
                    {['Track Assignments', 'AI Q&A', 'Analytics', 'Reminders'].map((feature) => (
                        <div
                            key={feature}
                            className="flex items-center gap-2 text-sm text-surface-400"
                        >
                            <div className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                            {feature}
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    )
}

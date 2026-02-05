'use client'

import { motion } from 'framer-motion'
import { BookOpen, Brain, BarChart3, Bell, ArrowRight, Sparkles } from 'lucide-react'
import Link from 'next/link'

const features = [
    {
        icon: BookOpen,
        title: 'Smart Tracking',
        description: 'Automatic syncing with Google Classroom for seamless assignment tracking',
        gradient: 'gradient-primary',
    },
    {
        icon: Brain,
        title: 'AI-Powered Q&A',
        description: 'Ask questions about your courses and get instant, source-backed answers',
        gradient: 'gradient-success',
    },
    {
        icon: BarChart3,
        title: 'Performance Analytics',
        description: 'Understand student performance with explainable, rule-based insights',
        gradient: 'gradient-warning',
    },
    {
        icon: Bell,
        title: 'Smart Reminders',
        description: 'Never miss a deadline with intelligent, multi-level notifications',
        gradient: 'gradient-danger',
    },
]

export default function HomePage() {
    return (
        <div className="min-h-screen bg-surface-950 text-white overflow-hidden">
            {/* Hero Section */}
            <div className="relative">
                {/* Gradient background */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary-900/50 via-surface-950 to-surface-950" />
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary-500/10 rounded-full blur-3xl" />

                <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                            <Sparkles className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-xl font-semibold">Classroom Assistant</span>
                    </div>
                    <Link
                        href="/login"
                        className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/10 transition-all duration-300 font-medium"
                    >
                        Sign In
                    </Link>
                </nav>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                    className="relative z-10 max-w-7xl mx-auto px-8 pt-20 pb-32 text-center"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-500/10 border border-primary-500/20 mb-8">
                        <Sparkles className="w-4 h-4 text-primary-400" />
                        <span className="text-sm text-primary-300">AI-Powered Education</span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
                        Your Intelligent
                        <br />
                        <span className="bg-gradient-to-r from-primary-400 via-purple-400 to-secondary-400 bg-clip-text text-transparent">
                            Classroom Companion
                        </span>
                    </h1>

                    <p className="text-xl text-surface-300 max-w-2xl mx-auto mb-12">
                        Track assignments, analyze performance, and get AI-powered answers
                        from your course content. Built for modern education.
                    </p>

                    <div className="flex gap-4 justify-center">
                        <Link
                            href="/login"
                            className="inline-flex items-center gap-2 px-8 py-4 rounded-full gradient-primary hover:opacity-90 transition-opacity font-semibold text-lg shadow-lg shadow-primary-500/25"
                        >
                            Get Started
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                        <Link
                            href="#features"
                            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 transition-all font-medium text-lg"
                        >
                            Learn More
                        </Link>
                    </div>
                </motion.div>
            </div>

            {/* Features Section */}
            <section id="features" className="py-24 px-8">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">Powerful Features</h2>
                        <p className="text-surface-400 text-lg max-w-xl mx-auto">
                            Everything you need to manage your classroom effectively
                        </p>
                    </motion.div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {features.map((feature, i) => (
                            <motion.div
                                key={feature.title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className="group p-6 rounded-2xl bg-surface-900/50 border border-surface-800 hover:border-surface-700 transition-all duration-300"
                            >
                                <div className={`w-12 h-12 rounded-xl ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                                    <feature.icon className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                                <p className="text-surface-400">{feature.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 px-8">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    className="max-w-4xl mx-auto text-center p-12 rounded-3xl bg-gradient-to-r from-primary-600 to-purple-600 relative overflow-hidden"
                >
                    <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
                    <div className="relative z-10">
                        <h2 className="text-4xl font-bold mb-4">Ready to Transform Your Classroom?</h2>
                        <p className="text-white/80 text-lg mb-8 max-w-xl mx-auto">
                            Join thousands of educators using AI to enhance learning outcomes
                        </p>
                        <Link
                            href="/login"
                            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-white text-primary-600 hover:bg-surface-100 transition-colors font-semibold text-lg"
                        >
                            Start Free Trial
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                    </div>
                </motion.div>
            </section>

            {/* Footer */}
            <footer className="border-t border-surface-800 py-8 px-8">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                            <Sparkles className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-medium">Classroom Assistant</span>
                    </div>
                    <p className="text-surface-500 text-sm">
                        © 2024 Classroom Assistant. All rights reserved.
                    </p>
                </div>
            </footer>
        </div>
    )
}
